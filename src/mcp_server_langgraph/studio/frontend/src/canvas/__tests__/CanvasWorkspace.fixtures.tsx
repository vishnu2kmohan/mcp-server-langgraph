/**
 * Shared fixtures and test utilities for CanvasWorkspace tests
 *
 * This file contains common test data, mocks, and render helpers
 * used across all CanvasWorkspace test shards.
 */
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import canvasReducer from "../../store/slices/canvasSlice";
import type { CanvasArtifact } from "../../types/artifacts";

// =============================================================================
// Mock Artifacts
// =============================================================================

export const mockArtifacts: CanvasArtifact[] = [
  {
    id: "artifact-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: 'console.log("Hello, World!");',
    contentType: "code",
    title: "Hello World",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
    editMetadata: {
      editedBy: "user",
      language: "javascript",
    },
  },
  {
    id: "artifact-2",
    type: "code",
    sessionId: "session-1",
    version: 2,
    content: "# README\n\nThis is a readme file.",
    contentType: "markdown",
    title: "README",
    createdAt: "2024-01-01T01:00:00Z",
    updatedAt: "2024-01-01T01:00:00Z",
    editMetadata: {
      editedBy: "ai-generation",
      aiConfidence: 0.95,
    },
  },
];

export const mermaidArtifact: CanvasArtifact[] = [
  {
    id: "mermaid-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: "graph TD\n  A --> B",
    contentType: "mermaid",
    title: "Mermaid Diagram",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
];

export const jsonArtifact: CanvasArtifact[] = [
  {
    id: "json-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: '{"name": "test", "value": 123}',
    contentType: "json",
    title: "JSON Data",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
];

export const artifactWithoutTitle: CanvasArtifact[] = [
  {
    id: "abcdef123456",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: "test",
    contentType: "code",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
];

export const aiSuggestionArtifact: CanvasArtifact[] = [
  {
    id: "ai-sug-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: "AI suggested code",
    contentType: "code",
    title: "AI Suggestion",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
    editMetadata: {
      editedBy: "ai-suggestion",
      aiConfidence: 0.8,
    },
  },
];

export const userEditedArtifact: CanvasArtifact[] = [
  {
    id: "user-edit-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: "User code",
    contentType: "code",
    title: "User Code",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
    editMetadata: {
      editedBy: "user",
    },
  },
];

export const multiLineArtifacts: CanvasArtifact[] = [
  {
    id: "multi-line",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: "line1\nline2\nline3\nline4\nline5",
    contentType: "code",
    title: "Multi-Line",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
    editMetadata: {
      editedBy: "user",
      language: "text",
    },
  },
];

// =============================================================================
// Mock Intelligence Data
// =============================================================================

export const mockCodeAnalysis = {
  qualityScore: 85,
  complexity: 5,
  issues: [],
  suggestions: [],
  isLoading: false,
  error: null,
};

export const mockDiagramAnalysis = {
  isValid: true,
  diagramType: "flowchart",
  nodeCount: 5,
  edgeCount: 4,
  issues: [],
  suggestions: [],
  isLoading: false,
  error: null,
};

// =============================================================================
// Store Creation Utilities
// =============================================================================

export function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
    },
    preloadedState,
  });
}

export const defaultCanvasState = {
  panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
  sessionNavCollapsed: false,
  canvasCollapsed: false,
  activeNavItem: "chat",
  selectedArtifactId: null,
  preferences: {
    showTimestamps: true,
    compactMode: false,
    showLineNumbers: true,
    codeTheme: "auto",
  },
};

export function createStoreWithArtifact(artifactId: string) {
  return createTestStore({
    canvas: {
      ...defaultCanvasState,
      selectedArtifactId: artifactId,
    },
  });
}

// =============================================================================
// Render Utilities
// =============================================================================

export function renderWithProviders(
  ui: React.ReactElement,
  { store = createTestStore(), ...options } = {},
) {
  return render(
    <Provider store={store}>
      <MemoryRouter>{ui}</MemoryRouter>
    </Provider>,
    options,
  );
}
