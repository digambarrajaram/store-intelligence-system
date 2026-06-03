import json
import os
from fastapi import APIRouter, HTTPException, Query, Request
from redis import Redis
from datetime import datetime

from services.transaction_importer import TransactionImporter

router = APIRouter()

@router.get("/insights/correlation")
async def get_correlation_insights(
    request: Request,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    store_id: str = Query("store_1"),
):
    r: Redis = request.app.state.redis
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    # Get vision footfall for this store
    footfall = int(await r.get(f"store:{store_id}:vision:footfall:{date}") or 0)

    # Get POS aggregates for this store
    agg_data = await r.hgetall(f"pos:store:{store_id}:aggregates:{date}")
    if not agg_data:
        raise HTTPException(status_code=404, detail=f"No POS data found for store {store_id} on date {date}")

    transactions = int(agg_data.get("total_orders", 0))
    total_gmv = float(agg_data.get("total_gmv", 0))
    avg_basket_gmv = total_gmv / transactions if transactions > 0 else 0.0
    conversion_rate_pct = (transactions / footfall * 100) if footfall > 0 else 0.0
    revenue_per_visitor = total_gmv / footfall if footfall > 0 else 0.0
    top_categories = json.loads(agg_data.get("top_categories", "[]"))
    top_performing_category = top_categories[0] if top_categories else ""

    if conversion_rate_pct > 30:
        insight = f"Conversion rate is {conversion_rate_pct:.2f}% — exceeds the 30% target."
    elif conversion_rate_pct > 20:
        insight = f"Conversion rate is {conversion_rate_pct:.2f}% — above average but below the 30% target."
    else:
        insight = f"Conversion rate is {conversion_rate_pct:.2f}% — below target; review footfall quality or sales strategy."

    return {
        "store_id": store_id,
        "date": date,
        "footfall": footfall,
        "transactions": transactions,
        "conversion_rate_pct": round(conversion_rate_pct, 2),
        "revenue_per_visitor": round(revenue_per_visitor, 2),
        "avg_basket_gmv": round(avg_basket_gmv, 2),
        "top_performing_category": top_performing_category,
        "insight": insight
    }


@router.get("/insights/salesperson")
async def get_salesperson_leaderboard(
    request: Request,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    store_id: str = Query("store_1"),
):
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    r: Redis = request.app.state.redis
    ranking = await TransactionImporter(store_id=store_id).get_salesperson_ranking(r, date)
    return ranking or []
