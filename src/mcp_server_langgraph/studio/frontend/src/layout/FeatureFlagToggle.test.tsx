/**
 * FeatureFlagToggle Tests
 *
 * Tests for the dev-mode feature flag toggle component.
 * Allows switching between StudioShell and AppShell.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FeatureFlagToggle } from "./FeatureFlagToggle";

// Storage key used by the component
const STORAGE_KEY = "studio-hybrid-shell-override";

describe("FeatureFlagToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("Visibility", () => {
    it("renders in development mode", () => {
      render(<FeatureFlagToggle isDev={true} />);

      expect(screen.getByTestId("feature-flag-toggle")).toBeInTheDocument();
    });

    it("does not render in production mode by default", () => {
      render(<FeatureFlagToggle isDev={false} />);

      expect(
        screen.queryByTestId("feature-flag-toggle"),
      ).not.toBeInTheDocument();
    });

    it("can be forced to show in production with forceShow prop", () => {
      render(<FeatureFlagToggle isDev={false} forceShow={true} />);

      expect(screen.getByTestId("feature-flag-toggle")).toBeInTheDocument();
    });
  });

  describe("Toggle Functionality", () => {
    it("shows toggle button with shell mode label", () => {
      render(<FeatureFlagToggle isDev={true} />);

      expect(screen.getByText(/shell mode/i)).toBeInTheDocument();
    });

    it("displays current mode (hybrid/legacy)", () => {
      render(<FeatureFlagToggle isDev={true} />);

      // Should show hybrid or legacy depending on current state
      expect(screen.getByTestId("current-mode")).toBeInTheDocument();
    });

    it("calls onChange when toggle is clicked", () => {
      const onChange = vi.fn();
      render(<FeatureFlagToggle isDev={true} onChange={onChange} />);

      const toggle = screen.getByRole("switch");
      fireEvent.click(toggle);

      expect(onChange).toHaveBeenCalled();
    });

    it("persists toggle state to localStorage", () => {
      render(<FeatureFlagToggle isDev={true} />);

      const toggle = screen.getByRole("switch");
      fireEvent.click(toggle);

      expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull();
    });

    it("reads initial state from localStorage", () => {
      localStorage.setItem(STORAGE_KEY, "true");

      render(<FeatureFlagToggle isDev={true} />);

      const toggle = screen.getByRole("switch");
      expect(toggle).toBeChecked();
    });
  });

  describe("Labels", () => {
    it("shows Hybrid label when enabled", () => {
      localStorage.setItem(STORAGE_KEY, "true");

      render(<FeatureFlagToggle isDev={true} />);

      expect(screen.getByTestId("current-mode")).toHaveTextContent(/hybrid/i);
    });

    it("shows Legacy label when disabled", () => {
      localStorage.setItem(STORAGE_KEY, "false");

      render(<FeatureFlagToggle isDev={true} />);

      expect(screen.getByTestId("current-mode")).toHaveTextContent(/legacy/i);
    });
  });

  describe("Accessibility", () => {
    it("has accessible toggle button", () => {
      render(<FeatureFlagToggle isDev={true} />);

      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveAttribute("aria-checked");
    });

    it("has descriptive label for screen readers", () => {
      render(<FeatureFlagToggle isDev={true} />);

      const toggle = screen.getByRole("switch");
      expect(toggle).toHaveAccessibleName();
    });
  });

  describe("Styling", () => {
    it("applies custom className when provided", () => {
      render(<FeatureFlagToggle isDev={true} className="custom-class" />);

      const container = screen.getByTestId("feature-flag-toggle");
      expect(container).toHaveClass("custom-class");
    });
  });
});
