/**
 * CrossInsightsPanel Tests (TDD)
 *
 * Tests for the cross-insights display panel that shows
 * AI-generated insights from batch composite analysis.
 *
 * Features tested:
 * - Display of cross-insights array
 * - Persona analysis summary
 * - Disclosure level recommendations
 * - Confidence indicators
 * - Loading state
 * - Empty state
 * - Collapsible behavior
 * - Admin-only visibility
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { CrossInsightsPanel } from "./CrossInsightsPanel";
import type {
  PersonaAnalysisResult,
  DisclosureAnalysisResult,
} from "../../hooks/useBatchCompositeAnalysis";

// Mock feature flag context
vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: vi.fn().mockReturnValue(true),
}));

// Create a minimal store for tests
const createTestStore = () => {
  return configureStore({
    reducer: {
      auth: () => ({ persona: "admin", isAuthenticated: true }),
    },
  });
};

const renderWithProviders = (component: React.ReactNode) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("CrossInsightsPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const mockPersonaResult: PersonaAnalysisResult = {
    assignedPersona: "bob",
    detectedPersona: "alice-builder",
    confidence: 0.85,
    behaviorSignals: ["Advanced feature usage", "Long sessions"],
    recommendation: "Consider upgrading to developer role",
    uiAdaptations: [{ feature: "workflow_builder", action: "unlock" }],
  };

  const mockDisclosureResult: DisclosureAnalysisResult = {
    currentLevel: "intermediate",
    recommendedLevel: "advanced",
    confidence: 0.82,
    unlockFeatures: ["custom_agents", "advanced_filters"],
    personalizedMessage: "Ready for advanced features!",
  };

  const mockCrossInsights = [
    "User behavior suggests higher expertise than assigned persona",
    "Progressive disclosure level should be upgraded",
    "Consider showing observability features to this user",
  ];

  describe("Rendering", () => {
    it("should render the panel with insights", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={mockPersonaResult}
          disclosureResult={mockDisclosureResult}
          confidence={0.84}
          isLoading={false}
        />,
      );

      expect(screen.getByText("AI Insights")).toBeInTheDocument();
      expect(
        screen.getByText(/User behavior suggests higher expertise/),
      ).toBeInTheDocument();
    });

    it("should display all cross-insights", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.75}
          isLoading={false}
        />,
      );

      mockCrossInsights.forEach((insight) => {
        expect(screen.getByText(insight)).toBeInTheDocument();
      });
    });

    it("should show persona mismatch warning when detected differs from assigned", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={mockPersonaResult}
          disclosureResult={null}
          confidence={0.85}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/Persona mismatch/i)).toBeInTheDocument();
      expect(screen.getByText(/bob/)).toBeInTheDocument();
      expect(screen.getByText(/alice-builder/)).toBeInTheDocument();
    });

    it("should show disclosure level upgrade recommendation", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={null}
          disclosureResult={mockDisclosureResult}
          confidence={0.82}
          isLoading={false}
        />,
      );

      // Check for level upgrade section
      expect(
        screen.getByText(/Level upgrade recommended/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/Current:/i)).toBeInTheDocument();
      expect(screen.getByText(/Recommended:/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Ready for advanced features/i),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={null}
          disclosureResult={null}
          confidence={0}
          isLoading={true}
        />,
      );

      expect(screen.getByTestId("insights-loading")).toBeInTheDocument();
    });

    it("should hide content when loading", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={mockPersonaResult}
          disclosureResult={mockDisclosureResult}
          confidence={0.84}
          isLoading={true}
        />,
      );

      expect(
        screen.queryByText(/User behavior suggests/),
      ).not.toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no insights available", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={null}
          disclosureResult={null}
          confidence={0}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/No insights available/i)).toBeInTheDocument();
    });

    it("should not render panel at all when nothing to show and hideWhenEmpty is true", () => {
      const { container } = renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={null}
          disclosureResult={null}
          confidence={0}
          isLoading={false}
          hideWhenEmpty={true}
        />,
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Confidence Indicator", () => {
    it("should display confidence score", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/84%/)).toBeInTheDocument();
    });

    it("should show high confidence indicator when above 0.8", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.85}
          isLoading={false}
        />,
      );

      expect(screen.getByTestId("confidence-high")).toBeInTheDocument();
    });

    it("should show medium confidence indicator when between 0.6 and 0.8", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.7}
          isLoading={false}
        />,
      );

      expect(screen.getByTestId("confidence-medium")).toBeInTheDocument();
    });

    it("should show low confidence indicator when below 0.6", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.5}
          isLoading={false}
        />,
      );

      expect(screen.getByTestId("confidence-low")).toBeInTheDocument();
    });
  });

  describe("Collapsible Behavior", () => {
    it("should be collapsible by default", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      const toggleButton = screen.getByRole("button", { name: /toggle/i });
      expect(toggleButton).toBeInTheDocument();
    });

    it("should collapse content when toggle is clicked", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      // Content should be visible initially
      expect(screen.getByText(mockCrossInsights[0])).toBeInTheDocument();

      // Click toggle
      fireEvent.click(screen.getByRole("button", { name: /toggle/i }));

      // Content should be removed from DOM after collapse
      expect(screen.queryByText(mockCrossInsights[0])).not.toBeInTheDocument();
    });

    it("should expand when toggle is clicked again", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      const toggleButton = screen.getByRole("button", { name: /toggle/i });

      // Collapse
      fireEvent.click(toggleButton);
      // Expand
      fireEvent.click(toggleButton);

      expect(screen.getByText(mockCrossInsights[0])).toBeInTheDocument();
    });

    it("should respect defaultCollapsed prop", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
          defaultCollapsed={true}
        />,
      );

      // Content should be removed from DOM when defaultCollapsed is true
      expect(screen.queryByText(mockCrossInsights[0])).not.toBeInTheDocument();
    });
  });

  describe("Dismissible Behavior", () => {
    it("should show dismiss button when onDismiss is provided", () => {
      const onDismiss = vi.fn();
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
          onDismiss={onDismiss}
        />,
      );

      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
          onDismiss={onDismiss}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe("UI Adaptations", () => {
    it("should display recommended UI adaptations from persona analysis", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={mockPersonaResult}
          disclosureResult={null}
          confidence={0.85}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/workflow_builder/i)).toBeInTheDocument();
      expect(screen.getByText(/unlock/i)).toBeInTheDocument();
    });

    it("should display features to unlock from disclosure analysis", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={[]}
          personaResult={null}
          disclosureResult={mockDisclosureResult}
          confidence={0.82}
          isLoading={false}
        />,
      );

      expect(screen.getByText(/custom_agents/i)).toBeInTheDocument();
      expect(screen.getByText(/advanced_filters/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible panel heading", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      expect(
        screen.getByRole("heading", { name: /AI Insights/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible list for insights", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      expect(screen.getByRole("list")).toBeInTheDocument();
      expect(screen.getAllByRole("listitem")).toHaveLength(
        mockCrossInsights.length,
      );
    });

    it("should have ARIA label for confidence indicator", () => {
      renderWithProviders(
        <CrossInsightsPanel
          crossInsights={mockCrossInsights}
          personaResult={null}
          disclosureResult={null}
          confidence={0.84}
          isLoading={false}
        />,
      );

      expect(
        screen.getByLabelText(/confidence score: 84%/i),
      ).toBeInTheDocument();
    });
  });
});
