import React from 'react';
import { FunnelChart as RechartsFunnelChart, Funnel, Tooltip, ResponsiveContainer, Label } from 'recharts';
import { usePolling } from '../hooks/usePolling';
import { FunnelData } from '../types/api';

const fetchFunnelData = async (): Promise<FunnelData[]> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/funnel`);
  if (!response.ok) {
    throw new Error('Failed to fetch funnel data');
  }
  return response.json();
};

export const FunnelChart = () => {
  const { data, error, isLoading } = usePolling<FunnelData[]>(fetchFunnelData, 30000, {
    immediate: true,
  });

  if (isLoading) {
    return (
      <div className="h-96 w-full bg-gray-700 bg-opacity-50 rounded-lg p-4 animate-pulse">
        <div className="h-full flex items-center justify-center text-gray-400">Loading funnel chart...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-96 w-full bg-red-500 bg-opacity-20 rounded-lg p-4">
        <div className="h-full flex items-center justify-center text-red-400">
          Error: {error}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-96 w-full bg-gray-800 bg-opacity-50 rounded-lg p-4">
        <div className="h-full flex items-center justify-center text-gray-400">
          No data available
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RechartsFunnelChart data={data}>
        <Tooltip />
        <Label
          position="insideLeft"
          formatter={(value, name) => `${name}: ${value}`}
        />
        <Funnel dataKey="value" nameKey="step" />
      </RechartsFunnelChart>
    </ResponsiveContainer>
  );
};