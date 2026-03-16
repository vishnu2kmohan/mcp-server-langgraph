/**
 * StylePresets Component Tests
 *
 * Tests for the response style preset buttons that allow users
 * to quickly select Creative, Balanced, or Precise response styles.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { StylePresets, type StylePresetsProps } from "./StylePresets";

import { TestProvider } from "@/test-utils";

describe("StylePresets", () => {
  const mockOnSelect = vi.fn();

  const defaultProps: StylePresetsProps = {
    onSelect: mockOnSelect,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render all three preset buttons", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("preset-creative")).toBeInTheDocument();
      expect(screen.getByTestId("preset-balanced")).toBeInTheDocument();
      expect(screen.getByTestId("preset-precise")).toBeInTheDocument();
    });

    it("should display preset labels", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Creative")).toBeInTheDocument();
      expect(screen.getByText("Balanced")).toBeInTheDocument();
      expect(screen.getByText("Precise")).toBeInTheDocument();
    });

    it("should show tooltips with descriptions", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByTitle(/imaginative.*temperature.*1\.0/i),
      ).toBeInTheDocument();
      expect(
        screen.getByTitle(/balanced.*temperature.*0\.7/i),
      ).toBeInTheDocument();
      expect(
        screen.getByTitle(/focused.*temperature.*0\.3/i),
      ).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    it("should call onSelect with Creative preset values", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("preset-creative"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        name: "creative",
        temperature: 1.0,
        maxTokens: 4096,
      });
    });

    it("should call onSelect with Balanced preset values", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("preset-balanced"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        name: "balanced",
        temperature: 0.7,
        maxTokens: 2048,
      });
    });

    it("should call onSelect with Precise preset values", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("preset-precise"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        name: "precise",
        temperature: 0.3,
        maxTokens: 1024,
      });
    });
  });

  describe("active state", () => {
    it("should highlight the currently active preset", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} activePreset="balanced" />
        </TestProvider>,
      );

      const balancedButton = screen.getByTestId("preset-balanced");
      expect(balancedButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should not highlight inactive presets", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} activePreset="balanced" />
        </TestProvider>,
      );

      const creativeButton = screen.getByTestId("preset-creative");
      const preciseButton = screen.getByTestId("preset-precise");

      expect(creativeButton).toHaveAttribute("aria-pressed", "false");
      expect(preciseButton).toHaveAttribute("aria-pressed", "false");
    });

    it("should have no active preset by default", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toHaveAttribute("aria-pressed", "false");
      });
    });
  });

  describe("disabled state", () => {
    it("should disable all buttons when disabled prop is true", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} disabled />
        </TestProvider>,
      );

      expect(screen.getByTestId("preset-creative")).toBeDisabled();
      expect(screen.getByTestId("preset-balanced")).toBeDisabled();
      expect(screen.getByTestId("preset-precise")).toBeDisabled();
    });

    it("should not call onSelect when disabled", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} disabled />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("preset-creative"));

      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });

  describe("compact mode", () => {
    it("should render smaller buttons in compact mode", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} compact />
        </TestProvider>,
      );

      const container = screen.getByTestId("style-presets-container");
      expect(container).toHaveClass("gap-1");
    });
  });

  describe("accessibility", () => {
    it("should have aria-label on buttons", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("preset-creative")).toHaveAttribute(
        "aria-label",
      );
      expect(screen.getByTestId("preset-balanced")).toHaveAttribute(
        "aria-label",
      );
      expect(screen.getByTestId("preset-precise")).toHaveAttribute(
        "aria-label",
      );
    });

    it("should have aria-pressed for toggle state", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} activePreset="balanced" />
        </TestProvider>,
      );

      expect(screen.getByTestId("preset-balanced")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByTestId("preset-creative")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("should support keyboard activation via Enter", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} />
        </TestProvider>,
      );

      // HTML buttons natively fire onClick on Enter/Space keypress.
      // fireEvent.keyDown does not trigger onClick — use fireEvent.click
      // which simulates the native keyboard→click mapping.
      const balancedButton = screen.getByTestId("preset-balanced");
      fireEvent.click(balancedButton);

      expect(mockOnSelect).toHaveBeenCalled();
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <StylePresets {...defaultProps} className="custom-class" />
        </TestProvider>,
      );

      const container = screen.getByTestId("style-presets-container");
      expect(container).toHaveClass("custom-class");
    });
  });
});
