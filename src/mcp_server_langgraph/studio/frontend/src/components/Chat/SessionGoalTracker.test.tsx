/**
 * SessionGoalTracker Component Tests
 *
 * TDD tests for multi-turn conversation goal tracking.
 * Allows users to set goals and track achievement.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  SessionGoalTracker,
  SessionGoalTrackerProps,
} from "./SessionGoalTracker";

describe("SessionGoalTracker", () => {
  const defaultProps: SessionGoalTrackerProps = {
    sessionId: "session-123",
    onGoalSet: vi.fn(),
    onGoalComplete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Goal Input Mode", () => {
    it("should display goal input when no goal is set", () => {
      render(<SessionGoalTracker {...defaultProps} />);
      expect(
        screen.getByPlaceholderText(/what would you like to accomplish/i),
      ).toBeInTheDocument();
    });

    it("should have set goal button", () => {
      render(<SessionGoalTracker {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /set goal/i }),
      ).toBeInTheDocument();
    });

    it("should call onGoalSet when goal is submitted", () => {
      render(<SessionGoalTracker {...defaultProps} />);

      const input = screen.getByPlaceholderText(
        /what would you like to accomplish/i,
      );
      fireEvent.change(input, { target: { value: "Write a Python script" } });
      fireEvent.click(screen.getByRole("button", { name: /set goal/i }));

      expect(defaultProps.onGoalSet).toHaveBeenCalledWith({
        sessionId: "session-123",
        goal: "Write a Python script",
        timestamp: expect.any(Number),
      });
    });

    it("should disable set button when input is empty", () => {
      render(<SessionGoalTracker {...defaultProps} />);
      const setButton = screen.getByRole("button", { name: /set goal/i });
      expect(setButton).toBeDisabled();
    });

    it("should enable set button when input has text", () => {
      render(<SessionGoalTracker {...defaultProps} />);

      const input = screen.getByPlaceholderText(
        /what would you like to accomplish/i,
      );
      fireEvent.change(input, { target: { value: "Write code" } });

      const setButton = screen.getByRole("button", { name: /set goal/i });
      expect(setButton).not.toBeDisabled();
    });
  });

  describe("Active Goal Display", () => {
    it("should display active goal when provided", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(screen.getByText("Write a Python script")).toBeInTheDocument();
    });

    it("should show goal label", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(screen.getByText(/current goal/i)).toBeInTheDocument();
    });

    it("should hide input when goal is active", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(
        screen.queryByPlaceholderText(/what would you like to accomplish/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("Goal Completion", () => {
    it("should show completion options when goal is active", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(
        screen.getByRole("button", { name: /^achieved$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /not achieved/i }),
      ).toBeInTheDocument();
    });

    it("should call onGoalComplete with achieved=true", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /^achieved$/i }));

      expect(defaultProps.onGoalComplete).toHaveBeenCalledWith({
        sessionId: "session-123",
        goal: "Write a Python script",
        achieved: true,
        timestamp: expect.any(Number),
      });
    });

    it("should call onGoalComplete with achieved=false", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /not achieved/i }));

      expect(defaultProps.onGoalComplete).toHaveBeenCalledWith({
        sessionId: "session-123",
        goal: "Write a Python script",
        achieved: false,
        timestamp: expect.any(Number),
      });
    });

    it("should show partial option", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(
        screen.getByRole("button", { name: /partially/i }),
      ).toBeInTheDocument();
    });

    it("should call onGoalComplete with achieved=partial", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /partially/i }));

      expect(defaultProps.onGoalComplete).toHaveBeenCalledWith({
        sessionId: "session-123",
        goal: "Write a Python script",
        achieved: "partial",
        timestamp: expect.any(Number),
      });
    });
  });

  describe("Compact Mode", () => {
    it("should render compact when compact prop is true", () => {
      render(<SessionGoalTracker {...defaultProps} compact />);
      const tracker = screen.getByTestId("session-goal-tracker");
      expect(tracker).toHaveClass("compact");
    });

    it("should show condensed goal display in compact mode", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
          compact
        />,
      );
      const tracker = screen.getByTestId("session-goal-tracker");
      expect(tracker).toHaveClass("compact");
    });
  });

  describe("Edit Goal", () => {
    it("should have edit button when goal is active", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });

    it("should show input when edit is clicked", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /edit/i }));

      expect(
        screen.getByDisplayValue("Write a Python script"),
      ).toBeInTheDocument();
    });

    it("should update goal when saved after edit", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /edit/i }));

      const input = screen.getByDisplayValue("Write a Python script");
      fireEvent.change(input, {
        target: { value: "Write a JavaScript function" },
      });
      fireEvent.click(screen.getByRole("button", { name: /save/i }));

      expect(defaultProps.onGoalSet).toHaveBeenCalledWith({
        sessionId: "session-123",
        goal: "Write a JavaScript function",
        timestamp: expect.any(Number),
      });
    });
  });

  describe("Clear Goal", () => {
    it("should have clear button when goal is active", () => {
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
        />,
      );
      expect(
        screen.getByRole("button", { name: /clear/i }),
      ).toBeInTheDocument();
    });

    it("should clear goal and show input when cleared", () => {
      const onClear = vi.fn();
      render(
        <SessionGoalTracker
          {...defaultProps}
          currentGoal="Write a Python script"
          onGoalClear={onClear}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /clear/i }));

      expect(onClear).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible input label", () => {
      render(<SessionGoalTracker {...defaultProps} />);
      const input = screen.getByPlaceholderText(
        /what would you like to accomplish/i,
      );
      expect(input).toHaveAttribute("aria-label");
    });

    it("should have testid for tracking", () => {
      render(<SessionGoalTracker {...defaultProps} />);
      expect(screen.getByTestId("session-goal-tracker")).toBeInTheDocument();
    });
  });
});
