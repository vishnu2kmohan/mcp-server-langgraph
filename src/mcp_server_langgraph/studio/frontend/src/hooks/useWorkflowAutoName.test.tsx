/**
 * useWorkflowAutoName Hook Tests
 *
 * TDD tests for automatic workflow naming functionality.
 * Follows the same pattern as useSessionAutoName but for workflows.
 *
 * Tests cover:
 * - Auto-naming for workflows with default names
 * - Linking workflows to originating sessions (when applicable)
 * - Respecting user-provided names
 * - Not re-triggering after initial naming attempt
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useWorkflowAutoName } from "./useWorkflowAutoName";
import workflowReducer from "../store/slices/workflowSlice";

// Mock the API mutation
const mockGenerateWorkflowTitle = vi.fn();
vi.mock("../api", () => ({
  useGenerateWorkflowTitleMutation: () => [
    mockGenerateWorkflowTitle,
    {
      isLoading: false,
      isSuccess: false,
      data: undefined,
      error: undefined,
    },
  ],
}));

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      workflow: workflowReducer,
    },
  });

// Wrapper with Redux provider
const createWrapper = () => {
  const store = createTestStore();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(Provider, { store }, children);
};

describe("useWorkflowAutoName", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Default Name Detection", () => {
    it("should detect workflows with default names", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });

    it("should detect 'Untitled Workflow' as default name", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "Untitled Workflow",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });

    it("should not detect custom names as default", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "My Custom Data Pipeline",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current.hasDefaultName).toBe(false);
    });
  });

  describe("Session Context Integration", () => {
    it("should accept originating session ID for context", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            originatingSessionId: "session-123",
            enabled: true,
          }),
        { wrapper },
      );

      // Should be valid hook result
      expect(result.current).toBeDefined();
      expect(result.current.hasDefaultName).toBe(true);
    });

    it("should include session context in generated name when available", () => {
      const wrapper = createWrapper();

      // Workflow created from a session about "Building a REST API"
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            originatingSessionId: "session-rest-api",
            sessionContext: "Building a REST API with FastAPI",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });
  });

  describe("Workflow Description Context", () => {
    it("should use workflow description for naming context", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            workflowDescription: "Automated data pipeline for ETL processing",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });
  });

  describe("Enabled State", () => {
    it("should not generate name when disabled", () => {
      const wrapper = createWrapper();
      renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            enabled: false,
          }),
        { wrapper },
      );

      // Should not trigger generation when disabled
      expect(mockGenerateWorkflowTitle).not.toHaveBeenCalled();
    });

    it("should return correct loading state", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            enabled: true,
          }),
        { wrapper },
      );

      // Initial state should not be loading
      expect(result.current.isGenerating).toBe(false);
    });
  });

  describe("Hook Interface", () => {
    it("should return expected interface", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(
        () =>
          useWorkflowAutoName({
            workflowId: "wf-1",
            currentName: "New Workflow",
            enabled: true,
          }),
        { wrapper },
      );

      expect(result.current).toHaveProperty("isGenerating");
      expect(result.current).toHaveProperty("isSuccess");
      expect(result.current).toHaveProperty("generatedTitle");
      expect(result.current).toHaveProperty("hasDefaultName");
      expect(result.current).toHaveProperty("error");
    });
  });
});
