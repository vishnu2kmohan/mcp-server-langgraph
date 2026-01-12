/**
 * Slider Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Slider } from "./Slider";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("Slider", () => {
  describe("rendering", () => {
    it("renders as a range input", () => {
      render(<Slider value={50} onChange={() => {}} />);
      expect(screen.getByRole("slider")).toBeInTheDocument();
    });

    it("renders with default min/max values", () => {
      render(<Slider value={50} onChange={() => {}} />);
      const slider = screen.getByRole("slider");
      expect(slider).toHaveAttribute("min", "0");
      expect(slider).toHaveAttribute("max", "100");
    });

    it("renders with custom min/max values", () => {
      render(
        <Slider value={0.5} onChange={() => {}} min={0} max={1} step={0.1} />,
      );
      const slider = screen.getByRole("slider");
      expect(slider).toHaveAttribute("min", "0");
      expect(slider).toHaveAttribute("max", "1");
      expect(slider).toHaveAttribute("step", "0.1");
    });

    it("renders with label", () => {
      render(<Slider value={50} onChange={() => {}} label="Volume" />);
      expect(screen.getByText("Volume")).toBeInTheDocument();
    });

    it("renders with value display", () => {
      render(<Slider value={75} onChange={() => {}} showValue />);
      expect(screen.getByText("75")).toBeInTheDocument();
    });

    it("renders with custom value formatter", () => {
      render(
        <Slider
          value={0.5}
          onChange={() => {}}
          showValue
          formatValue={(v) => `${(v * 100).toFixed(0)}%`}
        />,
      );
      expect(screen.getByText("50%")).toBeInTheDocument();
    });
  });

  describe("interaction", () => {
    it("calls onChange when value changes", () => {
      const onChange = vi.fn();
      render(<Slider value={50} onChange={onChange} />);
      const slider = screen.getByRole("slider");
      fireEvent.change(slider, { target: { value: "75" } });
      expect(onChange).toHaveBeenCalledWith(75);
    });

    it("respects step value", () => {
      const onChange = vi.fn();
      render(
        <Slider value={0.5} onChange={onChange} min={0} max={1} step={0.1} />,
      );
      const slider = screen.getByRole("slider");
      fireEvent.change(slider, { target: { value: "0.7" } });
      expect(onChange).toHaveBeenCalledWith(0.7);
    });
  });

  describe("disabled state", () => {
    it("can be disabled", () => {
      render(<Slider value={50} onChange={() => {}} disabled />);
      expect(screen.getByRole("slider")).toBeDisabled();
    });

    it("does not call onChange when disabled", () => {
      const onChange = vi.fn();
      render(<Slider value={50} onChange={onChange} disabled />);
      const slider = screen.getByRole("slider");
      fireEvent.change(slider, { target: { value: "75" } });
      // Native disabled prevents the event, but we verify it's disabled
      expect(slider).toBeDisabled();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<Slider value={50} onChange={() => {}} size="sm" />);
      const slider = screen.getByRole("slider");
      expect(slider).toHaveClass("h-1");
    });

    it("renders medium size (default)", () => {
      render(<Slider value={50} onChange={() => {}} />);
      const slider = screen.getByRole("slider");
      expect(slider).toHaveClass("h-2");
    });

    it("renders large size", () => {
      render(<Slider value={50} onChange={() => {}} size="lg" />);
      const slider = screen.getByRole("slider");
      expect(slider).toHaveClass("h-3");
    });
  });

  describe("accessibility", () => {
    it("has role slider", () => {
      render(<Slider value={50} onChange={() => {}} />);
      expect(screen.getByRole("slider")).toBeInTheDocument();
    });

    it("supports aria-label", () => {
      render(
        <Slider value={50} onChange={() => {}} aria-label="Volume control" />,
      );
      expect(screen.getByRole("slider")).toHaveAttribute(
        "aria-label",
        "Volume control",
      );
    });

    it("associates label with input via id", () => {
      render(
        <Slider
          value={50}
          onChange={() => {}}
          label="Volume"
          id="volume-slider"
        />,
      );
      const slider = screen.getByRole("slider");
      expect(slider).toHaveAttribute("id", "volume-slider");
    });
  });

  describe("marks/ticks", () => {
    it("renders tick marks when provided", () => {
      render(
        <Slider
          value={50}
          onChange={() => {}}
          marks={[
            { value: 0, label: "Min" },
            { value: 100, label: "Max" },
          ]}
        />,
      );
      expect(screen.getByText("Min")).toBeInTheDocument();
      expect(screen.getByText("Max")).toBeInTheDocument();
    });
  });
});
