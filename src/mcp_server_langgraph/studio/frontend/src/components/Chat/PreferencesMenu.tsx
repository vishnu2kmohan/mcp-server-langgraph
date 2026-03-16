/**
 * PreferencesMenu Component
 *
 * Hierarchical preferences dropdown for chat input settings using Radix UI.
 * Provides access to:
 * - Model selection (with thinking level)
 * - Tool selection mode (with nested tool provider)
 * - Knowledge Base focus mode
 *
 * Design System Compliance:
 * - Uses Radix UI DropdownMenu for accessibility
 * - Uses CVA for variant styling
 * - Uses Radix 1-12 color scale
 * - Focus rings: focus-visible:ring-2 focus-visible:ring-primary-7
 * - Touch targets: 32px minimum (WCAG 2.5.8)
 * - Reduced motion: motion-reduce:animate-none for prefers-reduced-motion
 *
 * @see Chat Input UX Plan for architecture details
 */

import { forwardRef, type ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Settings2,
  ChevronDown,
  ChevronRight,
  Check,
  Brain,
  Wrench,
  Database,
  Loader2,
  Cpu,
  Sparkles,
  MessageSquare,
  Zap,
  Palette,
} from "lucide-react";
import { cn } from "../../utils/cn";
import { Button } from "@/components/UI";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { KBFocusMode } from "./KnowledgeBaseFocus";
import type { ToolSelectionMode, ToolPreference } from "@/types/tools";
import { formatProviderDisplay } from "@/utils/modelDisplay";
import type { ModelOption } from "./ChatInput";
import type { ToolOption } from "./ToolSelector";
import type { PresetName, StylePreset } from "./StylePresets";
import { PRESET_CONFIGS } from "./StylePresets";

// =============================================================================
// Types
// =============================================================================

export interface PreferencesMenuProps {
  /** Currently selected model ID */
  selectedModel?: string;
  /** Available models for selection */
  availableModels?: ModelOption[];
  /** Whether models are loading */
  isModelsLoading?: boolean;
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Current thinking level */
  thinkingLevel?: ReasoningEffortLevel;
  /** Callback when thinking level changes */
  onThinkingLevelChange?: (level: ReasoningEffortLevel) => void;
  /** Current tool selection mode */
  toolMode?: ToolSelectionMode;
  /** Callback when tool mode changes */
  onToolModeChange?: (mode: ToolSelectionMode) => void;
  /** Currently selected tools (tool IDs) */
  selectedTools?: string[];
  /** Callback when tools change */
  onToolsChange?: (tools: string[]) => void;
  /** Available tools for multi-select (when toolMode is manual) */
  availableTools?: ToolOption[];
  /** Current KB focus mode */
  kbFocusMode?: KBFocusMode;
  /** Callback when KB focus mode changes */
  onKBFocusChange?: (mode: KBFocusMode) => void;
  // v7: Native tool preference
  /** Current tool preference (auto/native/builtin/mcp) */
  toolPreference?: ToolPreference;
  /** Callback when tool preference changes */
  onToolPreferenceChange?: (preference: ToolPreference) => void;
  /** Whether the menu is loading */
  isLoading?: boolean;
  /** Whether the menu is disabled */
  disabled?: boolean;
  /** Compact mode for smaller displays */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  // =========================================================================
  // Executor/Critic Model Selection (Critique Loop)
  // =========================================================================
  /** Whether critique loop is enabled (FF_ENABLE_CRITIQUE_LOOP) */
  critiqueLoopEnabled?: boolean;
  /** Currently selected executor model ID (for critique loop) */
  executorModel?: string | null;
  /** Callback when executor model changes */
  onExecutorModelChange?: (modelId: string | null) => void;
  /** Currently selected critic model ID (for critique loop) */
  criticModel?: string | null;
  /** Callback when critic model changes */
  onCriticModelChange?: (modelId: string | null) => void;
  // =========================================================================
  // Style Presets
  // =========================================================================
  /** Currently active style preset */
  activeStylePreset?: PresetName;
  /** Callback when style preset changes */
  onStylePresetChange?: (preset: StylePreset) => void;
}

// =============================================================================
// Constants
// =============================================================================

const THINKING_LEVELS: { value: ReasoningEffortLevel; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const TOOL_MODES: { value: ToolSelectionMode; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "manual", label: "Manual" },
  { value: "none", label: "None" },
];

const STYLE_PRESET_OPTIONS: {
  value: PresetName;
  label: string;
  description: string;
  icon: typeof Sparkles;
}[] = [
  {
    value: "creative",
    label: "Creative",
    description: `Temperature ${PRESET_CONFIGS.creative.temperature}, ${PRESET_CONFIGS.creative.maxTokens} tokens`,
    icon: Sparkles,
  },
  {
    value: "balanced",
    label: "Balanced",
    description: `Temperature ${PRESET_CONFIGS.balanced.temperature}, ${PRESET_CONFIGS.balanced.maxTokens} tokens`,
    icon: MessageSquare,
  },
  {
    value: "precise",
    label: "Precise",
    description: `Temperature ${PRESET_CONFIGS.precise.temperature}, ${PRESET_CONFIGS.precise.maxTokens} tokens`,
    icon: Cpu,
  },
];

// PRESET_CONFIGS imported directly from StylePresets.tsx (single source of truth)

const KB_FOCUS_MODES: { value: KBFocusMode; label: string }[] = [
  { value: "all", label: "All Sources" },
  { value: "kb_only", label: "KB Only" },
  { value: "web_only", label: "Web Only" },
  { value: "none", label: "None" },
];

// v7: Tool preference modes for native vs builtin execution
const TOOL_PREFERENCE_MODES: {
  value: ToolPreference;
  label: string;
  description: string;
}[] = [
  { value: "auto", label: "Auto", description: "Prefer native when available" },
  {
    value: "native",
    label: "Native Only",
    description: "Use LLM provider tools",
  },
  {
    value: "builtin",
    label: "Built-in Only",
    description: "Use server-side tools",
  },
  { value: "mcp", label: "MCP Only", description: "Use MCP server tools" },
];

// =============================================================================
// Helpers
// =============================================================================

// formatProviderDisplay imported from @/utils/modelDisplay

/**
 * Get display label for thinking level
 */
function getThinkingLevelLabel(level: ReasoningEffortLevel): string {
  return THINKING_LEVELS.find((l) => l.value === level)?.label ?? "Medium";
}

/**
 * Get display label for tool mode
 */
function getToolModeLabel(mode: ToolSelectionMode): string {
  return TOOL_MODES.find((m) => m.value === mode)?.label ?? "Auto";
}

/**
 * Get display label for KB focus mode
 */
function getKBFocusModeLabel(mode: KBFocusMode): string {
  return KB_FOCUS_MODES.find((m) => m.value === mode)?.label ?? "All Sources";
}

/**
 * Get display label for style preset
 */
function getStylePresetLabel(preset?: PresetName): string {
  return (
    STYLE_PRESET_OPTIONS.find((p) => p.value === preset)?.label ?? "Balanced"
  );
}

/**
 * Get display label for tool preference
 */
function getToolPreferenceLabel(pref: ToolPreference): string {
  return TOOL_PREFERENCE_MODES.find((p) => p.value === pref)?.label ?? "Auto";
}

// =============================================================================
// Styled Components
// =============================================================================

// Styled SubMenu Trigger
// Note: Radix DropdownMenu.SubTrigger types its ref as HTMLDivElement
const SubMenuTrigger = forwardRef<
  HTMLDivElement,
  {
    icon: ReactNode;
    label: string;
    value: string;
    "data-testid"?: string;
  }
>(({ icon, label, value, "data-testid": testId, ...props }, ref) => (
  <DropdownMenu.SubTrigger
    ref={ref}
    data-testid={testId}
    className={cn(
      "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
      "text-neutral-11 hover:bg-neutral-4 hover:text-neutral-12",
      "focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
      "cursor-pointer rounded-md",
      "transition-colors duration-150",
      "data-[state=open]:bg-neutral-4",
    )}
    {...props}
  >
    <div className="flex items-center gap-2">
      {icon}
      <span className="font-medium">{label}:</span>
      <span className="text-neutral-10">{value}</span>
    </div>
    <ChevronRight className="h-4 w-4 text-neutral-9" aria-hidden="true" />
  </DropdownMenu.SubTrigger>
));
SubMenuTrigger.displayName = "SubMenuTrigger";

// Styled SubMenu Content
const SubMenuContent = forwardRef<
  HTMLDivElement,
  { children: ReactNode; "data-testid"?: string }
>(({ children, "data-testid": testId, ...props }, ref) => (
  <DropdownMenu.Portal>
    <DropdownMenu.SubContent
      ref={ref}
      data-testid={testId}
      sideOffset={2}
      alignOffset={-4}
      className={cn(
        "min-w-[180px] rounded-lg p-1",
        "bg-neutral-2 border border-neutral-6",
        "shadow-elevated z-dropdown",
        "max-h-[300px] overflow-y-auto",
        // Animation (respects prefers-reduced-motion via motion-reduce)
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
        "data-[side=bottom]:slide-in-from-top-2",
        "data-[side=left]:slide-in-from-right-2",
        "data-[side=right]:slide-in-from-left-2",
        "data-[side=top]:slide-in-from-bottom-2",
        // Reduced motion: disable animations for accessibility
        "motion-reduce:animate-none motion-reduce:transition-none",
      )}
      {...props}
    >
      {children}
    </DropdownMenu.SubContent>
  </DropdownMenu.Portal>
));
SubMenuContent.displayName = "SubMenuContent";

// =============================================================================
// Component
// =============================================================================

export function PreferencesMenu({
  selectedModel,
  availableModels = [],
  isModelsLoading = false,
  onModelChange,
  thinkingLevel = "medium",
  onThinkingLevelChange,
  toolMode = "auto",
  onToolModeChange,
  // Tool selection props for individual tool multi-select (when toolMode is manual)
  selectedTools = [],
  onToolsChange,
  availableTools = [],
  kbFocusMode = "all",
  onKBFocusChange,
  // v7: Native tool preference
  toolPreference = "auto",
  onToolPreferenceChange,
  isLoading = false,
  disabled = false,
  compact = false,
  className,
  // Executor/Critic props
  critiqueLoopEnabled = false,
  executorModel,
  onExecutorModelChange,
  criticModel,
  onCriticModelChange,
  // Style presets
  activeStylePreset,
  onStylePresetChange,
}: PreferencesMenuProps) {
  // Normalize style preset so RadioGroup value and highlight class stay in sync
  const effectiveStylePreset: PresetName = activeStylePreset ?? "balanced";

  // Get current model display name
  const currentModel = availableModels.find((m) => m.id === selectedModel);
  const currentModelName = currentModel?.name ?? "Select Model";

  return (
    <div data-testid="preferences-menu" className={cn("relative", className)}>
      <DropdownMenu.Root>
        {/* Trigger Button */}
        <DropdownMenu.Trigger asChild>
          <Button
            variant="ghost"
            type="button"
            data-testid="preferences-menu-trigger"
            disabled={disabled || isLoading}
            aria-label="Open preferences menu"
            className={cn(
              "group inline-flex items-center gap-1.5 rounded-md text-sm font-medium",
              "min-h-8 transition-colors duration-150",
              "bg-neutral-3 text-neutral-11 hover:bg-neutral-4",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              compact ? "px-2" : "px-3",
            )}
          >
            {isLoading ? (
              <Loader2
                className="h-4 w-4 animate-spin"
                data-testid="preferences-loading"
                aria-hidden="true"
              />
            ) : (
              <Settings2 className="h-4 w-4" aria-hidden="true" />
            )}
            {!compact && <span>Preferences</span>}
            <ChevronDown
              className="h-3 w-3 transition-transform duration-150 group-data-[state=open]:rotate-180"
              aria-hidden="true"
            />
          </Button>
        </DropdownMenu.Trigger>

        {/* Dropdown Content */}
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            data-testid="preferences-dropdown"
            side="top"
            align="end"
            sideOffset={4}
            collisionPadding={8}
            className={cn(
              "min-w-[240px] rounded-lg p-1",
              "bg-neutral-2 border border-neutral-6",
              "shadow-elevated z-dropdown",
              // Animation (respects prefers-reduced-motion via motion-reduce)
              "data-[state=open]:animate-in data-[state=closed]:animate-out",
              "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
              "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
              "data-[side=bottom]:slide-in-from-top-2",
              "data-[side=top]:slide-in-from-bottom-2",
              // Reduced motion: disable animations for accessibility
              "motion-reduce:animate-none motion-reduce:transition-none",
            )}
          >
            {/* Model Submenu - Always render to show loading/empty states */}
            <DropdownMenu.Sub>
              <SubMenuTrigger
                data-testid="submenu-trigger-model"
                icon={<Cpu className="h-4 w-4" aria-hidden="true" />}
                label="Model"
                value={currentModelName}
              />
              <SubMenuContent data-testid="submenu-content-model">
                {isModelsLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2
                      className="h-4 w-4 animate-spin text-neutral-9"
                      aria-label="Loading models"
                    />
                  </div>
                ) : availableModels.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-neutral-10">
                    No models available
                  </div>
                ) : (
                  <DropdownMenu.RadioGroup
                    value={selectedModel}
                    onValueChange={(value) => onModelChange?.(value)}
                  >
                    {availableModels.map((model) => (
                      <DropdownMenu.RadioItem
                        key={model.id}
                        value={model.id}
                        className={cn(
                          "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                          "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                          "cursor-pointer rounded-md",
                          "transition-colors duration-150",
                          selectedModel === model.id
                            ? "text-primary-11 bg-primary-3"
                            : "text-neutral-12",
                        )}
                      >
                        <div className="flex flex-col items-start gap-0.5">
                          <span className="font-medium">{model.name}</span>
                          <span className="text-xs text-neutral-10">
                            {formatProviderDisplay(model)}
                          </span>
                        </div>
                        <DropdownMenu.ItemIndicator>
                          <Check className="h-4 w-4" aria-hidden="true" />
                        </DropdownMenu.ItemIndicator>
                      </DropdownMenu.RadioItem>
                    ))}
                  </DropdownMenu.RadioGroup>
                )}
              </SubMenuContent>
            </DropdownMenu.Sub>

            {/* Executor Model Submenu (Critique Loop) */}
            {critiqueLoopEnabled && availableModels.length > 0 && (
              <DropdownMenu.Sub>
                <SubMenuTrigger
                  data-testid="submenu-trigger-executor"
                  icon={<Sparkles className="h-4 w-4" aria-hidden="true" />}
                  label="Executor"
                  value={
                    executorModel
                      ? (availableModels.find((m) => m.id === executorModel)
                          ?.name ?? "Unknown")
                      : "Auto"
                  }
                />
                <SubMenuContent data-testid="submenu-content-executor">
                  <DropdownMenu.RadioGroup
                    value={executorModel ?? "auto"}
                    onValueChange={(value) =>
                      onExecutorModelChange?.(value === "auto" ? null : value)
                    }
                  >
                    <DropdownMenu.RadioItem
                      value="auto"
                      className={cn(
                        "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                        "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                        "cursor-pointer rounded-md",
                        "transition-colors duration-150",
                        !executorModel
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12",
                      )}
                    >
                      <span className="font-medium">
                        Auto (based on complexity)
                      </span>
                      <DropdownMenu.ItemIndicator>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </DropdownMenu.ItemIndicator>
                    </DropdownMenu.RadioItem>
                    {availableModels.map((model) => (
                      <DropdownMenu.RadioItem
                        key={model.id}
                        value={model.id}
                        className={cn(
                          "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                          "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                          "cursor-pointer rounded-md",
                          "transition-colors duration-150",
                          executorModel === model.id
                            ? "text-primary-11 bg-primary-3"
                            : "text-neutral-12",
                        )}
                      >
                        <div className="flex flex-col items-start gap-0.5">
                          <span className="font-medium">{model.name}</span>
                          <span className="text-xs text-neutral-10">
                            {formatProviderDisplay(model)}
                          </span>
                        </div>
                        <DropdownMenu.ItemIndicator>
                          <Check className="h-4 w-4" aria-hidden="true" />
                        </DropdownMenu.ItemIndicator>
                      </DropdownMenu.RadioItem>
                    ))}
                  </DropdownMenu.RadioGroup>
                </SubMenuContent>
              </DropdownMenu.Sub>
            )}

            {/* Critic Model Submenu (Critique Loop) */}
            {critiqueLoopEnabled && availableModels.length > 0 && (
              <DropdownMenu.Sub>
                <SubMenuTrigger
                  data-testid="submenu-trigger-critic"
                  icon={
                    <MessageSquare className="h-4 w-4" aria-hidden="true" />
                  }
                  label="Critic"
                  value={
                    criticModel
                      ? (availableModels.find((m) => m.id === criticModel)
                          ?.name ?? "Unknown")
                      : "Auto"
                  }
                />
                <SubMenuContent data-testid="submenu-content-critic">
                  <DropdownMenu.RadioGroup
                    value={criticModel ?? "auto"}
                    onValueChange={(value) =>
                      onCriticModelChange?.(value === "auto" ? null : value)
                    }
                  >
                    <DropdownMenu.RadioItem
                      value="auto"
                      className={cn(
                        "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                        "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                        "cursor-pointer rounded-md",
                        "transition-colors duration-150",
                        !criticModel
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12",
                      )}
                    >
                      <span className="font-medium">
                        Auto (cross-vendor diversity)
                      </span>
                      <DropdownMenu.ItemIndicator>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </DropdownMenu.ItemIndicator>
                    </DropdownMenu.RadioItem>
                    {availableModels.map((model) => (
                      <DropdownMenu.RadioItem
                        key={model.id}
                        value={model.id}
                        className={cn(
                          "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                          "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                          "cursor-pointer rounded-md",
                          "transition-colors duration-150",
                          criticModel === model.id
                            ? "text-primary-11 bg-primary-3"
                            : "text-neutral-12",
                        )}
                      >
                        <div className="flex flex-col items-start gap-0.5">
                          <span className="font-medium">{model.name}</span>
                          <span className="text-xs text-neutral-10">
                            {formatProviderDisplay(model)}
                          </span>
                        </div>
                        <DropdownMenu.ItemIndicator>
                          <Check className="h-4 w-4" aria-hidden="true" />
                        </DropdownMenu.ItemIndicator>
                      </DropdownMenu.RadioItem>
                    ))}
                  </DropdownMenu.RadioGroup>
                </SubMenuContent>
              </DropdownMenu.Sub>
            )}

            <DropdownMenu.Separator className="h-px bg-neutral-6 my-1" />

            {/* Thinking Level Submenu */}
            <DropdownMenu.Sub>
              <SubMenuTrigger
                data-testid="submenu-trigger-thinking"
                icon={<Brain className="h-4 w-4" aria-hidden="true" />}
                label="Thinking"
                value={getThinkingLevelLabel(thinkingLevel)}
              />
              <SubMenuContent data-testid="submenu-content-thinking">
                <DropdownMenu.RadioGroup
                  value={thinkingLevel}
                  onValueChange={(value) =>
                    onThinkingLevelChange?.(value as ReasoningEffortLevel)
                  }
                >
                  {THINKING_LEVELS.map((level) => (
                    <DropdownMenu.RadioItem
                      key={level.value}
                      value={level.value}
                      className={cn(
                        "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                        "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                        "cursor-pointer rounded-md",
                        "transition-colors duration-150",
                        thinkingLevel === level.value
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12",
                      )}
                    >
                      <span>{level.label}</span>
                      <DropdownMenu.ItemIndicator>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </DropdownMenu.ItemIndicator>
                    </DropdownMenu.RadioItem>
                  ))}
                </DropdownMenu.RadioGroup>
              </SubMenuContent>
            </DropdownMenu.Sub>

            {/* Tools Submenu (with nested Tool Provider) */}
            <DropdownMenu.Sub>
              <SubMenuTrigger
                data-testid="submenu-trigger-tools"
                icon={<Wrench className="h-4 w-4" aria-hidden="true" />}
                label="Tools"
                value={getToolModeLabel(toolMode)}
              />
              <SubMenuContent data-testid="submenu-content-tools">
                {/* Tool Mode Selection */}
                <DropdownMenu.RadioGroup
                  value={toolMode}
                  onValueChange={(value) =>
                    onToolModeChange?.(value as ToolSelectionMode)
                  }
                >
                  {TOOL_MODES.map((mode) => (
                    <DropdownMenu.RadioItem
                      key={mode.value}
                      value={mode.value}
                      className={cn(
                        "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                        "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                        "cursor-pointer rounded-md",
                        "transition-colors duration-150",
                        toolMode === mode.value
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12",
                      )}
                    >
                      <span>{mode.label}</span>
                      <DropdownMenu.ItemIndicator>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </DropdownMenu.ItemIndicator>
                    </DropdownMenu.RadioItem>
                  ))}
                </DropdownMenu.RadioGroup>

                <DropdownMenu.Separator className="h-px bg-neutral-6 my-1" />

                {/* Selected Tools Sub-submenu (only in manual mode) */}
                {toolMode === "manual" && (
                  <DropdownMenu.Sub>
                    <SubMenuTrigger
                      data-testid="submenu-trigger-selected-tools"
                      icon={<Wrench className="h-4 w-4" aria-hidden="true" />}
                      label="Selected Tools"
                      value={
                        selectedTools.length === 0
                          ? "None"
                          : `${selectedTools.length} selected`
                      }
                    />
                    <SubMenuContent data-testid="submenu-content-selected-tools">
                      {availableTools.length === 0 ? (
                        <div className="px-3 py-2 text-sm text-neutral-10">
                          No tools available
                        </div>
                      ) : (
                        availableTools.map((tool) => {
                          const isSelected = selectedTools.includes(
                            tool.toolId,
                          );
                          return (
                            <DropdownMenu.CheckboxItem
                              key={tool.toolId}
                              checked={isSelected}
                              onCheckedChange={() => {
                                if (isSelected) {
                                  // Remove tool
                                  onToolsChange?.(
                                    selectedTools.filter(
                                      (id) => id !== tool.toolId,
                                    ),
                                  );
                                } else {
                                  // Add tool
                                  onToolsChange?.([
                                    ...selectedTools,
                                    tool.toolId,
                                  ]);
                                }
                              }}
                              className={cn(
                                "flex items-center justify-between w-full px-3 py-2.5 text-sm",
                                "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                                "cursor-pointer rounded-md",
                                "transition-colors duration-150",
                                isSelected
                                  ? "text-primary-11 bg-primary-3"
                                  : "text-neutral-12",
                              )}
                            >
                              <div className="flex flex-col items-start gap-0.5">
                                <span className="font-medium">
                                  {tool.displayName}
                                </span>
                                {tool.description && (
                                  <span className="text-xs text-neutral-10">
                                    {tool.description}
                                  </span>
                                )}
                              </div>
                              <DropdownMenu.ItemIndicator>
                                <Check className="h-4 w-4" aria-hidden="true" />
                              </DropdownMenu.ItemIndicator>
                            </DropdownMenu.CheckboxItem>
                          );
                        })
                      )}
                    </SubMenuContent>
                  </DropdownMenu.Sub>
                )}

                {/* Nested Tool Provider Sub-submenu */}
                <DropdownMenu.Sub>
                  <SubMenuTrigger
                    data-testid="submenu-trigger-provider"
                    icon={<Zap className="h-4 w-4" aria-hidden="true" />}
                    label="Provider"
                    value={getToolPreferenceLabel(toolPreference)}
                  />
                  <SubMenuContent data-testid="submenu-content-provider">
                    <DropdownMenu.RadioGroup
                      value={toolPreference}
                      onValueChange={(value) =>
                        onToolPreferenceChange?.(value as ToolPreference)
                      }
                    >
                      {TOOL_PREFERENCE_MODES.map((pref) => (
                        <DropdownMenu.RadioItem
                          key={pref.value}
                          value={pref.value}
                          className={cn(
                            "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                            "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                            "cursor-pointer rounded-md",
                            "transition-colors duration-150",
                            toolPreference === pref.value
                              ? "text-primary-11 bg-primary-3"
                              : "text-neutral-12",
                          )}
                        >
                          <div className="flex flex-col items-start gap-0.5">
                            <span className="font-medium">{pref.label}</span>
                            <span className="text-xs text-neutral-10">
                              {pref.description}
                            </span>
                          </div>
                          <DropdownMenu.ItemIndicator>
                            <Check className="h-4 w-4" aria-hidden="true" />
                          </DropdownMenu.ItemIndicator>
                        </DropdownMenu.RadioItem>
                      ))}
                    </DropdownMenu.RadioGroup>
                  </SubMenuContent>
                </DropdownMenu.Sub>
              </SubMenuContent>
            </DropdownMenu.Sub>

            {/* KB Focus Submenu */}
            <DropdownMenu.Sub>
              <SubMenuTrigger
                data-testid="submenu-trigger-kb"
                icon={<Database className="h-4 w-4" aria-hidden="true" />}
                label="KB"
                value={getKBFocusModeLabel(kbFocusMode)}
              />
              <SubMenuContent data-testid="submenu-content-kb">
                <DropdownMenu.RadioGroup
                  value={kbFocusMode}
                  onValueChange={(value) =>
                    onKBFocusChange?.(value as KBFocusMode)
                  }
                >
                  {KB_FOCUS_MODES.map((mode) => (
                    <DropdownMenu.RadioItem
                      key={mode.value}
                      value={mode.value}
                      className={cn(
                        "flex items-center justify-between w-full px-3 py-2.5 text-sm", // py-2.5 for improved touch targets
                        "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                        "cursor-pointer rounded-md",
                        "transition-colors duration-150",
                        kbFocusMode === mode.value
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12",
                      )}
                    >
                      <span>{mode.label}</span>
                      <DropdownMenu.ItemIndicator>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </DropdownMenu.ItemIndicator>
                    </DropdownMenu.RadioItem>
                  ))}
                </DropdownMenu.RadioGroup>
              </SubMenuContent>
            </DropdownMenu.Sub>

            <DropdownMenu.Separator className="h-px bg-neutral-6 my-1" />

            {/* Style Presets Submenu */}
            <DropdownMenu.Sub>
              <SubMenuTrigger
                data-testid="submenu-trigger-style"
                icon={<Palette className="h-4 w-4" aria-hidden="true" />}
                label="Style"
                value={getStylePresetLabel(effectiveStylePreset)}
              />
              <SubMenuContent data-testid="submenu-content-style">
                <div data-testid="style-presets-container">
                  <DropdownMenu.RadioGroup
                    value={effectiveStylePreset}
                    onValueChange={(value) => {
                      const presetName = value as PresetName;
                      const config = PRESET_CONFIGS[presetName];
                      onStylePresetChange?.({
                        name: presetName,
                        ...config,
                      });
                    }}
                  >
                    {STYLE_PRESET_OPTIONS.map((preset) => {
                      const Icon = preset.icon;
                      return (
                        <DropdownMenu.RadioItem
                          key={preset.value}
                          value={preset.value}
                          data-testid={`preset-${preset.value}`}
                          className={cn(
                            "flex items-center justify-between w-full px-3 py-2.5 text-sm",
                            "hover:bg-neutral-4 focus:bg-neutral-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7",
                            "cursor-pointer rounded-md",
                            "transition-colors duration-150",
                            effectiveStylePreset === preset.value
                              ? "text-primary-11 bg-primary-3"
                              : "text-neutral-12",
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4" aria-hidden="true" />
                            <div className="flex flex-col items-start gap-0.5">
                              <span className="font-medium">
                                {preset.label}
                              </span>
                              <span className="text-xs text-neutral-10">
                                {preset.description}
                              </span>
                            </div>
                          </div>
                          <DropdownMenu.ItemIndicator>
                            <Check className="h-4 w-4" aria-hidden="true" />
                          </DropdownMenu.ItemIndicator>
                        </DropdownMenu.RadioItem>
                      );
                    })}
                  </DropdownMenu.RadioGroup>
                </div>
              </SubMenuContent>
            </DropdownMenu.Sub>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
}

PreferencesMenu.displayName = "PreferencesMenu";
