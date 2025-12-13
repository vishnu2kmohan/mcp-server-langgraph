/**
 * ObservabilityPage
 *
 * Observability page showing traces, logs, and metrics
 * for agent execution monitoring.
 */

import { useEffect, useState } from 'react';
import { Activity, FileText, BarChart3, RefreshCw, Clock } from 'lucide-react';

type ObservabilityTab = 'traces' | 'logs' | 'metrics';

interface Trace {
  id: string;
  name: string;
  duration: number;
  status: 'success' | 'error' | 'running';
  timestamp: string;
  spans: number;
}

interface TracesResponse {
  traces: Trace[];
}

export function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<ObservabilityTab>('traces');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);

  useEffect(() => {
    const loadTraces = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/v1/observability/traces', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to load traces');
        }

        const data: TracesResponse = await response.json();
        setTraces(data.traces);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load traces');
      } finally {
        setIsLoading(false);
      }
    };

    loadTraces();
  }, []);

  const tabs = [
    { id: 'traces' as const, label: 'Traces', icon: Activity },
    { id: 'logs' as const, label: 'Logs', icon: FileText, badge: 'Coming Soon' },
    { id: 'metrics' as const, label: 'Metrics', icon: BarChart3, badge: 'Coming Soon' },
  ];

  const getStatusColor = (status: Trace['status']) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'error': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'running': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Observability
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Monitor traces, logs, and metrics for your AI agents
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="px-6 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
              {tab.badge && (
                <span className="ml-1 px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded-full">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <p className="text-lg mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* Traces Tab */}
            {activeTab === 'traces' && (
              <div className="space-y-4">
                {traces.map((trace) => (
                  <div
                    key={trace.id}
                    className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Activity size={20} className="text-blue-500" />
                        <div>
                          <h3 className="font-medium text-gray-900 dark:text-gray-100">
                            {trace.name}
                          </h3>
                          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                            <span className="flex items-center gap-1">
                              <Clock size={14} />
                              {trace.duration}ms
                            </span>
                            <span>{trace.spans} spans</span>
                            <span>{new Date(trace.timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      </div>
                      <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(trace.status)}`}>
                        {trace.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Logs Tab */}
            {activeTab === 'logs' && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
                <FileText size={48} className="mb-4 opacity-50" />
                <p className="text-lg">Logs Coming Soon</p>
                <p className="text-sm mt-2">Log aggregation and viewing will be available in a future release</p>
              </div>
            )}

            {/* Metrics Tab */}
            {activeTab === 'metrics' && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
                <BarChart3 size={48} className="mb-4 opacity-50" />
                <p className="text-lg">Metrics Coming Soon</p>
                <p className="text-sm mt-2">Metrics dashboard will be available in a future release</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ObservabilityPage;
