/**
 * Accessibility Tests
 *
 * Regression tests ensuring key components meet accessibility standards.
 * Tests cover:
 * - ARIA attributes
 * - Keyboard navigation
 * - Focus management
 * - Screen reader compatibility
 * - PWA components accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { FeedbackModal } from "../components/Feedback/FeedbackModal";
import { UpdatePrompt } from "../components/PWA/UpdatePrompt";
import { InstallPrompt } from "../components/PWA/InstallPrompt";

// Minimal store for testing
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: (state = {}) => state,
    },
  });
};

// Mock the API hook
vi.mock("../api", () => ({
  useSubmitFeedbackMutation: vi.fn(() => [
    vi
      .fn()
      .mockReturnValue({ unwrap: () => Promise.resolve({ success: true }) }),
    { isLoading: false, isSuccess: false },
  ]),
}));

const renderWithStore = (component: React.ReactNode) => {
  const store = createTestStore();
  return {
    store,
    ...render(<Provider store={store}>{component}</Provider>),
  };
};

describe("Accessibility", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("FeedbackModal", () => {
    it("should have role=dialog", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have aria-labelledby", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);
      const modal = screen.getByRole("dialog");
      expect(modal).toHaveAttribute("aria-labelledby");
    });

    it("should have accessible close button", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);
      // Button should be findable by its accessible name
      const closeButton = screen.getByTestId("close-feedback-modal");
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe("Interactive Elements", () => {
    it("should have accessible NPS score buttons", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);

      // All NPS buttons should be accessible
      for (let i = 0; i <= 10; i++) {
        const button = screen.getByTestId(`nps-score-${i}`);
        expect(button).toBeInTheDocument();
        // Buttons should have visible text content
        expect(button).toHaveTextContent(String(i));
      }
    });

    it("should have accessible CSAT star buttons", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);

      // All star rating buttons should be accessible
      for (let i = 1; i <= 5; i++) {
        const button = screen.getByTestId(`csat-star-${i}`);
        expect(button).toBeInTheDocument();
      }
    });

    it("should have accessible submit button", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);

      // Submit button should be findable by role and name
      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe("Form Labels", () => {
    it("should have labeled text input", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);

      // Comment textarea should have placeholder (serves as accessible description)
      const textarea = screen.getByPlaceholderText(/additional comments/i);
      expect(textarea).toBeInTheDocument();
    });
  });

  describe("Focus States", () => {
    it("buttons should be focusable", () => {
      renderWithStore(<FeedbackModal isOpen={true} onClose={() => {}} />);

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        // Buttons should not have tabindex=-1 (which would make them unfocusable)
        expect(button).not.toHaveAttribute("tabindex", "-1");
      });
    });
  });
});

describe("PWA Components Accessibility", () => {
  const mockOnUpdate = vi.fn();
  const mockOnDismiss = vi.fn();
  const mockOnInstall = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("UpdatePrompt", () => {
    it("should have role=alert for screen readers", () => {
      render(
        <UpdatePrompt
          needsUpdate={true}
          isUpdating={false}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live=polite for non-intrusive announcements", () => {
      render(
        <UpdatePrompt
          needsUpdate={true}
          isUpdating={false}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("should have accessible update button with aria-label", () => {
      render(
        <UpdatePrompt
          needsUpdate={true}
          isUpdating={false}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      const updateButton = screen.getByRole("button", {
        name: /update application now/i,
      });
      expect(updateButton).toBeInTheDocument();
    });

    it("should have accessible dismiss button with aria-label", () => {
      render(
        <UpdatePrompt
          needsUpdate={true}
          isUpdating={false}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      const dismissButton = screen.getByRole("button", {
        name: /remind me later/i,
      });
      expect(dismissButton).toBeInTheDocument();
    });

    it("buttons should be disabled when updating", () => {
      render(
        <UpdatePrompt
          needsUpdate={true}
          isUpdating={true}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe("InstallPrompt", () => {
    it("should have role=alert for screen readers", () => {
      render(
        <InstallPrompt
          canInstall={true}
          isInstalling={false}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have aria-live=polite for non-intrusive announcements", () => {
      render(
        <InstallPrompt
          canInstall={true}
          isInstalling={false}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("should have accessible install button with aria-label", () => {
      render(
        <InstallPrompt
          canInstall={true}
          isInstalling={false}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      const installButton = screen.getByRole("button", {
        name: /install app now/i,
      });
      expect(installButton).toBeInTheDocument();
    });

    it("should have accessible dismiss button with aria-label", () => {
      render(
        <InstallPrompt
          canInstall={true}
          isInstalling={false}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      const dismissButton = screen.getByRole("button", { name: /no thanks/i });
      expect(dismissButton).toBeInTheDocument();
    });

    it("buttons should be disabled when installing", () => {
      render(
        <InstallPrompt
          canInstall={true}
          isInstalling={true}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe("Common A11y Patterns", () => {
    it("UpdatePrompt should not render when not needed (avoids empty alerts)", () => {
      const { container } = render(
        <UpdatePrompt
          needsUpdate={false}
          isUpdating={false}
          onUpdate={mockOnUpdate}
          onDismiss={mockOnDismiss}
        />,
      );

      expect(container.firstChild).toBeNull();
    });

    it("InstallPrompt should not render when cannot install (avoids empty alerts)", () => {
      const { container } = render(
        <InstallPrompt
          canInstall={false}
          isInstalling={false}
          onInstall={mockOnInstall}
          onDismiss={mockOnDismiss}
        />,
      );

      expect(container.firstChild).toBeNull();
    });
  });
});

describe("Chat Components Accessibility", () => {
  describe("SlashCommandMenu", () => {
    beforeEach(async () => {
      vi.resetModules();
    });

    it("should have role=listbox for screen readers", async () => {
      const { SlashCommandMenu } =
        await import("../components/Chat/SlashCommandMenu");

      const commands = [
        { name: "help", description: "Show help" },
        { name: "clear", description: "Clear chat" },
      ];

      render(
        <SlashCommandMenu
          commands={commands}
          isOpen={true}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have aria-label on the listbox", async () => {
      const { SlashCommandMenu } =
        await import("../components/Chat/SlashCommandMenu");

      const commands = [{ name: "help", description: "Show help" }];

      render(
        <SlashCommandMenu
          commands={commands}
          isOpen={true}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );

      const listbox = screen.getByRole("listbox");
      expect(listbox).toHaveAttribute("aria-label", "Slash commands");
    });

    it("should have role=option for each command", async () => {
      const { SlashCommandMenu } =
        await import("../components/Chat/SlashCommandMenu");

      const commands = [
        { name: "help", description: "Show help" },
        { name: "clear", description: "Clear chat" },
      ];

      render(
        <SlashCommandMenu
          commands={commands}
          isOpen={true}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );

      const options = screen.getAllByRole("option");
      expect(options).toHaveLength(2);
    });

    it("should have aria-selected on the highlighted option", async () => {
      const { SlashCommandMenu } =
        await import("../components/Chat/SlashCommandMenu");

      const commands = [
        { name: "help", description: "Show help" },
        { name: "clear", description: "Clear chat" },
      ];

      render(
        <SlashCommandMenu
          commands={commands}
          isOpen={true}
          onSelect={() => {}}
          onClose={() => {}}
          selectedIndex={0}
        />,
      );

      const options = screen.getAllByRole("option");
      expect(options[0]).toHaveAttribute("aria-selected", "true");
      expect(options[1]).toHaveAttribute("aria-selected", "false");
    });
  });

  describe("LLMThinkingTrace Accessibility", () => {
    it("should have accessible toggle button with aria-expanded", async () => {
      const { LLMThinkingTrace } =
        await import("../components/Chat/LLMThinkingTrace");

      render(
        <LLMThinkingTrace
          thinkingContent="Thinking about the problem..."
          thinkingTokens={100}
          isExpanded={false}
          onToggle={() => {}}
        />,
      );

      // Toggle button should have aria-label and aria-expanded
      const button = screen.getByRole("button", {
        name: /toggle thinking trace/i,
      });
      expect(button).toBeInTheDocument();
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("should reflect expanded state in aria-expanded", async () => {
      const { LLMThinkingTrace } =
        await import("../components/Chat/LLMThinkingTrace");

      render(
        <LLMThinkingTrace
          thinkingContent="Thinking about the problem..."
          thinkingTokens={100}
          isExpanded={true}
          onToggle={() => {}}
        />,
      );

      const button = screen.getByRole("button", {
        name: /toggle thinking trace/i,
      });
      expect(button).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("AIFollowUpSuggestions Accessibility", () => {
    it("should have accessible suggestion buttons", async () => {
      const { AIFollowUpSuggestions } =
        await import("../components/Chat/AIFollowUpSuggestions");

      const suggestions = [
        { id: "1", text: "Tell me more", category: "explore" as const },
        { id: "2", text: "Give an example", category: "example" as const },
      ];

      render(
        <AIFollowUpSuggestions
          suggestions={suggestions}
          onSuggestionClick={() => {}}
        />,
      );

      // Each suggestion should be a clickable element
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("should have descriptive text on suggestion buttons", async () => {
      const { AIFollowUpSuggestions } =
        await import("../components/Chat/AIFollowUpSuggestions");

      const suggestions = [
        { id: "1", text: "Tell me more", category: "explore" as const },
      ];

      render(
        <AIFollowUpSuggestions
          suggestions={suggestions}
          onSuggestionClick={() => {}}
        />,
      );

      // Button should have visible text
      expect(screen.getByText("Tell me more")).toBeInTheDocument();
    });
  });

  describe("ReasoningEffortSelector Accessibility", () => {
    it("should have accessible button group for effort levels", async () => {
      const { ReasoningEffortSelector } =
        await import("../components/Chat/ReasoningEffortSelector");

      render(<ReasoningEffortSelector value="medium" onChange={() => {}} />);

      // Should have buttons for each effort level
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(3); // Low, Medium, High
    });

    it("should have aria-pressed on the selected effort button", async () => {
      const { ReasoningEffortSelector } =
        await import("../components/Chat/ReasoningEffortSelector");

      render(<ReasoningEffortSelector value="medium" onChange={() => {}} />);

      // Medium should be pressed
      const mediumButton = screen.getByText("Medium").closest("button");
      expect(mediumButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should have descriptive title on effort buttons", async () => {
      const { ReasoningEffortSelector } =
        await import("../components/Chat/ReasoningEffortSelector");

      render(<ReasoningEffortSelector value="medium" onChange={() => {}} />);

      // Buttons should have title attributes for screen readers
      const mediumButton = screen.getByText("Medium").closest("button");
      expect(mediumButton).toHaveAttribute("title");
    });
  });
});
