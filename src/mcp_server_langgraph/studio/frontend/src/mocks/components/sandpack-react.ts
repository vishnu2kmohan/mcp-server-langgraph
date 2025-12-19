/**
 * Mock for @codesandbox/sandpack-react
 *
 * This mock provides test-friendly implementations of Sandpack components
 * that avoid CSS-in-JS (Stitches) compatibility issues with jsdom 27.
 *
 * jsdom 27 uses @acemir/cssom which has stricter CSS parsing that fails on
 * Stitches' internal CSS rules like '--sxs{--sxs:6}'.
 *
 * Usage in test files:
 *
 * ```typescript
 * import { vi } from "vitest";
 *
 * vi.mock("@codesandbox/sandpack-react", () => import("../mocks/components/sandpack-react"));
 * ```
 *
 * Or add to vitest.config.ts for global mocking:
 * ```typescript
 * alias: {
 *   "@codesandbox/sandpack-react": "./src/mocks/components/sandpack-react.ts",
 * }
 * ```
 */

import React from "react";
import { vi } from "vitest";

// =============================================================================
// Types (simplified from @codesandbox/sandpack-react)
// =============================================================================

interface SandpackProviderProps {
  children?: React.ReactNode;
  template?: string;
  theme?: string | object;
  files?: Record<string, string>;
  customSetup?: {
    dependencies?: Record<string, string>;
    entry?: string;
  };
  options?: {
    autorun?: boolean;
    autoReload?: boolean;
  };
}

interface SandpackLayoutProps {
  children?: React.ReactNode;
}

interface SandpackPreviewProps {
  style?: React.CSSProperties;
}

interface SandpackCodeEditorProps {
  showLineNumbers?: boolean;
  showTabs?: boolean;
  readOnly?: boolean;
  style?: React.CSSProperties;
}

interface SandpackContextValue {
  status: "initial" | "idle" | "running" | "timeout" | "error";
  error: Error | null;
  dispatch: ReturnType<typeof vi.fn>;
  listen: ReturnType<typeof vi.fn>;
}

// =============================================================================
// Mock Context
// =============================================================================

const SandpackContext = React.createContext<{ sandpack: SandpackContextValue }>(
  {
    sandpack: {
      status: "idle",
      error: null,
      dispatch: vi.fn(),
      listen: vi.fn(),
    },
  },
);

// =============================================================================
// Mock Components
// =============================================================================

/**
 * Mock SandpackProvider component.
 * Provides a mock context without loading Stitches.
 */
export const SandpackProvider = ({
  children,
}: SandpackProviderProps): React.ReactElement => {
  const mockSandpack: SandpackContextValue = {
    status: "idle",
    error: null,
    dispatch: vi.fn(),
    listen: vi.fn(),
  };

  return React.createElement(
    SandpackContext.Provider,
    { value: { sandpack: mockSandpack } },
    React.createElement(
      "div",
      { "data-testid": "sandpack-provider" },
      children,
    ),
  );
};

/**
 * Mock SandpackLayout component.
 * Simple flex container for layout.
 */
export const SandpackLayout = ({
  children,
}: SandpackLayoutProps): React.ReactElement => {
  return React.createElement(
    "div",
    {
      "data-testid": "sandpack-layout",
      style: { display: "flex", flexDirection: "column" },
    },
    children,
  );
};

/**
 * Mock SandpackPreview component.
 * Shows a placeholder preview area.
 */
export const SandpackPreview = ({
  style,
}: SandpackPreviewProps): React.ReactElement => {
  return React.createElement(
    "div",
    {
      "data-testid": "sandpack-preview",
      style: { ...style, backgroundColor: "#f5f5f5", padding: "16px" },
    },
    "Preview Area",
  );
};

/**
 * Mock SandpackCodeEditor component.
 * Shows code in a simple pre tag.
 */
export const SandpackCodeEditor = ({
  style,
}: SandpackCodeEditorProps): React.ReactElement => {
  return React.createElement(
    "pre",
    {
      "data-testid": "sandpack-code-editor",
      style: {
        ...style,
        backgroundColor: "#1e1e1e",
        color: "#d4d4d4",
        padding: "16px",
        fontFamily: "monospace",
      },
    },
    "// Code Editor",
  );
};

/**
 * Mock useSandpack hook.
 * Returns mock context value.
 */
export const useSandpack = (): { sandpack: SandpackContextValue } => {
  return React.useContext(SandpackContext);
};

// =============================================================================
// Additional exports that components might use
// =============================================================================

export const SandpackConsole = (): React.ReactElement => {
  return React.createElement(
    "div",
    { "data-testid": "sandpack-console" },
    "Console Output",
  );
};

export const SandpackFileExplorer = (): React.ReactElement => {
  return React.createElement(
    "div",
    { "data-testid": "sandpack-file-explorer" },
    "File Explorer",
  );
};

export const SandpackThemeProvider = ({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement => {
  return React.createElement(React.Fragment, null, children);
};

// Theme constants that might be imported
export const nightOwl = {};
export const cobalt2 = {};
export const githubLight = {};
export const sandpackDark = {};

// =============================================================================
// Default Export
// =============================================================================

export default {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview,
  SandpackCodeEditor,
  SandpackConsole,
  SandpackFileExplorer,
  SandpackThemeProvider,
  useSandpack,
  nightOwl,
  cobalt2,
  githubLight,
  sandpackDark,
};
