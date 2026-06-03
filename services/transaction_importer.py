import io
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from services.conversion_engine import ConversionEngine


REQUIRED_COLUMNS = {
    'order_id',
    'order_date',
    'salesperson_name',
    'qty',
    'GMV',
    'NMV',
    'sub_category',
    'brand_name',
    'dep_name'
}


class TransactionImporter:
    def __init__(self, date_field: str = 'order_date', store_id: str = 'store_1'):
        self.date_field = date_field
        self.store_id = store_id

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f'Missing columns: {missing}')

    def _normalize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        df[self.date_field] = pd.to_datetime(df[self.date_field], errors='coerce')
        if df[self.date_field].isnull().any():
            raise ValueError('Invalid date format in transaction data. Expected YYYY-MM-DD')
        df[self.date_field] = df[self.date_field].dt.strftime('%Y-%m-%d')
        return df

    def parse_csv(self, contents: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(contents))
        self._validate_columns(df)
        return self._normalize_dates(df)

    def parse_json(self, data: Any) -> pd.DataFrame:
        if not isinstance(data, list):
            raise ValueError('JSON payload must be an array')
        df = pd.DataFrame(data)
        self._validate_columns(df)
        return self._normalize_dates(df)

    def _build_transaction_row(self, row: pd.Series) -> Dict[str, Any]:
        return {
            'order_id': str(row['order_id']),
            'order_date': row[self.date_field],
            'salesperson_name': str(row['salesperson_name']),
            'qty': int(row['qty']),
            'GMV': float(row['GMV']),
            'NMV': float(row['NMV']),
            'sub_category': str(row['sub_category']),
            'brand_name': str(row['brand_name']),
            'dep_name': str(row['dep_name'])
        }

    def _pos_key(self, order_date: str) -> str:
        return f'pos:store:{self.store_id}:{order_date}'

    def _pos_aggregates_key(self, order_date: str) -> str:
        return f'pos:store:{self.store_id}:aggregates:{order_date}'

    def store_transactions(self, df: pd.DataFrame, redis_client) -> Dict[str, Any]:
        if df.empty:
            return {
                'transactions_processed': 0,
                'salesperson_ranking': [],
                'aggregates': {}
            }

        aggregates: Dict[str, Dict[str, Any]] = {}
        salesperson_rankings: Dict[str, List[Dict[str, Any]]] = {}

        for _, row in df.iterrows():
            transaction = self._build_transaction_row(row)
            order_date = transaction['order_date']
            key = self._pos_key(order_date)
            redis_client.hset(key, transaction['order_id'], json.dumps(transaction))
            redis_client.expire(key, 86400)

        for order_date, group_df in df.groupby(self.date_field):
            total_orders = int(len(group_df))
            total_gmv = float(group_df['GMV'].sum())
            total_nmv = float(group_df['NMV'].sum())
            avg_basket_size = float(group_df['qty'].mean())
            top_categories = group_df.groupby('sub_category')['GMV'].sum().nlargest(3).index.tolist()
            top_brands = group_df.groupby('brand_name')['GMV'].sum().nlargest(3).index.tolist()

            redis_client.hset(
                self._pos_aggregates_key(order_date),
                mapping={
                    'total_orders': total_orders,
                    'total_gmv': total_gmv,
                    'total_nmv': total_nmv,
                    'avg_basket_size': avg_basket_size,
                    'top_categories': json.dumps(top_categories),
                    'top_brands': json.dumps(top_brands)
                }
            )
            redis_client.expire(self._pos_aggregates_key(order_date), 86400)

            aggregates[order_date] = {
                'total_orders': total_orders,
                'total_gmv': total_gmv,
                'total_nmv': total_nmv,
                'avg_basket_size': avg_basket_size,
                'top_categories': top_categories,
                'top_brands': top_brands
            }

            ranked = (
                group_df.groupby('salesperson_name')
                .agg(order_count=('order_id', 'count'), total_gmv=('GMV', 'sum'))
                .reset_index()
                .sort_values('total_gmv', ascending=False)
            )
            salesperson_rankings[order_date] = ranked.to_dict('records')

        # Record conversion events from POS transactions so funnel conversion counts reflect actual orders.
        try:
            ConversionEngine(redis_client, store_id=self.store_id).record_conversions(df)
        except Exception:
            pass

        return {
            'transactions_processed': int(len(df)),
            'salesperson_ranking': salesperson_rankings,
            'aggregates': aggregates
        }

    async def get_salesperson_ranking(self, redis_client, date: str) -> List[Dict[str, Any]]:
        transactions_hash = await redis_client.hgetall(self._pos_key(date))
        if not transactions_hash:
            return []

        transactions = []
        for value in transactions_hash.values():
            try:
                transactions.append(json.loads(value))
            except json.JSONDecodeError:
                continue

        if not transactions:
            return []

        df = pd.DataFrame(transactions)
        grouped = df.groupby('salesperson_name').agg(
            order_count=('order_id', 'count'),
            total_gmv=('GMV', 'sum')
        ).reset_index()
        grouped['avg_basket'] = grouped['total_gmv'] / grouped['order_count']
        grouped = grouped.sort_values('total_gmv', ascending=False)
        return grouped.to_dict('records')
