import React from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Alert } from '../types/api';
import { useEffect, useRef, useState } from 'react';

export const AnomalyFeed = () => {
  const rawWsUrl = import.meta.env.VITE_WS_URL?.trim();
  const wsUrl = rawWsUrl
    ? rawWsUrl.replace(/\/$/, '')
    : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;
  const { data: alertData, error, isConnected } = useWebSocket<Alert>(`${wsUrl}/ws/alerts`);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (alertData) {
      setAlerts((prev) => {
        const newAlerts = [alertData, ...prev];
        // Keep only last 20
        return newAlerts.slice(0, 20);
      });
    }
  }, [alertData]);

  // Scroll to bottom when new alert arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [alerts]);

  if (error) {
    return (
      <div className="h-96 w-full bg-red-500 bg-opacity-20 rounded-lg p-4">
        <div className="h-full flex items-center justify-center text-red-400">
          WebSocket Error: {error}
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="h-96 w-full bg-gray-700 bg-opacity-50 rounded-lg p-4">
        <div className="h-full flex items-center justify-center text-gray-400">
          Connecting to WebSocket...
        </div>
      </div>
    );
  }

  return (
    <div className="h-96 w-full bg-gray-800 bg-opacity-50 rounded-lg p-4 overflow-y-auto">
      <div className="space-y-2">
        {alerts.map((alert) => (
          <div key={alert.id} className="p-3 border-b border-gray-700 last:border-b-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span
                  className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                    alert.severity === 'critical'
                      ? 'bg-red-500 text-white'
                      : alert.severity === 'warning'
                      ? 'bg-yellow-500 text-black'
                      : 'bg-blue-500 text-white'
                  }`}
                >
                  {alert.severity.toUpperCase()}
                </span>
                <div>
                  <p className="font-medium text-white">{alert.type}</p>
                  <p className="text-sm text-gray-400">{alert.zone}</p>
                </div>
              </div>
              <p className="text-xs text-gray-500">
                {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="py-4 text-center text-gray-400">
            No alerts
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};