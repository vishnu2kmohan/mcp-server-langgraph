import { vi } from "vitest";
import type { ReasoningEffortLevel } from "../ReasoningEffortSelector";
import type { KBFocusMode } from "../KnowledgeBaseFocus";
import type { ToolSelectionMode } from "@/types/tools";

// Mock lucide-react icons - must be called in each shard via vi.mock()
export const lucideReactMockFactory = () => ({
  Settings2: () => <span data-testid="icon-settings" />,
  ChevronDown: () => <span data-testid="icon-chevron-down" />,
  ChevronRight: () => <span data-testid="icon-chevron-right" />,
  Check: () => <span data-testid="icon-check" />,
  Brain: () => <span data-testid="icon-brain" />,
  Wrench: () => <span data-testid="icon-wrench" />,
  Database: () => <span data-testid="icon-database" />,
  Cpu: () => <span data-testid="icon-cpu" />,
  Loader2: (props: { "data-testid"?: string; "aria-label"?: string }) => (
    <span
      data-testid={props["data-testid"] ?? "icon-loader"}
      aria-label={props["aria-label"]}
    />
  ),
  Sparkles: () => <span data-testid="icon-sparkles" />,
  MessageSquare: () => <span data-testid="icon-message" />,
  Zap: () => <span data-testid="icon-zap" />,
  Palette: () => <span data-testid="icon-palette" />,
});

export const defaultProps = {
  selectedModel: "claude-sonnet-4",
  onModelChange: vi.fn(),
  thinkingLevel: "medium" as ReasoningEffortLevel,
  onThinkingLevelChange: vi.fn(),
  toolMode: "auto" as ToolSelectionMode,
  onToolModeChange: vi.fn(),
  selectedTools: [] as string[],
  onToolsChange: vi.fn(),
  kbFocusMode: "all" as KBFocusMode,
  onKBFocusChange: vi.fn(),
};

export const createDefaultProps = () => ({
  ...defaultProps,
  onModelChange: vi.fn(),
  onThinkingLevelChange: vi.fn(),
  onToolModeChange: vi.fn(),
  onToolsChange: vi.fn(),
  onKBFocusChange: vi.fn(),
});
