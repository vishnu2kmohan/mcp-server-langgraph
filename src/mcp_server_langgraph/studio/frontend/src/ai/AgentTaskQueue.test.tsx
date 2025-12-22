/**
 * AgentTaskQueue Tests
 *
 * TDD tests for the task queue management component that:
 * - Displays queued/running/completed tasks
 * - Allows canceling tasks
 * - Allows clearing completed tasks
 * - Shows task progress
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { AgentTaskQueue } from "./AgentTaskQueue";
import backgroundAgentReducer, {
  addAgent,
  type BackgroundAgent,
} from "../store/slices/backgroundAgentSlice";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = (agents: BackgroundAgent[] = []) => {
  const store = configureStore({
    reducer: {
      backgroundAgent: backgroundAgentReducer,
    },
  });

  agents.forEach((agent) => {
    store.dispatch(addAgent(agent));
  });

  return store;
};

const createMockAgent = (
  overrides: Partial<BackgroundAgent> = {},
): BackgroundAgent => ({
  id: "agent-1",
  name: "Test Agent",
  task: "Processing data",
  status: "queued",
  progress: 0,
  artifacts: [],
  startedAt: Date.now(),
  ...overrides,
});

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("AgentTaskQueue", () => {
  describe("Empty State", () => {
    it("should show empty state when no tasks", () => {
      const store = createTestStore();
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("empty-queue")).toBeInTheDocument();
      expect(screen.getByText(/no tasks/i)).toBeInTheDocument();
    });

    it("should show helpful message in empty state", () => {
      const store = createTestStore();
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(
        screen.getByText(/background agents will appear here/i),
      ).toBeInTheDocument();
    });
  });

  describe("Task Display", () => {
    it("should display queued tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Queued Task", status: "queued" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Queued Task")).toBeInTheDocument();
      // Check status badge contains queued
      expect(screen.getByTestId("status-badge-1")).toHaveTextContent(/queued/i);
    });

    it("should display running tasks with progress", () => {
      const store = createTestStore([
        createMockAgent({
          id: "1",
          name: "Running Task",
          status: "running",
          progress: 45,
        }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Running Task")).toBeInTheDocument();
      expect(screen.getByText("45%")).toBeInTheDocument();
    });

    it("should display completed tasks", () => {
      const store = createTestStore([
        createMockAgent({
          id: "1",
          name: "Completed Task",
          status: "completed",
          progress: 100,
        }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Completed Task")).toBeInTheDocument();
    });

    it("should display failed tasks with error", () => {
      const store = createTestStore([
        createMockAgent({
          id: "1",
          name: "Failed Task",
          status: "failed",
          error: "Connection timeout",
        }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Failed Task")).toBeInTheDocument();
      expect(screen.getByText("Connection timeout")).toBeInTheDocument();
    });

    it("should display task description", () => {
      const store = createTestStore([
        createMockAgent({
          id: "1",
          name: "Test Task",
          task: "Analyzing code patterns",
        }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Analyzing code patterns")).toBeInTheDocument();
    });

    it("should display multiple tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Task 1", status: "queued" }),
        createMockAgent({ id: "2", name: "Task 2", status: "running" }),
        createMockAgent({ id: "3", name: "Task 3", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Task 1")).toBeInTheDocument();
      expect(screen.getByText("Task 2")).toBeInTheDocument();
      expect(screen.getByText("Task 3")).toBeInTheDocument();
    });
  });

  describe("Task Actions", () => {
    it("should show cancel button for queued tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Queued Task", status: "queued" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });

    it("should show cancel button for running tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Running Task", status: "running" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });

    it("should not show cancel button for completed tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Completed Task", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
    });

    it("should call onCancel when cancel button clicked", async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running" }),
      ]);
      render(<AgentTaskQueue onCancel={onCancel} />, {
        wrapper: createWrapper(store),
      });

      await user.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalledWith("1");
    });

    it("should show dismiss button for failed tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "failed", error: "Error" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("button", { name: /dismiss/i })).toBeInTheDocument();
    });

    it("should remove task when dismiss clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Failed Task", status: "failed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      await user.click(screen.getByRole("button", { name: /dismiss/i }));

      expect(screen.queryByText("Failed Task")).not.toBeInTheDocument();
    });
  });

  describe("Clear Completed", () => {
    it("should show clear all button when completed tasks exist", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("button", { name: /clear completed/i })).toBeInTheDocument();
    });

    it("should not show clear all button when no completed tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.queryByRole("button", { name: /clear completed/i })).not.toBeInTheDocument();
    });

    it("should clear completed tasks when clear all clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Running", status: "running" }),
        createMockAgent({ id: "2", name: "Completed", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      await user.click(screen.getByRole("button", { name: /clear completed/i }));

      expect(screen.getByText("Running")).toBeInTheDocument();
      expect(screen.queryByText("Completed")).not.toBeInTheDocument();
    });
  });

  describe("Progress Bar", () => {
    it("should show progress bar for running tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running", progress: 50 }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("should set correct progress value", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running", progress: 75 }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      const progressbar = screen.getByRole("progressbar");
      expect(progressbar).toHaveAttribute("aria-valuenow", "75");
    });

    it("should not show progress bar for queued tasks", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "queued" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    });
  });

  describe("Task Count", () => {
    it("should display total task count in header", () => {
      const store = createTestStore([
        createMockAgent({ id: "1" }),
        createMockAgent({ id: "2" }),
        createMockAgent({ id: "3" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText(/3 tasks/)).toBeInTheDocument();
    });

    it("should display singular for one task", () => {
      const store = createTestStore([createMockAgent({ id: "1" })]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText(/1 task/)).toBeInTheDocument();
    });

    it("should display running count", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running" }),
        createMockAgent({ id: "2", status: "running" }),
        createMockAgent({ id: "3", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByText(/2 running/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading", () => {
      const store = createTestStore([createMockAgent({ id: "1" })]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("heading", { name: /task queue/i })).toBeInTheDocument();
    });

    it("should have accessible task list", () => {
      const store = createTestStore([
        createMockAgent({ id: "1" }),
        createMockAgent({ id: "2" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("should have proper aria-label on cancel buttons", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", name: "Test Task", status: "running" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      expect(
        screen.getByRole("button", { name: /cancel test task/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply custom className", () => {
      const store = createTestStore([createMockAgent({ id: "1" })]);
      render(<AgentTaskQueue className="custom-class" />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByTestId("agent-task-queue")).toHaveClass("custom-class");
    });

    it("should show status badge with correct color for running", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "running" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      const badge = screen.getByTestId("status-badge-1");
      expect(badge).toHaveClass("bg-blue-500");
    });

    it("should show status badge with correct color for completed", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "completed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      const badge = screen.getByTestId("status-badge-1");
      expect(badge).toHaveClass("bg-green-500");
    });

    it("should show status badge with correct color for failed", () => {
      const store = createTestStore([
        createMockAgent({ id: "1", status: "failed" }),
      ]);
      render(<AgentTaskQueue />, { wrapper: createWrapper(store) });

      const badge = screen.getByTestId("status-badge-1");
      expect(badge).toHaveClass("bg-red-500");
    });
  });
});
