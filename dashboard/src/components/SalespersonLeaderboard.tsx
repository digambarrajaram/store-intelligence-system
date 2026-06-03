import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { SalespersonData } from '../types/api';

const fetchSalespersonData = async (): Promise<SalespersonData[]> => {
  // Get today's date in YYYY-MM-DD format using LOCAL timezone
  // toISOString() returns UTC date which can be off by a day for timezones like Asia/Calcutta (UTC+5:30)
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/insights/salesperson?date=${today}`);
  if (!response.ok) {
    throw new Error('Failed to fetch salesperson data');
  }
  const data = await response.json();
  // Map API response to match SalespersonData interface
  return data.map((person: any, index: number) => ({
    id: person.salesperson_name || `person_${index}`, // Use name as ID or generate fallback
    name: person.salesperson_name,
    gmv: person.total_gmv,
    transactions: person.order_count
  }));
};

export const SalespersonLeaderboard = () => {
  const { data, error, isLoading } = usePolling<SalespersonData[]>(fetchSalespersonData, 30000, {
    immediate: true,
  });

  React.useEffect(() => {
    if (data) {
      console.log('[SalespersonLeaderboard] Data loaded:', { count: data.length, data });
    }
  }, [data]);

  const [sortConfig, setSortConfig] = React.useState<{ key: keyof SalespersonData; direction: 'asc' | 'desc' } | null>(null);

  const sortedData = React.useMemo(() => {
    if (!sortConfig || !data) return data;
    return [...data].sort((a, b) => {
      if (sortConfig.key === 'gmv') {
        return sortConfig.direction === 'asc'
          ? a.gmv - b.gmv
          : b.gmv - a.gmv;
      }
      if (sortConfig.key === 'transactions') {
        return sortConfig.direction === 'asc'
          ? a.transactions - b.transactions
          : b.transactions - a.transactions;
      }
      if (sortConfig.key === 'name') {
        return sortConfig.direction === 'asc'
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      }
      return sortConfig.direction === 'asc'
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name);
    });
  }, [data, sortConfig]);

  const requestSort = (key: keyof SalespersonData) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800/50 rounded">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-cyan-400 border-t-transparent mb-3"></div>
          <p className="text-slate-400">Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-red-500/10 rounded">
        <div className="text-center">
          <p className="text-red-400 font-semibold">Error loading data</p>
          <p className="text-red-300 text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!sortedData || sortedData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800/30 rounded">
        <p className="text-slate-400">No salesperson data available</p>
      </div>
    );
  }

  const topPerformer = sortedData[0];

  return (
    <div className="w-full h-full flex flex-col bg-slate-800/20 rounded overflow-hidden">
      <div className="p-4">
        <div className="rounded-3xl bg-slate-950/80 p-4 ring-1 ring-cyan-400/15 backdrop-blur-xl">
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Top Performer</p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-slate-400">Best daily GMV</p>
              <p className="mt-1 text-2xl font-semibold text-white">{topPerformer.name}</p>
            </div>
            <div className="rounded-2xl bg-cyan-400/10 px-3 py-2 text-sm font-semibold text-cyan-200">
              ${topPerformer.gmv.toLocaleString()} | {topPerformer.transactions} orders
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full divide-y divide-slate-700">
          <thead className="sticky top-0 bg-slate-950/60 backdrop-blur-sm">
            <tr>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => requestSort('name')}
                  className="text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-300 transition-colors flex items-center gap-1"
                >
                  Salesperson
                  {sortConfig?.key === 'name' && (
                    <span className="text-cyan-400">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                  )}
                </button>
              </th>
              <th className="px-4 py-3 text-right">
                <button
                  onClick={() => requestSort('gmv')}
                  className="text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-300 transition-colors flex items-center justify-end gap-1 w-full"
                >
                  GMV
                  {sortConfig?.key === 'gmv' && (
                    <span className="text-cyan-400">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                  )}
                </button>
              </th>
              <th className="px-4 py-3 text-right">
                <button
                  onClick={() => requestSort('transactions')}
                  className="text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-300 transition-colors flex items-center justify-end gap-1 w-full"
                >
                  Orders
                  {sortConfig?.key === 'transactions' && (
                    <span className="text-cyan-400">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                  )}
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {sortedData.map((person, rank) => (
              <tr key={person.id} className={`${rank === 0 ? 'bg-slate-700/40' : 'hover:bg-slate-700/20'} transition-colors`}>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full ${rank === 0 ? 'bg-gradient-to-br from-emerald-400 to-cyan-500' : 'bg-slate-700'} flex items-center justify-center text-xs font-bold text-white`}>
                      {rank + 1}
                    </div>
                    <span className="text-sm font-medium text-white">{person.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className={`text-sm font-semibold ${rank === 0 ? 'text-emerald-300' : 'text-cyan-300'}`}>${person.gmv.toLocaleString()}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className="text-sm text-slate-300">{person.transactions}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};