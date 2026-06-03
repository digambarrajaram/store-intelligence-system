import React from 'react';
import { FunnelChart as RechartsFunnelChart, Funnel, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { usePolling } from '../hooks/usePolling';
import { FunnelData } from '../types/api';

interface RawFunnelResponse {
  entered_store?: number;
  browsed_gt_2min?: number;
  reached_checkout_zone?: number;
  converted?: number;
}

const normalizeFunnelResponse = (payload: any): FunnelData[] => {
  if (Array.isArray(payload)) {
    return payload;
  }

  const raw = payload as RawFunnelResponse;
  return [
    { step: 'Entered Store', value: Number(raw.entered_store || 0) },
    { step: 'Browsed > 2 min', value: Number(raw.browsed_gt_2min || 0) },
    { step: 'Checkout Zone', value: Number(raw.reached_checkout_zone || 0) },
    { step: 'Converted', value: Number(raw.converted || 0) },
  ];
};

const fetchFunnelData = async (): Promise<FunnelData[]> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/analytics/funnel`);
  if (!response.ok) {
    throw new Error('Failed to fetch funnel data');
  }
  const payload = await response.json();
  const funnel = payload?.funnel || (Array.isArray(payload) ? payload : []);
  console.log('[FunnelChart] API Response:', {
    status: response.status,
    payload,
    funnel,
  });
  return normalizeFunnelResponse(funnel);
};

const FUNNEL_COLORS = ['#06b6d4', '#0891b2', '#0e7490', '#164e63'];

export const FunnelChart = () => {
  const { data, error, isLoading } = usePolling<FunnelData[]>(fetchFunnelData, 30000, {
    immediate: true,
  });

  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (data && data.length > 0) {
      console.log('[FunnelChart] Data loaded successfully:', {
        count: data.length,
        data,
        containerHeight: containerRef.current?.offsetHeight,
      });
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800/50 rounded">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-cyan-400 border-t-transparent mb-3"></div>
          <p className="text-slate-400">Loading funnel chart...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-red-500/10 rounded">
        <div className="text-center">
          <p className="text-red-400 font-semibold">Error loading chart</p>
          <p className="text-red-300 text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800/30 rounded">
        <p className="text-slate-400">No funnel data available</p>
      </div>
    );
  }

  const entered = data.find((item) => item.step === 'Entered Store')?.value || 0;
  const converted = data.find((item) => item.step === 'Converted')?.value || 0;
  const conversionRate = entered > 0 ? Math.round((converted / entered) * 100) : 0;

  return (
    <div ref={containerRef} className="w-full h-full flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-3xl border border-slate-700/50 bg-slate-950/80 p-4 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Conversion percentage</p>
          <p className="mt-3 text-3xl font-semibold text-white">{conversionRate}%</p>
          <p className="mt-2 text-xs text-slate-500">of store entrants completed a purchase.</p>
        </div>
        <div className="rounded-3xl border border-slate-700/50 bg-slate-950/80 p-4 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Checkout throughput</p>
          <p className="mt-3 text-3xl font-semibold text-white">{data.find((item) => item.step === 'Checkout Zone')?.value || 0}</p>
          <p className="mt-2 text-xs text-slate-500">Customers reached checkout zone in the selected window.</p>
        </div>
      </div>

      <div className="flex-1 min-h-[260px]">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <RechartsFunnelChart data={data} margin={{ top: 20, right: 160, bottom: 20, left: 20 }}>
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#0f172a', 
                border: '1px solid #475569', 
                borderRadius: '6px',
                color: '#f1f5f9'
              }} 
              labelStyle={{ color: '#f1f5f9' }}
              formatter={(value) => [`${value} customers`, 'Count']}
            />
            <Funnel 
              dataKey="value" 
              data={data}
              isAnimationActive={false}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={FUNNEL_COLORS[index % FUNNEL_COLORS.length]} />
              ))}
            </Funnel>
          </RechartsFunnelChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
