/**
 * OrchestratorControls Tests
 *
 * Tests for the orchestrator configuration controls component.
 * Features:
 * - Orchestrator mode selector (standard/swarm/studio/ux/alert)
 * - Thinking budget dropdown (none/light/medium/deep)
 * - Critique rounds slider (0-3)
 * - Auto-approve toggle
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  OrchestratorControls,
  type OrchestratorConfig,
} from "./OrchestratorControls";

import { TestProvider } from "@/test-utils";

describe("OrchestratorControls", () => {
  const defaultConfig: OrchestratorConfig = {
    orchestrator: "standard",
    thinkingBudget: "medium",
    critiqueRounds: 1,
    autoApprove: false,
  };

  const defaultProps = {
    config: defaultConfig,
    onChange: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render orchestrator controls heading", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByText(/orchestrator configuration/i),
      ).toBeInTheDocument();
    });

    it("should render orchestrator mode selector", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/orchestrator mode/i)).toBeInTheDocument();
    });

    it("should render thinking budget selector", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/thinking budget/i)).toBeInTheDocument();
    });

    it("should render critique rounds control", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/critique rounds/i)).toBeInTheDocument();
    });

    it("should render auto-approve toggle", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/auto-approve/i)).toBeInTheDocument();
    });
  });

  describe("Orchestrator Mode", () => {
    it("should display current orchestrator mode", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const select = screen.getByLabelText(
        /orchestrator mode/i,
      ) as HTMLSelectElement;
      expect(select.value).toBe("standard");
    });

    it("should have all orchestrator options", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("option", { name: /standard/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /swarm/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /studio/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /ux/i })).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /alert/i }),
      ).toBeInTheDocument();
    });

    it("should call onChange when orchestrator mode changes", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const select = screen.getByLabelText(/orchestrator mode/i);
      fireEvent.change(select, { target: { value: "swarm" } });
      expect(defaultProps.onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        orchestrator: "swarm",
      });
    });
  });

  describe("Thinking Budget", () => {
    it("should display current thinking budget", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const select = screen.getByLabelText(
        /thinking budget/i,
      ) as HTMLSelectElement;
      expect(select.value).toBe("medium");
    });

    it("should have all thinking budget options", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("option", { name: /none/i })).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /light/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /medium/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /deep/i })).toBeInTheDocument();
    });

    it("should call onChange when thinking budget changes", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const select = screen.getByLabelText(/thinking budget/i);
      fireEvent.change(select, { target: { value: "deep" } });
      expect(defaultProps.onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        thinkingBudget: "deep",
      });
    });
  });

  describe("Critique Rounds", () => {
    it("should display current critique rounds value", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const input = screen.getByLabelText(
        /critique rounds/i,
      ) as HTMLInputElement;
      expect(input.value).toBe("1");
    });

    it("should have min 0 and max 3", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const input = screen.getByLabelText(
        /critique rounds/i,
      ) as HTMLInputElement;
      expect(input.min).toBe("0");
      expect(input.max).toBe("3");
    });

    it("should call onChange when critique rounds changes", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const input = screen.getByLabelText(/critique rounds/i);
      fireEvent.change(input, { target: { value: "2" } });
      expect(defaultProps.onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        critiqueRounds: 2,
      });
    });
  });

  describe("Auto-Approve Toggle", () => {
    it("should display current auto-approve state", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const checkbox = screen.getByLabelText(
        /auto-approve/i,
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
    });

    it("should display checked when auto-approve is true", () => {
      const propsWithAutoApprove = {
        ...defaultProps,
        config: { ...defaultConfig, autoApprove: true },
      };
      render(
        <TestProvider>
          <OrchestratorControls {...propsWithAutoApprove} />
        </TestProvider>,
      );
      const checkbox = screen.getByLabelText(
        /auto-approve/i,
      ) as HTMLInputElement;
      expect(checkbox.checked).toBe(true);
    });

    it("should call onChange when auto-approve is toggled", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} />
        </TestProvider>,
      );
      const checkbox = screen.getByLabelText(/auto-approve/i);
      fireEvent.click(checkbox);
      expect(defaultProps.onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        autoApprove: true,
      });
    });
  });

  describe("Disabled State", () => {
    it("should disable orchestrator selector when disabled", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} disabled={true} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/orchestrator mode/i)).toBeDisabled();
    });

    it("should disable thinking budget selector when disabled", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} disabled={true} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/thinking budget/i)).toBeDisabled();
    });

    it("should disable critique rounds input when disabled", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} disabled={true} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/critique rounds/i)).toBeDisabled();
    });

    it("should disable auto-approve toggle when disabled", () => {
      render(
        <TestProvider>
          <OrchestratorControls {...defaultProps} disabled={true} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/auto-approve/i)).toBeDisabled();
    });
  });
});
