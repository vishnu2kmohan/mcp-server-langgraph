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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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
