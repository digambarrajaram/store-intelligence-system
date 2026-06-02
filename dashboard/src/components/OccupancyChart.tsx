import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Line } from 'recharts';
import { usePolling } from '../hooks/usePolling';
import { OccupancyData } from '../types/api';

const fetchOccupancyData = async (): Promise<OccupancyData[]> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/metrics?window_minutes=60`);
  if (!response.ok) {
    throw new Error('Failed to fetch occupancy data');
  }
  return response.json();
};

export const OccupancyChart = () => {
  const { data, error, isLoading } = usePolling<OccupancyData[]>(fetchOccupancyData, 30000, {
    immediate: true,
  });

  if (isLoading) {
    return (
      <div className="h-96 w-full bg-gray-700 bg-opacity-50 rounded-lg p-4 animate-pulse">
        <div className="h-full flex items-center justify-center text-gray-400">Loading occupancy chart...</div>
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

  // Calculate peak for the peak line
  const peak = Math.max(...data.map((d) => d.count));
  const dataWithPeak = data.map((d) => ({ ...d, peak }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={dataWithPeak}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="timestamp" tickFormatter={(timestamp) => {
          const date = new Date(timestamp);
          return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }} />
        <YAxis />
        <Tooltip />
        <Area type="monotone" dataKey="count" stroke="#8884d8" fillOpacity={0.1} />
        <Line type="monotone" dataKey="count" stroke="#8884d8" strokeWidth={2} />
        {/* Peak line */}
        <Line type="monotone" dataKey="peak" stroke="#ff0000" strokeWidth={1} strokeDasharray="4 4" />
      </AreaChart>
    </ResponsiveContainer>
  );
};

