/**
 * OnboardingWizard Component Tests
 *
 * TDD tests for the multi-step onboarding wizard.
 * Replaces single modal with a guided 4-step flow:
 * Step 1: Welcome + value proposition
 * Step 2: Persona selection (admin/developer/user)
 * Step 3: Template selection
 * Step 4: Quick tour of interface
 *
 * Phase 6.5: AI-Powered Onboarding Personalization integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { OnboardingWizard, OnboardingWizardProps } from "./OnboardingWizard";

import { TestProvider } from "@/test-utils";

// Mock useAIOnboarding hook to avoid Redux dependency in tests
vi.mock("../../hooks/useAIOnboarding", () => ({
  useAIOnboarding: () => ({
    isLoading: false,
    error: null,
    detectedIntent: null,
    confidence: 0,
    recommendedPath: [],
    skipSteps: [],
    personaPrediction: null,
    refresh: vi.fn(),
  }),
}));

const mockTemplates = [
  {
    id: "chatbot-basic",
    name: "Basic Chatbot",
    description: "A simple conversational chatbot",
    category: "conversational",
    tags: ["chat", "simple"],
  },
  {
    id: "api-agent",
    name: "API Agent",
    description: "An agent that calls external APIs",
    category: "agent",
    tags: ["api", "tools"],
  },
];

describe("OnboardingWizard", () => {
  const defaultProps: OnboardingWizardProps = {
    isOpen: true,
    onComplete: vi.fn(),
    onSkip: vi.fn(),
    templates: mockTemplates,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when isOpen is true", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} isOpen={false} />
        </TestProvider>,
      );
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("Step 1: Welcome", () => {
    it("should display welcome message on first step", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/welcome to agent studio/i)).toBeInTheDocument();
    });

    it("should show value proposition", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/build ai agents/i)).toBeInTheDocument();
    });

    it("should display Next button to proceed", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /get started|next/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Progress Indicator", () => {
    it("should show step 1 of 4 initially", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/step 1 of 4/i)).toBeInTheDocument();
    });

    it("should display progress bar", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("should update progress as user advances", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "1");

      // Click next to go to step 2
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      expect(progressBar).toHaveAttribute("aria-valuenow", "2");
    });
  });

  describe("Step 2: Persona Selection", () => {
    it("should show persona options after clicking next", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );

      expect(
        screen.getByText(/how will you use agent studio/i),
      ).toBeInTheDocument();
    });

    it("should display admin, developer, and user persona options", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );

      expect(screen.getByText(/administrator/i)).toBeInTheDocument();
      expect(screen.getByText(/developer/i)).toBeInTheDocument();
      expect(screen.getByText(/standard user/i)).toBeInTheDocument();
    });

    it("should allow selecting a persona", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );

      const developerOption = screen.getByText(/developer/i).closest("button");
      fireEvent.click(developerOption!);

      expect(developerOption).toHaveAttribute("aria-pressed", "true");
    });

    it("should enable next button only after persona selection", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );

      const nextButton = screen.getByRole("button", { name: /next/i });
      expect(nextButton).toBeDisabled();

      const developerOption = screen.getByText(/developer/i).closest("button");
      fireEvent.click(developerOption!);
      expect(nextButton).not.toBeDisabled();
    });
  });

  describe("Step 3: Template Selection", () => {
    const goToStep3 = () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      // Step 1 → Step 2
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      // Select persona
      const developerOption = screen.getByText(/developer/i).closest("button");
      fireEvent.click(developerOption!);
      // Step 2 → Step 3
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
    };

    it("should display template options on step 3", () => {
      goToStep3();
      expect(screen.getByText(/choose a template/i)).toBeInTheDocument();
    });

    it("should show available templates", () => {
      goToStep3();
      expect(screen.getByText("Basic Chatbot")).toBeInTheDocument();
      expect(screen.getByText("API Agent")).toBeInTheDocument();
    });

    it("should allow selecting a template", () => {
      goToStep3();
      const templateCard = screen.getByText("Basic Chatbot").closest("button");
      fireEvent.click(templateCard!);
      expect(templateCard).toHaveAttribute("aria-pressed", "true");
    });

    it("should show Start from scratch option", () => {
      goToStep3();
      expect(
        screen.getByRole("button", { name: /start from scratch/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Step 4: Quick Tour", () => {
    const goToStep4 = () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      // Step 1 → Step 2
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      // Select persona
      fireEvent.click(screen.getByText(/developer/i).closest("button")!);
      // Step 2 → Step 3
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      // Select template
      fireEvent.click(screen.getByText("Basic Chatbot").closest("button")!);
      // Step 3 → Step 4
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
    };

    it("should display tour introduction on step 4", () => {
      goToStep4();
      expect(screen.getByText(/quick tour/i)).toBeInTheDocument();
    });

    it("should show key features to explore", () => {
      goToStep4();
      expect(screen.getByText(/command palette/i)).toBeInTheDocument();
      expect(screen.getByText(/chat sessions/i)).toBeInTheDocument();
      // Check for Workflows feature in the tour (specific title text)
      expect(screen.getByText("Workflows")).toBeInTheDocument();
    });

    it("should display finish button", () => {
      goToStep4();
      expect(
        screen.getByRole("button", { name: /finish|complete/i }),
      ).toBeInTheDocument();
    });

    it("should call onComplete when finish is clicked", () => {
      goToStep4();
      fireEvent.click(screen.getByRole("button", { name: /finish|complete/i }));
      expect(defaultProps.onComplete).toHaveBeenCalledWith({
        persona: "developer",
        template: mockTemplates[0],
        tourCompleted: true,
      });
    });
  });

  describe("Navigation", () => {
    it("should allow going back to previous steps", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      // Go to step 2
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      expect(screen.getByText(/step 2 of 4/i)).toBeInTheDocument();

      // Go back to step 1
      fireEvent.click(screen.getByRole("button", { name: /back/i }));
      expect(screen.getByText(/step 1 of 4/i)).toBeInTheDocument();
    });

    it("should not show back button on step 1", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /back/i }),
      ).not.toBeInTheDocument();
    });

    it("should preserve selections when going back and forward", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      // Go to step 2 and select persona
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      fireEvent.click(screen.getByText(/developer/i).closest("button")!);

      // Go to step 3 and back to step 2
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /back/i }));

      // Developer should still be selected
      const developerOption = screen.getByText(/developer/i).closest("button");
      expect(developerOption).toHaveAttribute("aria-pressed", "true");
    });
  });

  describe("Skip Functionality", () => {
    it("should show skip button on all steps", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
    });

    it("should call onSkip when skip is clicked", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /skip/i }));
      expect(defaultProps.onSkip).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible dialog role", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("should have aria-labelledby for dialog title", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });

    it("should announce step changes to screen readers", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-valuemin",
        "1",
      );
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-valuemax",
        "4",
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty templates gracefully on step 3", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} templates={[]} />
        </TestProvider>,
      );
      // Go to step 3
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      fireEvent.click(screen.getByText(/developer/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));

      expect(screen.getByText(/no templates available/i)).toBeInTheDocument();
    });

    it("should allow completing without template when none selected", () => {
      render(
        <TestProvider>
          <OnboardingWizard {...defaultProps} />
        </TestProvider>,
      );
      // Go through all steps
      fireEvent.click(
        screen.getByRole("button", { name: /get started|next/i }),
      );
      fireEvent.click(screen.getByText(/developer/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      // Skip template selection
      fireEvent.click(
        screen.getByRole("button", { name: /start from scratch/i }),
      );
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /finish|complete/i }));

      expect(defaultProps.onComplete).toHaveBeenCalledWith({
        persona: "developer",
        template: null,
        tourCompleted: true,
      });
    });
  });
});
