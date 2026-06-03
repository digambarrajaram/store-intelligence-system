import React, { useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { usePolling } from '../hooks/usePolling';
import { OccupancyData } from '../types/api';

const fetchOccupancyData = async (): Promise<OccupancyData[]> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/analytics/occupancy/history?window_minutes=60&interval_minutes=5`);
  if (!response.ok) {
    throw new Error('Failed to fetch occupancy data');
  }
  const payload = await response.json();
  const history = payload?.history || (Array.isArray(payload) ? payload : []);
  console.log('[OccupancyChart] API Response:', {
    status: response.status,
    payload,
    historyCount: history.length,
    sampleData: history[0],
  });
  return history;
};

export const OccupancyChart = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data, error, isLoading } = usePolling<OccupancyData[]>(fetchOccupancyData, 30000, {
    immediate: true,
  });

  React.useEffect(() => {
    if (data && data.length > 0) {
      console.log('[OccupancyChart] Data loaded successfully:', {
        count: data.length,
        firstItem: data[0],
        lastItem: data[data.length - 1],
        containerHeight: containerRef.current?.offsetHeight,
      });
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800/50 rounded">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-cyan-400 border-t-transparent mb-3"></div>
          <p className="text-slate-400">Loading occupancy chart...</p>
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
        <p className="text-slate-400">No occupancy data available</p>
      </div>
    );
  }

  const peak = Math.max(...data.map((d) => d.count));

  return (
    <div ref={containerRef} className="w-full h-full flex flex-col">
      <div className="mb-4 flex flex-col gap-3 rounded-3xl border border-slate-700/50 bg-slate-950/80 p-4 text-sm text-slate-300">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>Peak occupancy</span>
          <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">{peak}</span>
        </div>
        <div className="text-xs text-slate-500">Based on the last 60 minutes of entry/exit events.</div>
      </div>
      <ResponsiveContainer width="100%" height="100%" debounce={100}>
        <AreaChart 
          data={data} 
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          syncId="store-metrics"
        >
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#475569" vertical={false} />
          <XAxis 
            dataKey="timestamp" 
            stroke="#94a3b8" 
            style={{ fontSize: '12px' }}
            tickFormatter={(timestamp) => {
              try {
                const date = new Date(timestamp);
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              } catch {
                return timestamp;
              }
            }} 
          />
          <YAxis 
            stroke="#94a3b8" 
            style={{ fontSize: '12px' }}
            domain={[0, peak * 1.1]}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              border: '1px solid #475569', 
              borderRadius: '6px',
              color: '#f1f5f9'
            }} 
            labelStyle={{ color: '#f1f5f9' }}
            formatter={(value) => [`${value} customers`, 'Occupancy']}
          />
          <Area 
            type="monotone" 
            dataKey="count" 
            stroke="#06b6d4" 
            fill="url(#colorCount)" 
            isAnimationActive={false}
            name="Store Occupancy"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

