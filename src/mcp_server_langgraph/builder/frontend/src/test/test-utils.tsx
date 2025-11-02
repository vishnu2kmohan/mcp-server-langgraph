/**
 * Testing Utilities
 *
 * Custom render function and test helpers for React components.
 * Provides React Flow wrapper and common testing utilities.
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ReactFlowProvider } from 'reactflow';

/**
 * Custom render function that wraps components with necessary providers
 */
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    return <ReactFlowProvider>{children}</ReactFlowProvider>;
  };

  return render(ui, { wrapper: Wrapper, ...options });
}

/**
 * Mock workflow data for testing
 */
export const mockWorkflow = {
  name: 'test_workflow',
  description: 'Test workflow for testing',
  nodes: [
    {
      id: 'node1',
      type: 'default',
      data: { label: 'Search', nodeType: 'tool', config: { tool: 'web_search' } },
      position: { x: 100, y: 100 },
    },
    {
      id: 'node2',
      type: 'default',
      data: { label: 'Process', nodeType: 'llm', config: { model: 'gemini-flash' } },
      position: { x: 300, y: 100 },
    },
  ],
  edges: [
    {
      id: 'edge1',
      source: 'node1',
      target: 'node2',
    },
  ],
};

/**
 * Mock generated Python code
 */
export const mockGeneratedCode = `"""
Test workflow for testing

Auto-generated from Visual Workflow Builder.
"""

from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


class TestWorkflowState(TypedDict):
    """State for test_workflow workflow."""
    query: str
    result: str


def node_node1(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Search - tool: web_search."""
    result = call_tool("web_search", state)
    state["result"] = result
    return state


def node_node2(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Process - LLM: gemini-flash."""
    from litellm import completion

    response = completion(
        model="gemini-flash",
        messages=[{"role": "user", "content": state["query"]}]
    )
    state["llm_response"] = response.choices[0].message.content
    return state


def create_test_workflow() -> StateGraph:
    """
    Create test_workflow workflow.

    Returns:
        Compiled LangGraph application
    """
    graph = StateGraph(TestWorkflowState)

    graph.add_node("node1", node_node1)
    graph.add_node("node2", node_node2)

    graph.add_edge("node1", "node2")

    graph.set_entry_point("node1")
    graph.set_finish_point("node2")

    return graph
`;

/**
 * Create mock axios response
 */
export const createMockAxiosResponse = <T,>(data: T) => ({
  data,
  status: 200,
  statusText: 'OK',
  headers: {},
  config: {} as any,
});

/**
 * Create mock axios error
 */
export const createMockAxiosError = (message: string, status = 400) => ({
  response: {
    data: { detail: message },
    status,
    statusText: status === 400 ? 'Bad Request' : 'Internal Server Error',
    headers: {},
    config: {} as any,
  },
  message,
  isAxiosError: true,
});

// Re-export everything from React Testing Library
export * from '@testing-library/react';
export { customRender as render };
