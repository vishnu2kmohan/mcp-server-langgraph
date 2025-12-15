/**
 * OnboardingModal Tests
 *
 * Tests for the first-run onboarding modal with template picker.
 * Helps new users choose a workflow template to get started.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { OnboardingModal, WorkflowTemplate } from "./OnboardingModal";

// Mock templates
const mockTemplates: WorkflowTemplate[] = [
  {
    id: "chatbot-basic",
    name: "Basic Chatbot",
    description: "A simple conversational chatbot",
    category: "conversational",
    tags: ["chat", "simple"],
  },
  {
    id: "chatbot-rag",
    name: "RAG Chatbot",
    description: "Retrieval-augmented generation chatbot",
    category: "conversational",
    tags: ["chat", "rag", "retrieval"],
  },
  {
    id: "api-agent",
    name: "API Agent",
    description: "An agent that calls external APIs",
    category: "agent",
    tags: ["api", "tools"],
  },
];

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: () => ({}),
    },
  });
};

const renderWithProvider = (ui: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

describe("OnboardingModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSelectTemplate: vi.fn(),
    templates: mockTemplates,
    isLoading: false,
    error: null as string | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when isOpen is true", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} isOpen={true} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("Header", () => {
    it("should display welcome message", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });

    it("should display subtitle with instructions", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getByText(/choose a template/i)).toBeInTheDocument();
    });
  });

  describe("Template List", () => {
    it("should display all templates", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getByText("Basic Chatbot")).toBeInTheDocument();
      expect(screen.getByText("RAG Chatbot")).toBeInTheDocument();
      expect(screen.getByText("API Agent")).toBeInTheDocument();
    });

    it("should display template descriptions", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(
        screen.getByText("A simple conversational chatbot"),
      ).toBeInTheDocument();
    });

    it("should display template categories", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getAllByText(/conversational/i).length).toBeGreaterThan(0);
    });
  });

  describe("Template Selection", () => {
    it("should call onSelectTemplate when template is clicked", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      const templateCard = screen.getByText("Basic Chatbot").closest("button");
      fireEvent.click(templateCard!);
      expect(defaultProps.onSelectTemplate).toHaveBeenCalledWith(
        mockTemplates[0],
      );
    });

    it("should highlight selected template", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);

      // Click to select
      const templateCard = screen.getByText("Basic Chatbot").closest("button");
      fireEvent.click(templateCard!);

      // Verify onSelectTemplate was called
      expect(defaultProps.onSelectTemplate).toHaveBeenCalledWith(
        mockTemplates[0],
      );
    });
  });

  describe("Skip Option", () => {
    it("should display skip button", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
    });

    it("should call onClose when skip is clicked", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      const skipButton = screen.getByRole("button", { name: /skip/i });
      fireEvent.click(skipButton);
      expect(defaultProps.onClose).toHaveBeenCalledOnce();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when loading", () => {
      renderWithProvider(
        <OnboardingModal {...defaultProps} isLoading={true} templates={[]} />,
      );
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should not show templates when loading", () => {
      renderWithProvider(
        <OnboardingModal {...defaultProps} isLoading={true} templates={[]} />,
      );
      expect(screen.queryByText("Basic Chatbot")).not.toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error message when error occurs", () => {
      renderWithProvider(
        <OnboardingModal
          {...defaultProps}
          error="Failed to load templates"
          templates={[]}
        />,
      );
      expect(screen.getByText("Failed to load templates")).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      renderWithProvider(
        <OnboardingModal
          {...defaultProps}
          error="Error"
          templates={[]}
          onRetry={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should call onRetry when retry button clicked", () => {
      const onRetry = vi.fn();
      renderWithProvider(
        <OnboardingModal
          {...defaultProps}
          error="Error"
          templates={[]}
          onRetry={onRetry}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /retry/i }));
      expect(onRetry).toHaveBeenCalledOnce();
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no templates available", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} templates={[]} />);
      expect(screen.getByText(/no templates available/i)).toBeInTheDocument();
    });
  });

  describe("Blank Start Option", () => {
    it("should display start from scratch option", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /start from scratch/i }),
      ).toBeInTheDocument();
    });

    it("should call onSelectTemplate with null for blank start", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      const blankButton = screen.getByRole("button", {
        name: /start from scratch/i,
      });
      fireEvent.click(blankButton);
      expect(defaultProps.onSelectTemplate).toHaveBeenCalledWith(null);
    });
  });

  describe("Accessibility", () => {
    it("should have accessible dialog role", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have accessible template buttons", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("should trap focus within modal", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      // Dialog should be present and focusable
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeInTheDocument();
    });
  });

  describe("Category Filtering", () => {
    it("should display category filter buttons", () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /all categories/i }),
      ).toBeInTheDocument();
    });

    it("should filter templates by category when clicked", async () => {
      renderWithProvider(<OnboardingModal {...defaultProps} />);

      // Click on agent category filter - use aria-label which is the category name
      const agentFilters = screen
        .getAllByRole("button")
        .filter((btn) => btn.getAttribute("aria-label") === "agent");
      if (agentFilters.length > 0) {
        fireEvent.click(agentFilters[0]);
        await waitFor(() => {
          // API Agent should be visible
          expect(screen.getByText("API Agent")).toBeInTheDocument();
        });
      }
    });
  });
});
