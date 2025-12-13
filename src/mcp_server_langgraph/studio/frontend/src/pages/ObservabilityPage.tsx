/**
 * ObservabilityPage
 *
 * Observability page showing traces, logs, and metrics
 * for agent execution monitoring.
 */

import { useEffect, useState } from 'react';
import { Activity, FileText, BarChart3, RefreshCw, Filter, Clock } from 'lucide-react';

type ObservabilityTab = 'traces' | 'logs' | 'metrics';

interface Trace {
  id: string;
  name: string;
  duration: number;
  status: 'success' | 'error' | 'running';
  timestamp: Date;
  spans: number;
}

interface Log {
  id: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: Date;
  source: string;
}

interface Metric {
  name: string;
  value: number;
  unit: string;
  change: number;
}

export function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<ObservabilityTab>('traces');
  const [isLoading, setIsLoading] = useState(true);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);

  useEffect(() => {
    // Simulate loading data
    const loadData = async () => {
      setIsLoading(true);
      await new Promise((r) => setTimeout(r, 500));

      // Mock data
      setTraces([
        { id: '1', name: 'chat/completion', duration: 1234, status: 'success', timestamp: new Date(), spans: 5 },
        { id: '2', name: 'tools/execute', duration: 567, status: 'success', timestamp: new Date(Date.now() - 60000), spans: 3 },
        { id: '3', name: 'workflow/run', duration: 2345, status: 'running', timestamp: new Date(Date.now() - 120000), spans: 8 },
      ]);

      setLogs([
        { id: '1', level: 'info', message: 'Session started', timestamp: new Date(), source: 'session-manager' },
        { id: '2', level: 'debug', message: 'Loading tools from MCP server', timestamp: new Date(Date.now() - 30000), source: 'mcp-client' },
        { id: '3', level: 'warn', message: 'Rate limit approaching (80%)', timestamp: new Date(Date.now() - 60000), source: 'rate-limiter' },
        { id: '4', level: 'error', message: 'Tool execution timeout', timestamp: new Date(Date.now() - 90000), source: 'tool-executor' },
      ]);

      setMetrics([
        { name: 'Requests / min', value: 42, unit: 'req/min', change: 5.2 },
        { name: 'Avg Response Time', value: 234, unit: 'ms', change: -12.5 },
        { name: 'Error Rate', value: 0.5, unit: '%', change: -0.2 },
        { name: 'Active Sessions', value: 8, unit: '', change: 2 },
      ]);

      setIsLoading(false);
    };

    loadData();
  }, []);

  const tabs = [
    { id: 'traces' as const, label: 'Traces', icon: Activity },
    { id: 'logs' as const, label: 'Logs', icon: FileText },
    { id: 'metrics' as const, label: 'Metrics', icon: BarChart3 },
  ];

  const getLogLevelColor = (level: Log['level']) => {
    switch (level) {
      case 'debug': return 'text-gray-500';
      case 'info': return 'text-blue-500';
      case 'warn': return 'text-yellow-500';
      case 'error': return 'text-red-500';
    }
  };

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
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Filter size={16} className="text-gray-400" />
                    <span className="text-sm text-gray-600 dark:text-gray-300">
                      Showing all levels
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-gray-100 dark:divide-gray-700 font-mono text-sm">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <div className="flex items-start gap-3">
                        <span className={`uppercase text-xs font-bold ${getLogLevelColor(log.level)}`}>
                          {log.level}
                        </span>
                        <span className="text-gray-400 text-xs">
                          {log.timestamp.toLocaleTimeString()}
                        </span>
                        <span className="text-gray-500 text-xs">
                          [{log.source}]
                        </span>
                        <span className="text-gray-900 dark:text-gray-100 flex-1">
                          {log.message}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metrics Tab */}
            {activeTab === 'metrics' && (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {metrics.map((metric) => (
                  <div
                    key={metric.name}
                    className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {metric.name}
                    </h3>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                        {metric.value}
                      </span>
                      {metric.unit && (
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          {metric.unit}
                        </span>
                      )}
                    </div>
                    <div className="mt-2">
                      <span
                        className={`text-sm ${
                          metric.change >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {metric.change >= 0 ? '+' : ''}
                        {metric.change}%
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                        vs last hour
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ObservabilityPage;
