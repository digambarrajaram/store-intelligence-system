import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { KPIData } from '../types/api';

const fetchKPIData = async (): Promise<KPIData> => {
  const apiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.trim() : '/api/v1';
  const response = await fetch(`${apiUrl}/kpis`);
  if (!response.ok) {
    throw new Error('Failed to fetch KPI data');
  }
  return response.json();
};

export const KPICards = () => {
  const { data, error, isLoading } = usePolling<KPIData>(fetchKPIData, 30000, {
    immediate: true,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-gray-700 bg-opacity-50 rounded-lg p-4 animate-pulse">
            <h3 className="text-sm font-medium text-gray-400">Loading...</h3>
            <p className="text-2xl font-bold text-white">--</p>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-red-500 bg-opacity-20 rounded-lg p-4">
            <h3 className="text-sm font-medium text-red-400">Error</h3>
            <p className="text-xl font-bold text-red-200">{error}</p>
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return <div className="grid grid-cols-4 gap-4"></div>;
  }

  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Current Occupancy */}
      <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400">Current Occupancy</h3>
        <div className="flex items-baseline mt-2">
          <p className="text-4xl font-bold text-white">{data.currentOccupancy}</p>
          <span className="ml-2 text-lg">
            {data.occupancyTrend === 'up' ? (
              <span className="text-green-400">▲</span>
            ) : data.occupancyTrend === 'down' ? (
              <span className="text-red-400">▼</span>
            ) : (
              <span className="text-gray-400">―</span>
            )}
          </span>
        </div>
      </div>

      {/* Total Entries Today */}
      <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400">Total Entries Today</h3>
        <p className="mt-2 text-2xl font-bold text-white">{data.totalEntriesToday}</p>
        {/* Sparkline placeholder */}
        <div className="mt-2 h-4 w-full bg-gray-700 rounded">
          <div className="h-full bg-blue-500 rounded" style={{ width: '70%' }}></div>
        </div>
      </div>

      {/* Conversion Rate */}
      <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400">Conversion Rate</h3>
        <p className="mt-2 text-2xl font-bold text-white">
          {data.conversionRate}%
        </p>
        <p className="mt-1 text-sm text-gray-400">
          (footfall vs POS transactions)
        </p>
      </div>

      {/* Active Anomalies */}
      <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400">Active Anomalies</h3>
        <div className="mt-2 flex items-center">
          <span
            className={`px-2 py-1 text-xs font-bold rounded-full ${
              data.activeAnomalies > 0
                ? 'bg-red-500 text-white'
                : 'bg-green-500 text-white'
            }`}
          >
            {data.activeAnomalies}
          </span>
          <p className="ml-2 text-sm text-white">
            {data.activeAnomalies > 0 ? 'Alerts active' : 'All clear'}
          </p>
        </div>
      </div>
    </div>
  );
};