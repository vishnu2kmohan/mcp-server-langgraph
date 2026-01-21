export interface ObservabilityPollingConfig {
  traceListActiveMs: number;
  traceListIdleMs: number;
  traceDetailMs: number;
  metricsMs: number;
  logsMs: number;
  alertsMs: number;
}

const DEFAULT_POLLING: ObservabilityPollingConfig = {
  traceListActiveMs: 5000,
  traceListIdleMs: 20000,
  traceDetailMs: 5000,
  metricsMs: 15000,
  logsMs: 15000,
  alertsMs: 10000,
};

function parsePollingInterval(
  value: string | undefined,
  fallback: number,
): number {
  if (value === undefined || value === "") return fallback;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return fallback;
  return Math.floor(parsed);
}

export const OBSERVABILITY_POLLING_CONFIG: ObservabilityPollingConfig = {
  traceListActiveMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_TRACE_LIST_POLLING_ACTIVE_MS,
    DEFAULT_POLLING.traceListActiveMs,
  ),
  traceListIdleMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_TRACE_LIST_POLLING_IDLE_MS,
    DEFAULT_POLLING.traceListIdleMs,
  ),
  traceDetailMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_TRACE_DETAIL_POLLING_MS,
    DEFAULT_POLLING.traceDetailMs,
  ),
  metricsMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_METRICS_POLLING_MS,
    DEFAULT_POLLING.metricsMs,
  ),
  logsMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_LOGS_POLLING_MS,
    DEFAULT_POLLING.logsMs,
  ),
  alertsMs: parsePollingInterval(
    import.meta.env?.VITE_OBSERVABILITY_ALERTS_POLLING_MS,
    DEFAULT_POLLING.alertsMs,
  ),
};
