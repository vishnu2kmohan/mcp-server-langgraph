/**
 * useLGTMIntegration Hook Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests LGTM stack (Loki, Grafana, Tempo, Mimir) integration with graceful fallback.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";

import { useLGTMIntegration } from "./useLGTMIntegration";

// =============================================================================
// Mock Environment Variables using vi.stubEnv
// =============================================================================

function mockEnv(env: Record<string, string>) {
  Object.entries(env).forEach(([key, value]) => {
    vi.stubEnv(key, value);
  });
}

// =============================================================================
// Basic Configuration Tests
// =============================================================================

describe("useLGTMIntegration", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("configuration detection", () => {
    it("should detect when LGTM stack is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "",
        VITE_LOKI_URL: "",
        VITE_TEMPO_URL: "",
        VITE_MIMIR_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(false);
      expect(result.current.canOpenInGrafana).toBe(false);
      expect(result.current.canOpenInLoki).toBe(false);
      expect(result.current.canOpenInTempo).toBe(false);
    });

    it("should detect when Grafana is configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(true);
      expect(result.current.canOpenInGrafana).toBe(true);
      expect(result.current.config.grafanaUrl).toBe("https://grafana.example.com");
    });

    it("should detect when Loki is configured", () => {
      mockEnv({
        VITE_LOKI_URL: "https://loki.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(true);
      expect(result.current.canOpenInLoki).toBe(true);
      expect(result.current.config.lokiUrl).toBe("https://loki.example.com");
    });

    it("should detect when Tempo is configured", () => {
      mockEnv({
        VITE_TEMPO_URL: "https://tempo.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(true);
      expect(result.current.canOpenInTempo).toBe(true);
      expect(result.current.config.tempoUrl).toBe("https://tempo.example.com");
    });

    it("should detect when all LGTM services are configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "https://loki.example.com",
        VITE_TEMPO_URL: "https://tempo.example.com",
        VITE_MIMIR_URL: "https://mimir.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(true);
      expect(result.current.canOpenInGrafana).toBe(true);
      expect(result.current.canOpenInLoki).toBe(true);
      expect(result.current.canOpenInTempo).toBe(true);
    });
  });

  // ===========================================================================
  // Provider Detection Tests
  // ===========================================================================

  describe("provider detection", () => {
    it("should detect docker-compose provider", () => {
      mockEnv({
        VITE_GRAFANA_URL: "http://localhost:3000",
        VITE_CLOUD_PROVIDER: "docker-compose",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.provider).toBe("docker-compose");
    });

    it("should detect kubernetes provider", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.k8s.internal",
        VITE_CLOUD_PROVIDER: "kubernetes",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.provider).toBe("kubernetes");
    });

    it("should detect AWS platform", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_CLOUD_PLATFORM: "aws",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.platform).toBe("aws");
    });

    it("should detect GCP platform", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_CLOUD_PLATFORM: "gcp",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.platform).toBe("gcp");
    });

    it("should detect Azure platform", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_CLOUD_PLATFORM: "azure",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.platform).toBe("azure");
    });

    it("should default to unknown when provider not specified", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.config.provider).toBe("unknown");
      expect(result.current.config.platform).toBe("unknown");
    });
  });

  // ===========================================================================
  // URL Builder Tests - Grafana Dashboard
  // ===========================================================================

  describe("getGrafanaDashboardUrl", () => {
    it("should return dashboard URL when Grafana is configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getGrafanaDashboardUrl("abc123");
      expect(url).toBe("https://grafana.example.com/d/abc123");
    });

    it("should return null when Grafana is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getGrafanaDashboardUrl("abc123");
      expect(url).toBeNull();
    });

    it("should handle trailing slash in Grafana URL", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com/",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getGrafanaDashboardUrl("abc123");
      expect(url).toBe("https://grafana.example.com/d/abc123");
    });
  });

  // ===========================================================================
  // URL Builder Tests - Trace
  // ===========================================================================

  describe("getTraceUrl", () => {
    it("should return Tempo explore URL when configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_TEMPO_URL: "https://tempo.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getTraceUrl("abc123def456");
      expect(url).toContain("grafana.example.com");
      expect(url).toContain("abc123def456");
    });

    it("should return null when Tempo is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_TEMPO_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getTraceUrl("abc123def456");
      expect(url).toBeNull();
    });

    it("should use Grafana explore for trace viewing", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_TEMPO_URL: "https://tempo.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getTraceUrl("trace-id-123");
      expect(url).toContain("/explore");
    });
  });

  // ===========================================================================
  // URL Builder Tests - Logs
  // ===========================================================================

  describe("getLogsUrl", () => {
    it("should return Loki explore URL when configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "https://loki.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getLogsUrl('{app="myapp"}');
      expect(url).toContain("grafana.example.com");
      expect(url).toContain("/explore");
    });

    it("should encode query in URL", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "https://loki.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const query = '{app="myapp", level="error"}';
      const url = result.current.getLogsUrl(query);

      // Query is embedded in JSON structure within URL params
      // Decode and verify the query is present
      expect(url).toBeDefined();
      const urlObj = new URL(url!);
      const leftParam = urlObj.searchParams.get("left");
      expect(leftParam).toBeDefined();
      const parsed = JSON.parse(leftParam!);
      expect(parsed.queries[0].expr).toBe(query);
    });

    it("should return null when Loki is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getLogsUrl('{app="myapp"}');
      expect(url).toBeNull();
    });

    it("should include time range when provided", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "https://loki.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getLogsUrl('{app="myapp"}', {
        from: 1704067200000,
        to: 1704153600000,
      });
      expect(url).toContain("from=");
      expect(url).toContain("to=");
    });
  });

  // ===========================================================================
  // URL Builder Tests - Metrics
  // ===========================================================================

  describe("getMetricsUrl", () => {
    it("should return Grafana explore URL for metrics when Mimir configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_MIMIR_URL: "https://mimir.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getMetricsUrl("rate(http_requests_total[5m])");
      expect(url).toContain("grafana.example.com");
      expect(url).toContain("/explore");
    });

    it("should return null when Mimir is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_MIMIR_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getMetricsUrl("rate(http_requests_total[5m])");
      expect(url).toBeNull();
    });
  });

  // ===========================================================================
  // URL Builder Tests - Alerts
  // ===========================================================================

  describe("getAlertUrl", () => {
    it("should return Grafana alerting URL when configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getAlertUrl("alert-123");
      expect(url).toBe("https://grafana.example.com/alerting/list?search=alert-123");
    });

    it("should return null when Grafana is not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getAlertUrl("alert-123");
      expect(url).toBeNull();
    });
  });

  // ===========================================================================
  // Graceful Fallback Tests
  // ===========================================================================

  describe("graceful fallback", () => {
    it("should return relative URLs when base URL not configured", () => {
      mockEnv({
        VITE_GRAFANA_URL: "",
        VITE_LOKI_URL: "configured",
        VITE_TEMPO_URL: "configured",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      // Should still be available even without absolute Grafana URL
      expect(result.current.canOpenInLoki).toBe(true);
      expect(result.current.canOpenInTempo).toBe(true);
    });

    it("should handle malformed URLs gracefully", () => {
      mockEnv({
        VITE_GRAFANA_URL: "not-a-valid-url",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      // Should not throw, should handle gracefully
      expect(() => result.current.getGrafanaDashboardUrl("abc123")).not.toThrow();
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("edge cases", () => {
    it("should handle empty trace ID", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_TEMPO_URL: "https://tempo.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getTraceUrl("");
      expect(url).toBeNull();
    });

    it("should handle empty log query", () => {
      mockEnv({
        VITE_GRAFANA_URL: "https://grafana.example.com",
        VITE_LOKI_URL: "https://loki.example.com",
      });

      const { result } = renderHook(() => useLGTMIntegration());

      const url = result.current.getLogsUrl("");
      expect(url).toBeNull();
    });

    it("should handle undefined environment variables", () => {
      // Don't mock any env vars - they should be undefined
      const { result } = renderHook(() => useLGTMIntegration());

      expect(result.current.isAvailable).toBe(false);
      expect(result.current.getGrafanaDashboardUrl("test")).toBeNull();
    });
  });
});
