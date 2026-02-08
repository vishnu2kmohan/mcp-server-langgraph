/**
 * SupportBadge Tests
 *
 * Tests for the SupportBadge component covering:
 * - All support level variants render correctly
 * - Correct labels and icons
 * - Color class application
 * - Accessibility attributes
 * - className composition
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { SupportBadge } from "./SupportBadge";
import type { SupportLevel } from "./SupportBadge";

import { TestProvider } from "@/test-utils";

describe("SupportBadge", () => {
  const levels: SupportLevel[] = ["managed", "premium", "community", "custom"];

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it.each(levels)("renders %s level badge", (level) => {
    render(
      <TestProvider>
        <SupportBadge level={level} />
      </TestProvider>,
    );
    expect(screen.getByTestId(`support-badge-${level}`)).toBeInTheDocument();
  });

  it("renders managed badge with correct label", () => {
    render(
      <TestProvider>
        <SupportBadge level="managed" />
      </TestProvider>,
    );
    expect(screen.getByText("Managed")).toBeInTheDocument();
  });

  it("renders premium badge with correct label", () => {
    render(
      <TestProvider>
        <SupportBadge level="premium" />
      </TestProvider>,
    );
    expect(screen.getByText("Premium")).toBeInTheDocument();
  });

  it("renders community badge with correct label", () => {
    render(
      <TestProvider>
        <SupportBadge level="community" />
      </TestProvider>,
    );
    expect(screen.getByText("Community")).toBeInTheDocument();
  });

  it("renders custom badge with correct label", () => {
    render(
      <TestProvider>
        <SupportBadge level="custom" />
      </TestProvider>,
    );
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("applies success color classes for managed level", () => {
    render(
      <TestProvider>
        <SupportBadge level="managed" />
      </TestProvider>,
    );
    const badge = screen.getByTestId("support-badge-managed");
    expect(badge.className).toContain("bg-success-3");
    expect(badge.className).toContain("text-success-11");
  });

  it("applies warning color classes for premium level", () => {
    render(
      <TestProvider>
        <SupportBadge level="premium" />
      </TestProvider>,
    );
    const badge = screen.getByTestId("support-badge-premium");
    expect(badge.className).toContain("bg-warning-3");
    expect(badge.className).toContain("text-warning-11");
  });

  it("applies primary color classes for community level", () => {
    render(
      <TestProvider>
        <SupportBadge level="community" />
      </TestProvider>,
    );
    const badge = screen.getByTestId("support-badge-community");
    expect(badge.className).toContain("bg-primary-3");
    expect(badge.className).toContain("text-primary-11");
  });

  it("applies neutral color classes for custom level", () => {
    render(
      <TestProvider>
        <SupportBadge level="custom" />
      </TestProvider>,
    );
    const badge = screen.getByTestId("support-badge-custom");
    expect(badge.className).toContain("bg-neutral-3");
    expect(badge.className).toContain("text-neutral-11");
  });

  it("includes icon with aria-hidden attribute", () => {
    const { container } = render(
      <TestProvider>
        <SupportBadge level="managed" />
      </TestProvider>,
    );
    const icon = container.querySelector('[aria-hidden="true"]');
    expect(icon).toBeTruthy();
  });

  it("accepts and applies className prop", () => {
    render(
      <TestProvider>
        <SupportBadge level="managed" className="extra-class" />
      </TestProvider>,
    );
    const badge = screen.getByTestId("support-badge-managed");
    expect(badge.className).toContain("extra-class");
  });
});
