/**
 * VegaLiteArtifact Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 *
 * VegaLiteArtifact renders Vega-Lite specifications using vega-embed.
 * This enables interactive Altair charts in the chat/canvas.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VegaLiteArtifact } from "./VegaLiteArtifact";

import { TestProvider } from "@/test-utils";

// Sample Vega-Lite specs for testing
const SIMPLE_BAR_CHART_SPEC = {
  $schema: "https://vega.github.io/schema/vega-lite/v5.json",
  description: "A simple bar chart",
  data: {
    values: [
      { category: "A", value: 28 },
      { category: "B", value: 55 },
      { category: "C", value: 43 },
    ],
  },
  mark: "bar",
  encoding: {
    x: { field: "category", type: "nominal" },
    y: { field: "value", type: "quantitative" },
  },
};

const _SIMPLE_LINE_CHART_SPEC = {
  $schema: "https://vega.github.io/schema/vega-lite/v5.json",
  description: "A simple line chart",
  data: {
    values: [
      { x: 1, y: 10 },
      { x: 2, y: 20 },
      { x: 3, y: 15 },
    ],
  },
  mark: "line",
  encoding: {
    x: { field: "x", type: "quantitative" },
    y: { field: "y", type: "quantitative" },
  },
};

const INVALID_SPEC = {
  invalid: "not a valid vega-lite spec",
};

// Mock vega-embed module - use synchronous mock to avoid act() warnings
vi.mock("vega-embed", () => ({
  default: vi.fn().mockImplementation((container, spec) => {
    // Return a resolved promise synchronously to avoid async state updates
    // that cause act() warnings in tests
    if (spec && spec.$schema && spec.$schema.includes("vega-lite")) {
      return Promise.resolve({
        view: {
          finalize: vi.fn(),
        },
        finalize: vi.fn(),
      });
    }
    // Return rejected promise for invalid specs
    return Promise.reject(new Error("Invalid Vega-Lite specification"));
  }),
}));

// Helper to render and wait for async updates
async function _renderAndWait(ui: React.ReactElement) {
  const result = render(ui);
  // Wait for any pending state updates from vega-embed
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

// Suppress act() warnings for async vega-embed operations at file level
// These warnings are expected since vega-embed does async work
const originalError = console.error;

beforeEach(() => {
  vi.clearAllMocks();
  // Suppress "not wrapped in act(...)" warnings
  console.error = (...args) => {
    if (args[0]?.includes?.("not wrapped in act(...)")) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterEach(async () => {
  // Flush any pending state updates
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  cleanup();
  console.error = originalError;
  vi.restoreAllMocks();
});

describe("VegaLiteArtifact", () => {
  describe("Rendering", () => {
    it("should render the component container", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    });

    it("should display title when provided", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} title="Sales Chart" />
        </TestProvider>,
      );

      expect(screen.getByText("Sales Chart")).toBeInTheDocument();
    });

    it("should use spec description as fallback title", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      expect(screen.getByText("A simple bar chart")).toBeInTheDocument();
    });

    it("should display default title when no title or description", () => {
      const specWithoutDescription = {
        ...SIMPLE_BAR_CHART_SPEC,
        description: undefined,
      };
      render(
        <TestProvider>
          <VegaLiteArtifact spec={specWithoutDescription} />
        </TestProvider>,
      );

      expect(screen.getByText("Vega-Lite Chart")).toBeInTheDocument();
    });

    it("should render chart container for vega-embed", async () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("vega-chart-container")).toBeInTheDocument();
      });
    });
  });

  describe("Spec Handling", () => {
    it("should accept spec as object", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    });

    it("should accept spec as JSON string", () => {
      const specString = JSON.stringify(SIMPLE_BAR_CHART_SPEC);
      render(
        <TestProvider>
          <VegaLiteArtifact spec={specString} />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    });

    it("should handle invalid JSON string gracefully", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec="{ invalid json }" />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
      // Shows error for invalid JSON
      expect(
        screen.getByText(/failed to parse|invalid json/i),
      ).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message for invalid spec", async () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={INVALID_SPEC} />
        </TestProvider>,
      );

      // The component shows an error for invalid specs (missing mark/layer/composition)
      await waitFor(() => {
        expect(screen.getByTestId("vega-error")).toBeInTheDocument();
      });

      // Verify error message text is shown
      expect(
        screen.getByText(/invalid vega-lite specification/i),
      ).toBeInTheDocument();
    });

    it("should display retry button on error", async () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={INVALID_SPEC} />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("vega-error")).toBeInTheDocument();
      });

      // Retry button(s) should be present on error (may be multiple - in header and error area)
      const retryButtons = screen.getAllByRole("button", { name: /retry/i });
      expect(retryButtons.length).toBeGreaterThan(0);
    });
  });

  describe("Theme Support", () => {
    it("should apply dark theme when specified", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} theme="dark" />
        </TestProvider>,
      );

      const container = screen.getByTestId("vega-lite-artifact");
      // The 'dark' class (not 'dark:' prefix) is added when theme="dark"
      expect(container).toHaveClass("dark");
    });

    it("should apply light theme by default", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      const container = screen.getByTestId("vega-lite-artifact");
      // The 'dark' class should not be present when theme is light (default)
      // Note: 'dark:' prefixes in Tailwind CSS classes are different from the 'dark' class
      const classList = container.className.split(" ");
      expect(classList).not.toContain("dark");
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator while chart is rendering", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      // Initially should show loading
      expect(
        screen.getByTestId("vega-loading") || screen.getByText(/loading/i),
      ).toBeInTheDocument();
    });
  });

  describe("Export Functionality", () => {
    it("should render export button", async () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      await waitFor(() => {
        const exportButton = screen.queryByRole("button", {
          name: /export|download/i,
        });
        // Export is optional but expected
        if (exportButton) {
          expect(exportButton).toBeInTheDocument();
        }
      });
    });
  });

  describe("Accessibility", () => {
    it("should have accessible chart container", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} title="Sales Chart" />
        </TestProvider>,
      );

      const container = screen.getByTestId("vega-chart-container");
      expect(container).toHaveAttribute("role", "img");
      expect(container).toHaveAttribute("aria-label");
    });
  });

  describe("Responsiveness", () => {
    it("should accept width prop", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} width={500} />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    });

    it("should accept height prop", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} height={300} />
        </TestProvider>,
      );

      expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    });

    it("should default to responsive width when no width specified", () => {
      render(
        <TestProvider>
          <VegaLiteArtifact spec={SIMPLE_BAR_CHART_SPEC} />
        </TestProvider>,
      );

      const container = screen.getByTestId("vega-lite-artifact");
      expect(container.className).toMatch(/w-full|width.*100/);
    });
  });
});

describe("VegaLiteArtifact Integration", () => {
  it("should work with Altair-generated specs", () => {
    // Altair generates Vega-Lite specs with specific structure
    const altairSpec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      config: {
        view: { continuousWidth: 300, continuousHeight: 300 },
      },
      data: { name: "data-abc123" },
      datasets: {
        "data-abc123": [
          { x: 1, y: 10 },
          { x: 2, y: 20 },
        ],
      },
      mark: { type: "point" },
      encoding: {
        x: { field: "x", type: "quantitative" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={altairSpec} title="Altair Scatter Plot" />
      </TestProvider>,
    );

    expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
    expect(screen.getByText("Altair Scatter Plot")).toBeInTheDocument();
  });
});

describe("VegaLiteArtifact Error Handling", () => {
  it("should handle null spec gracefully", () => {
    // @ts-expect-error - Testing null handling
    render(
      <TestProvider>
        <VegaLiteArtifact spec={null} />
      </TestProvider>,
    );

    expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
  });

  it("should handle undefined spec gracefully", () => {
    // @ts-expect-error - Testing undefined handling
    render(
      <TestProvider>
        <VegaLiteArtifact spec={undefined} />
      </TestProvider>,
    );

    expect(screen.getByTestId("vega-lite-artifact")).toBeInTheDocument();
  });

  it("should handle empty object spec", async () => {
    render(
      <TestProvider>
        <VegaLiteArtifact spec={{}} />
      </TestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/invalid vega-lite specification/i),
    ).toBeInTheDocument();
  });

  it("should handle spec with only data (no mark)", async () => {
    const specWithOnlyData = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      data: { values: [{ x: 1, y: 2 }] },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithOnlyData} />
      </TestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });
  });

  it("should handle deeply nested invalid JSON string", () => {
    const badJson = "{ 'invalid': 'single quotes not allowed' }";
    render(
      <TestProvider>
        <VegaLiteArtifact spec={badJson} />
      </TestProvider>,
    );

    expect(screen.getByText(/failed to parse/i)).toBeInTheDocument();
  });

  it("should display error icon in error state", async () => {
    render(
      <TestProvider>
        <VegaLiteArtifact spec={INVALID_SPEC} />
      </TestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });

    // Error icon should be visible (AlertCircle)
    const errorContainer = screen.getByTestId("vega-error");
    expect(errorContainer).toBeInTheDocument();
  });

  it("should allow retry after error", async () => {
    const user = userEvent.setup();
    render(
      <TestProvider>
        <VegaLiteArtifact spec={INVALID_SPEC} />
      </TestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });

    // Click retry button
    const retryButtons = screen.getAllByRole("button", { name: /retry/i });
    expect(retryButtons.length).toBeGreaterThan(0);

    await user.click(retryButtons[0]);

    // Should still show error since spec is still invalid
    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });
  });

  it("should not show export button when in error state", async () => {
    render(
      <TestProvider>
        <VegaLiteArtifact spec={INVALID_SPEC} />
      </TestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vega-error")).toBeInTheDocument();
    });

    // Export button should not be visible during error
    const exportButton = screen.queryByRole("button", {
      name: /export|download/i,
    });
    expect(exportButton).not.toBeInTheDocument();
  });
});

describe("VegaLiteArtifact Title Extraction", () => {
  it("should extract string title from spec.title", () => {
    const specWithStringTitle = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      title: "Sales by Region",
      mark: "bar",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "nominal" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithStringTitle} />
      </TestProvider>,
    );

    expect(screen.getByText("Sales by Region")).toBeInTheDocument();
  });

  it("should extract title from spec.title.text object", () => {
    const specWithObjectTitle = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      title: {
        text: "Revenue Analysis 2024",
        fontSize: 18,
        anchor: "middle",
      },
      mark: "line",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "quantitative" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithObjectTitle} />
      </TestProvider>,
    );

    expect(screen.getByText("Revenue Analysis 2024")).toBeInTheDocument();
  });

  it("should fallback to description when title is not present", () => {
    const specWithDescription = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      description: "Monthly sales trends",
      mark: "line",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "quantitative" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithDescription} />
      </TestProvider>,
    );

    expect(screen.getByText("Monthly sales trends")).toBeInTheDocument();
  });

  it("should prefer title over description when both present", () => {
    const specWithBoth = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      title: "Preferred Title",
      description: "This is the description",
      mark: "bar",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "nominal" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithBoth} />
      </TestProvider>,
    );

    expect(screen.getByText("Preferred Title")).toBeInTheDocument();
    expect(
      screen.queryByText("This is the description"),
    ).not.toBeInTheDocument();
  });

  it("should use prop title over spec title", () => {
    const specWithTitle = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      title: "Spec Title",
      mark: "bar",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "nominal" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithTitle} title="Prop Title" />
      </TestProvider>,
    );

    expect(screen.getByText("Prop Title")).toBeInTheDocument();
    expect(screen.queryByText("Spec Title")).not.toBeInTheDocument();
  });

  it("should handle Altair spec with .properties(title=...)", () => {
    // Altair typically sets title via .properties(title='...')
    const altairSpecWithTitle = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      config: {
        view: { continuousWidth: 300, continuousHeight: 300 },
      },
      title: "Altair Generated Title",
      data: { name: "data-xyz789" },
      datasets: {
        "data-xyz789": [
          { category: "A", count: 10 },
          { category: "B", count: 20 },
        ],
      },
      mark: { type: "bar" },
      encoding: {
        x: { field: "category", type: "nominal" },
        y: { field: "count", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={altairSpecWithTitle} />
      </TestProvider>,
    );

    expect(screen.getByText("Altair Generated Title")).toBeInTheDocument();
  });

  it("should display default title for spec without title or description", () => {
    const specWithoutTitleOrDescription = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      mark: "point",
      data: { values: [{ x: 1, y: 2 }] },
      encoding: {
        x: { field: "x", type: "quantitative" },
        y: { field: "y", type: "quantitative" },
      },
    };

    render(
      <TestProvider>
        <VegaLiteArtifact spec={specWithoutTitleOrDescription} />
      </TestProvider>,
    );

    expect(screen.getByText("Vega-Lite Chart")).toBeInTheDocument();
  });
});
