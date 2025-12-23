/**
 * FocusMode Component Tests
 *
 * Tests for the JupyterLab-style Simple Interface mode.
 * Allows users to toggle between full workspace and focused single-panel view.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { FocusMode, FocusModeToggle, useFocusMode } from "./FocusMode";
import { renderHook, act } from "@testing-library/react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FocusModeToggle", () => {
  it("renders toggle button", () => {
    render(<FocusModeToggle isFocused={false} onToggle={() => {}} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("shows expand icon when not focused", () => {
    render(<FocusModeToggle isFocused={false} onToggle={() => {}} />);
    expect(screen.getByLabelText("Enter focus mode")).toBeInTheDocument();
  });

  it("shows collapse icon when focused", () => {
    render(<FocusModeToggle isFocused={true} onToggle={() => {}} />);
    expect(screen.getByLabelText("Exit focus mode")).toBeInTheDocument();
  });

  it("calls onToggle when clicked", () => {
    const onToggle = vi.fn();
    render(<FocusModeToggle isFocused={false} onToggle={onToggle} />);

    fireEvent.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("applies custom className", () => {
    render(
      <FocusModeToggle
        isFocused={false}
        onToggle={() => {}}
        className="custom-class"
      />,
    );
    expect(screen.getByRole("button")).toHaveClass("custom-class");
  });
});

describe("FocusMode", () => {
  const defaultProps = {
    leftPanel: <div data-testid="left-panel">Left</div>,
    mainPanel: <div data-testid="main-panel">Main</div>,
    rightPanel: <div data-testid="right-panel">Right</div>,
  };

  describe("normal mode", () => {
    it("renders all three panels", () => {
      render(<FocusMode {...defaultProps} />);

      expect(screen.getByTestId("left-panel")).toBeInTheDocument();
      expect(screen.getByTestId("main-panel")).toBeInTheDocument();
      expect(screen.getByTestId("right-panel")).toBeInTheDocument();
    });

    it("shows focus mode toggle", () => {
      render(<FocusMode {...defaultProps} />);
      expect(screen.getByLabelText("Enter focus mode")).toBeInTheDocument();
    });
  });

  describe("focus mode", () => {
    it("hides side panels when focused", () => {
      render(<FocusMode {...defaultProps} defaultFocused={true} />);

      // Side panels should be aria-hidden when in focus mode
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );
      expect(screen.getByTestId("main-panel")).toBeInTheDocument();
      expect(screen.getByTestId("right-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );
    });

    it("shows exit focus mode button when focused", () => {
      render(<FocusMode {...defaultProps} defaultFocused={true} />);
      expect(screen.getByLabelText("Exit focus mode")).toBeInTheDocument();
    });

    it("toggles focus mode on button click", () => {
      render(<FocusMode {...defaultProps} />);

      // Enter focus mode
      fireEvent.click(screen.getByLabelText("Enter focus mode"));
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );

      // Exit focus mode
      fireEvent.click(screen.getByLabelText("Exit focus mode"));
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "false",
      );
    });
  });

  describe("keyboard shortcuts", () => {
    it("toggles focus mode with Escape key", () => {
      render(<FocusMode {...defaultProps} enableKeyboardShortcut={true} />);

      // Enter focus mode first
      fireEvent.click(screen.getByLabelText("Enter focus mode"));
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );

      // Press Escape to exit
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "false",
      );
    });

    it("does not respond to Escape when keyboard shortcut disabled", () => {
      render(<FocusMode {...defaultProps} enableKeyboardShortcut={false} />);

      fireEvent.click(screen.getByLabelText("Enter focus mode"));
      fireEvent.keyDown(document, { key: "Escape" });

      // Should still be in focus mode
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );
    });
  });

  describe("callbacks", () => {
    it("calls onFocusChange when mode changes", () => {
      const onFocusChange = vi.fn();
      render(<FocusMode {...defaultProps} onFocusChange={onFocusChange} />);

      fireEvent.click(screen.getByLabelText("Enter focus mode"));
      expect(onFocusChange).toHaveBeenCalledWith(true);

      fireEvent.click(screen.getByLabelText("Exit focus mode"));
      expect(onFocusChange).toHaveBeenCalledWith(false);
    });
  });

  describe("controlled mode", () => {
    it("respects controlled isFocused prop", () => {
      const { rerender } = render(
        <FocusMode {...defaultProps} isFocused={false} />,
      );
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "false",
      );

      rerender(<FocusMode {...defaultProps} isFocused={true} />);
      expect(screen.getByTestId("left-panel").parentElement).toHaveAttribute(
        "aria-hidden",
        "true",
      );
    });
  });
});

describe("useFocusMode hook", () => {
  it("initializes with default value", () => {
    const { result } = renderHook(() => useFocusMode(false));
    expect(result.current.isFocused).toBe(false);
  });

  it("toggles focus mode", () => {
    const { result } = renderHook(() => useFocusMode(false));

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isFocused).toBe(true);
  });

  it("enters focus mode", () => {
    const { result } = renderHook(() => useFocusMode(false));

    act(() => {
      result.current.enterFocus();
    });

    expect(result.current.isFocused).toBe(true);
  });

  it("exits focus mode", () => {
    const { result } = renderHook(() => useFocusMode(true));

    act(() => {
      result.current.exitFocus();
    });

    expect(result.current.isFocused).toBe(false);
  });
});
