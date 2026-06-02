import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { SalespersonData } from '../types/api';

const fetchSalespersonData = async (): Promise<SalespersonData[]> => {
  // Get today's date in YYYY-MM-DD format
  const today = new Date().toISOString().split('T')[0];
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
      // For 'id' or any other key, fallback to name sorting for consistency
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
      <div className="h-96 w-full bg-gray-700 bg-opacity-50 rounded-lg p-4 animate-pulse">
        <div className="h-full flex items-center justify-center text-gray-400">Loading leaderboard...</div>
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
    <div className="h-96 w-full bg-gray-800 bg-opacity-50 rounded-lg p-4 overflow-y-auto">
      <table className="min-w-full divide-y divide-gray-700">
        <thead className="bg-gray-900">
          <tr>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer"
              onClick={() => requestSort('name')}
            >
              Name
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer"
              onClick={() => requestSort('gmv')}
            >
              GMV
              {sortConfig?.key === 'gmv' ? (
                sortConfig.direction === 'asc' ? ' ↑' : ' ↓'
              ) : ''}
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer"
              onClick={() => requestSort('transactions')}
            >
              Transactions
              {sortConfig?.key === 'transactions' ? (
                sortConfig.direction === 'asc' ? ' ↑' : ' ↓'
              ) : ''}
            </th>
          </tr>
        </thead>
        <tbody className="bg-gray-800 divide-y divide-gray-700">
          {sortedData.map((person) => (
            <tr key={person.id} className="hover:bg-gray-700">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                {person.name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                ${person.gmv.toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                {person.transactions}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};