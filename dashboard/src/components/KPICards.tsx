import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { KPIData } from '../types/api';

const fetchKPIData = async (): Promise<KPIData> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/analytics/kpis`);
  if (!response.ok) {
    throw new Error('Failed to fetch KPI data');
  }
  return response.json();
};

export const KPICards = () => {
  const { data, error, isLoading } = usePolling<KPIData>(fetchKPIData, 30000, {
    immediate: true,
  });

  const cardClass = 'rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl shadow-slate-950/20 backdrop-blur-xl';

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`${cardClass} animate-pulse`}>
            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Loading...</h3>
            <p className="mt-4 text-4xl font-bold text-slate-100">--</p>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-3xl border border-red-500/20 bg-red-500/10 p-5 shadow-lg shadow-red-900/10">
            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-red-300">Error</h3>
            <p className="mt-4 text-xl font-semibold text-red-100">{error}</p>
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4" />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div className={cardClass}>
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Current Occupancy</h3>
        <div className="mt-4 flex items-end gap-3">
          <p className="text-4xl font-bold text-white">{data.currentOccupancy}</p>
          <span className="text-2xl">
            {data.occupancyTrend === 'up' ? (
              <span className="text-emerald-400">▲</span>
            ) : data.occupancyTrend === 'down' ? (
              <span className="text-rose-400">▼</span>
            ) : (
              <span className="text-slate-500">―</span>
            )}
          </span>
        </div>
        <p className="mt-3 text-sm text-slate-500">Live customers currently in store.</p>
      </div>

      <div className={cardClass}>
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Total Entries Today</h3>
        <p className="mt-4 text-4xl font-bold text-white">{data.totalEntriesToday}</p>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-900">
          <div className="h-full w-3/4 rounded-full bg-cyan-400" />
        </div>
        <p className="mt-3 text-sm text-slate-500">Relative traffic volume vs target.</p>
      </div>

      <div className={cardClass}>
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Conversion Rate</h3>
        <p className="mt-4 text-4xl font-bold text-white">{data.conversionRate}%</p>
        <p className="mt-3 text-sm text-slate-500">Footfall converted into purchases.</p>
      </div>

      <div className={cardClass}>
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Active Anomalies</h3>
        <div className="mt-4 flex items-center gap-3">
          <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${data.activeAnomalies > 0 ? 'bg-rose-500/10 text-rose-300' : 'bg-emerald-500/10 text-emerald-300'}`}>
            {data.activeAnomalies}
          </span>
          <span className="text-sm text-slate-500">{data.activeAnomalies > 0 ? 'Attention needed' : 'All clear'}</span>
        </div>
      </div>
    </div>
  );
};