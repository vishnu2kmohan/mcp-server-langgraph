import { vi } from "vitest";
import type { ModelOption } from "../HeaderModelSelector";
import type { ReasoningEffortLevel } from "../ReasoningEffortSelector";

export const mockModels: ModelOption[] = [
  {
    id: "claude-opus-4.5",
    name: "Claude Opus 4.5",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "preview",
  },
];

export const defaultProps = {
  selectedModel: "claude-opus-4.5",
  availableModels: mockModels,
  onModelChange: vi.fn(),
  thinkingLevel: "medium" as ReasoningEffortLevel,
  onThinkingLevelChange: vi.fn(),
};

export const defaultNativeCapabilitiesMock = {
  capabilities: [],
  nativeProvider: null,
  masterEnabled: false,
  isLoading: false,
  isError: false,
  error: undefined,
  refetch: vi.fn(),
  supportsWebSearch: false,
  supportsCodeExecution: false,
  hasNativeTools: false,
  isToolAvailable: () => false,
  getCapability: () => undefined,
};
