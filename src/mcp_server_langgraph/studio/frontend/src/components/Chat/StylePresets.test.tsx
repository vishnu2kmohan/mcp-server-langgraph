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
      render(<StylePresets {...defaultProps} />);

      expect(screen.getByTestId("preset-creative")).toBeInTheDocument();
      expect(screen.getByTestId("preset-balanced")).toBeInTheDocument();
      expect(screen.getByTestId("preset-precise")).toBeInTheDocument();
    });

    it("should display preset labels", () => {
      render(<StylePresets {...defaultProps} />);

      expect(screen.getByText("Creative")).toBeInTheDocument();
      expect(screen.getByText("Balanced")).toBeInTheDocument();
      expect(screen.getByText("Precise")).toBeInTheDocument();
    });

    it("should show tooltips with descriptions", () => {
      render(<StylePresets {...defaultProps} />);

      expect(
        screen.getByTitle(/imaginative.*temperature.*1\.2/i),
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
      render(<StylePresets {...defaultProps} />);

      fireEvent.click(screen.getByTestId("preset-creative"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        name: "creative",
        temperature: 1.2,
        maxTokens: 4096,
      });
    });

    it("should call onSelect with Balanced preset values", () => {
      render(<StylePresets {...defaultProps} />);

      fireEvent.click(screen.getByTestId("preset-balanced"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        name: "balanced",
        temperature: 0.7,
        maxTokens: 2048,
      });
    });

    it("should call onSelect with Precise preset values", () => {
      render(<StylePresets {...defaultProps} />);

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
      render(<StylePresets {...defaultProps} activePreset="balanced" />);

      const balancedButton = screen.getByTestId("preset-balanced");
      expect(balancedButton).toHaveClass("bg-blue-600");
    });

    it("should not highlight inactive presets", () => {
      render(<StylePresets {...defaultProps} activePreset="balanced" />);

      const creativeButton = screen.getByTestId("preset-creative");
      const preciseButton = screen.getByTestId("preset-precise");

      expect(creativeButton).not.toHaveClass("bg-blue-600");
      expect(preciseButton).not.toHaveClass("bg-blue-600");
    });

    it("should have no active preset by default", () => {
      render(<StylePresets {...defaultProps} />);

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).not.toHaveClass("bg-blue-600");
      });
    });
  });

  describe("disabled state", () => {
    it("should disable all buttons when disabled prop is true", () => {
      render(<StylePresets {...defaultProps} disabled />);

      expect(screen.getByTestId("preset-creative")).toBeDisabled();
      expect(screen.getByTestId("preset-balanced")).toBeDisabled();
      expect(screen.getByTestId("preset-precise")).toBeDisabled();
    });

    it("should not call onSelect when disabled", () => {
      render(<StylePresets {...defaultProps} disabled />);

      fireEvent.click(screen.getByTestId("preset-creative"));

      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });

  describe("compact mode", () => {
    it("should render smaller buttons in compact mode", () => {
      render(<StylePresets {...defaultProps} compact />);

      const container = screen.getByTestId("style-presets-container");
      expect(container).toHaveClass("gap-1");
    });
  });

  describe("accessibility", () => {
    it("should have aria-label on buttons", () => {
      render(<StylePresets {...defaultProps} />);

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
      render(<StylePresets {...defaultProps} activePreset="balanced" />);

      expect(screen.getByTestId("preset-balanced")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByTestId("preset-creative")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("should support keyboard navigation", () => {
      render(<StylePresets {...defaultProps} />);

      const balancedButton = screen.getByTestId("preset-balanced");
      fireEvent.keyDown(balancedButton, { key: "Enter" });

      expect(mockOnSelect).toHaveBeenCalled();
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(<StylePresets {...defaultProps} className="custom-class" />);

      const container = screen.getByTestId("style-presets-container");
      expect(container).toHaveClass("custom-class");
    });
  });
});
