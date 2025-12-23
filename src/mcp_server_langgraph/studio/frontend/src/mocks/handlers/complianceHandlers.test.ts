/**
 * Compliance Handlers Tests
 *
 * TDD tests for compliance API MSW handlers.
 * Validates that handlers return proper data structures.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest";
import { setupServer } from "msw/node";
import {
  complianceHandlers,
  mockComplianceSummary,
} from "./complianceHandlers";

const server = setupServer(...complianceHandlers);

describe("complianceHandlers", () => {
  beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });
  afterAll(() => server.close());

  describe("GET /api/v1/compliance/reports/summary", () => {
    it("should return compliance summary with all frameworks", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/summary?start_time=2024-01-01&end_time=2024-12-31",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("soc2");
      expect(data).toHaveProperty("hipaa");
      expect(data).toHaveProperty("gdpr");
      expect(data).toHaveProperty("fedramp");
    });

    it("should return proper structure for each framework", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/summary?start_time=2024-01-01&end_time=2024-12-31",
      );

      const data = await response.json();

      // Each framework should have percentage, status, and counts
      expect(data.soc2).toMatchObject({
        percentage: expect.any(Number),
        compliant_count: expect.any(Number),
        total_count: expect.any(Number),
        status: expect.stringMatching(/^(compliant|partial|non-compliant)$/),
      });
    });
  });

  describe("GET /api/v1/compliance/reports/soc2", () => {
    it("should return SOC2 report with controls", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/soc2?start_time=2024-01-01&end_time=2024-12-31",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("controls");
      expect(Array.isArray(data.controls)).toBe(true);
    });
  });

  describe("GET /api/v1/compliance/reports/hipaa", () => {
    it("should return HIPAA report with PHI indicators", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/hipaa?start_time=2024-01-01&end_time=2024-12-31",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("controls");
      expect(data).toHaveProperty("phi_access_logs");
    });
  });

  describe("GET /api/v1/compliance/reports/gdpr", () => {
    it("should return GDPR report with data subject rights", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/gdpr?start_time=2024-01-01&end_time=2024-12-31",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("controls");
      expect(data).toHaveProperty("data_subject_requests");
    });
  });

  describe("GET /api/v1/compliance/reports/fedramp", () => {
    it("should return FedRAMP report with authorization status", async () => {
      const response = await fetch(
        "/api/v1/compliance/reports/fedramp?start_time=2024-01-01&end_time=2024-12-31",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("controls");
      expect(data).toHaveProperty("authorization_status");
    });
  });

  describe("mockComplianceSummary", () => {
    it("should provide realistic mock data", () => {
      expect(mockComplianceSummary.soc2.percentage).toBeGreaterThanOrEqual(0);
      expect(mockComplianceSummary.soc2.percentage).toBeLessThanOrEqual(100);
      expect(mockComplianceSummary.hipaa.total_count).toBeGreaterThan(0);
    });
  });
});
