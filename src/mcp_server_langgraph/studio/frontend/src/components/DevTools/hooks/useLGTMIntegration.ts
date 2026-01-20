/**
 * useLGTMIntegration Hook
 *
 * Multi-cloud aware LGTM stack (Loki, Grafana, Tempo, Mimir) integration
 * with graceful fallback for AWS+EKS, GCP+GKE, Azure+AKS, OpenShift/Rancher.
 *
 * Features:
 * - Configuration detection from environment variables
 * - Provider/platform detection (docker-compose, kubernetes, aws, gcp, azure)
 * - URL builders for Grafana dashboards, traces, logs, metrics, alerts
 * - Graceful fallback when services are not configured
 */

import { useMemo, useCallback } from "react";

// =============================================================================
// Types
// =============================================================================

export type LGTMProvider = "docker-compose" | "kubernetes" | "unknown";
export type LGTMPlatform = "aws" | "gcp" | "azure" | "openshift" | "rancher" | "unknown";

export interface LGTMConfig {
  grafanaUrl: string;
  lokiUrl: string;
  tempoUrl: string;
  mimirUrl: string;
  provider: LGTMProvider;
  platform: LGTMPlatform;
}

export interface TimeRange {
  from: number;
  to: number;
}

export interface UseLGTMIntegrationReturn {
  /** Full configuration */
  config: LGTMConfig;
  /** Whether any LGTM service is available */
  isAvailable: boolean;
  /** Whether Grafana is configured */
  canOpenInGrafana: boolean;
  /** Whether Loki is configured */
  canOpenInLoki: boolean;
  /** Whether Tempo is configured */
  canOpenInTempo: boolean;
  /** Get URL for a Grafana dashboard */
  getGrafanaDashboardUrl: (dashboardUid: string) => string | null;
  /** Get URL for viewing a trace in Tempo via Grafana Explore */
  getTraceUrl: (traceId: string) => string | null;
  /** Get URL for viewing logs in Loki via Grafana Explore */
  getLogsUrl: (query: string, timeRange?: TimeRange) => string | null;
  /** Get URL for viewing metrics in Mimir via Grafana Explore */
  getMetricsUrl: (query: string) => string | null;
  /** Get URL for viewing an alert in Grafana Alerting */
  getAlertUrl: (alertId: string) => string | null;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Normalize a URL by removing trailing slashes
 */
function normalizeUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

/**
 * Check if a URL is valid/non-empty
 */
function isValidUrl(url: string | undefined): boolean {
  return !!url && url.trim().length > 0;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * useLGTMIntegration Hook
 *
 * Provides multi-cloud LGTM stack integration with graceful fallback.
 *
 * @example
 * ```tsx
 * const {
 *   isAvailable,
 *   canOpenInGrafana,
 *   getTraceUrl,
 *   getLogsUrl,
 * } = useLGTMIntegration();
 *
 * // Open trace in Grafana Tempo
 * if (canOpenInGrafana) {
 *   const url = getTraceUrl("abc123");
 *   if (url) window.open(url, "_blank");
 * }
 * ```
 */
export function useLGTMIntegration(): UseLGTMIntegrationReturn {
  // Read configuration from environment
  const config = useMemo<LGTMConfig>(() => {
    const grafanaUrl = import.meta.env.VITE_GRAFANA_URL ?? "";
    const lokiUrl = import.meta.env.VITE_LOKI_URL ?? "";
    const tempoUrl = import.meta.env.VITE_TEMPO_URL ?? "";
    const mimirUrl = import.meta.env.VITE_MIMIR_URL ?? "";
    const provider = (import.meta.env.VITE_CLOUD_PROVIDER as LGTMProvider) ?? "unknown";
    const platform = (import.meta.env.VITE_CLOUD_PLATFORM as LGTMPlatform) ?? "unknown";

    return {
      grafanaUrl: normalizeUrl(grafanaUrl),
      lokiUrl: normalizeUrl(lokiUrl),
      tempoUrl: normalizeUrl(tempoUrl),
      mimirUrl: normalizeUrl(mimirUrl),
      provider: provider || "unknown",
      platform: platform || "unknown",
    };
  }, []);

  // Derived availability flags
  const canOpenInGrafana = isValidUrl(config.grafanaUrl);
  const canOpenInLoki = isValidUrl(config.lokiUrl);
  const canOpenInTempo = isValidUrl(config.tempoUrl);

  const isAvailable = canOpenInGrafana || canOpenInLoki || canOpenInTempo;

  // URL Builders

  /**
   * Get URL for a Grafana dashboard
   */
  const getGrafanaDashboardUrl = useCallback(
    (dashboardUid: string): string | null => {
      if (!canOpenInGrafana) return null;
      return `${config.grafanaUrl}/d/${dashboardUid}`;
    },
    [config.grafanaUrl, canOpenInGrafana],
  );

  /**
   * Get URL for viewing a trace in Tempo via Grafana Explore
   */
  const getTraceUrl = useCallback(
    (traceId: string): string | null => {
      if (!traceId || traceId.trim() === "") return null;
      if (!canOpenInTempo || !canOpenInGrafana) return null;

      // Build Grafana Explore URL for Tempo trace
      const params = new URLSearchParams({
        orgId: "1",
        left: JSON.stringify({
          datasource: "tempo",
          queries: [{ refId: "A", queryType: "traceId", traceId }],
          range: { from: "now-1h", to: "now" },
        }),
      });

      return `${config.grafanaUrl}/explore?${params.toString()}`;
    },
    [config.grafanaUrl, canOpenInTempo, canOpenInGrafana],
  );

  /**
   * Get URL for viewing logs in Loki via Grafana Explore
   */
  const getLogsUrl = useCallback(
    (query: string, timeRange?: TimeRange): string | null => {
      if (!query || query.trim() === "") return null;
      if (!canOpenInLoki || !canOpenInGrafana) return null;

      const params = new URLSearchParams({
        orgId: "1",
        left: JSON.stringify({
          datasource: "loki",
          queries: [{ refId: "A", expr: query }],
          range: timeRange
            ? { from: String(timeRange.from), to: String(timeRange.to) }
            : { from: "now-1h", to: "now" },
        }),
      });

      // Add time range as separate params if provided
      if (timeRange) {
        params.set("from", String(timeRange.from));
        params.set("to", String(timeRange.to));
      }

      return `${config.grafanaUrl}/explore?${params.toString()}`;
    },
    [config.grafanaUrl, canOpenInLoki, canOpenInGrafana],
  );

  /**
   * Get URL for viewing metrics in Mimir via Grafana Explore
   */
  const getMetricsUrl = useCallback(
    (query: string): string | null => {
      if (!isValidUrl(config.mimirUrl) || !canOpenInGrafana) return null;

      const params = new URLSearchParams({
        orgId: "1",
        left: JSON.stringify({
          datasource: "mimir",
          queries: [{ refId: "A", expr: query }],
          range: { from: "now-1h", to: "now" },
        }),
      });

      return `${config.grafanaUrl}/explore?${params.toString()}`;
    },
    [config.grafanaUrl, config.mimirUrl, canOpenInGrafana],
  );

  /**
   * Get URL for viewing an alert in Grafana Alerting
   */
  const getAlertUrl = useCallback(
    (alertId: string): string | null => {
      if (!canOpenInGrafana) return null;
      return `${config.grafanaUrl}/alerting/list?search=${alertId}`;
    },
    [config.grafanaUrl, canOpenInGrafana],
  );

  return {
    config,
    isAvailable,
    canOpenInGrafana,
    canOpenInLoki,
    canOpenInTempo,
    getGrafanaDashboardUrl,
    getTraceUrl,
    getLogsUrl,
    getMetricsUrl,
    getAlertUrl,
  };
}

export default useLGTMIntegration;
