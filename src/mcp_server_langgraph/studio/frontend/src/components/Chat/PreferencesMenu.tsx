/**
 * PreferencesMenu Component
 *
 * Consolidated preferences dropdown for chat input settings.
 * Provides access to:
 * - Model selection (with thinking level)
 * - Tool selection mode
 * - Knowledge Base focus mode
 *
 * Design System Compliance:
 * - Uses CVA for variant styling
 * - Uses Radix 1-12 color scale
 * - Focus rings: focus-visible:ring-2 focus-visible:ring-primary-7
 * - Touch targets: 32px minimum (WCAG 2.5.8)
 *
 * @see Chat Input UX Plan for architecture details
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Settings2, ChevronDown, Check, Brain, Wrench, Database, Loader2, Cpu, Sparkles, MessageSquare, Zap } from "lucide-react";
import { cn } from "../../utils/cn";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { KBFocusMode } from "./KnowledgeBaseFocus";
import type { ToolSelectionMode, ToolPreference } from "@/types/tools";
import type { ModelOption } from "./ChatInput";

import { Button } from "@/components/UI";

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
  /** Currently selected tools */
  selectedTools?: string[];
  /** Callback when tools change */
  onToolsChange?: (tools: string[]) => void;
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

const KB_FOCUS_MODES: { value: KBFocusMode; label: string }[] = [
  { value: "all", label: "All Sources" },
  { value: "kb_only", label: "KB Only" },
  { value: "web_only", label: "Web Only" },
  { value: "none", label: "None" },
];

// v7: Tool preference modes for native vs builtin execution
const TOOL_PREFERENCE_MODES: { value: ToolPreference; label: string; description: string }[] = [
  { value: "auto", label: "Auto", description: "Prefer native when available" },
  { value: "native", label: "Native Only", description: "Use LLM provider tools" },
  { value: "builtin", label: "Built-in Only", description: "Use server-side tools" },
  { value: "mcp", label: "MCP Only", description: "Use MCP server tools" },
];

// =============================================================================
// Helpers
// =============================================================================

/**
 * Format model provider display with vendor info for transparency.
 * Shows "google (Vertex AI)" when using Vertex AI instead of native API.
 */
function formatProviderDisplay(model: ModelOption): string {
  const { provider, vendor } = model;
  if (!vendor) return provider;

  // Show vendor distinction when it differs from simplified provider
  if (vendor === "vertex_ai" && provider === "google") {
    return "Google (Vertex AI)";
  }
  if (vendor === "vertex_ai_anthropic" && provider === "anthropic") {
    return "Anthropic (Vertex AI)";
  }
  if (vendor === "azure" && provider === "openai") {
    return "OpenAI (Azure)";
  }

  // Capitalize provider for display
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

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
  selectedTools: _selectedTools,
  onToolsChange: _onToolsChange,
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
}: PreferencesMenuProps) {
  // Get current model info (reserved for future tooltip/display enhancements)
  const _currentModel = availableModels.find((m) => m.id === selectedModel);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
    return undefined;
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    },
    []
  );

  const handleToggle = useCallback(() => {
    if (!disabled && !isLoading) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled, isLoading]);

  const handleThinkingLevelChange = useCallback(
    (level: ReasoningEffortLevel) => {
      onThinkingLevelChange?.(level);
    },
    [onThinkingLevelChange]
  );

  const handleToolModeChange = useCallback(
    (mode: ToolSelectionMode) => {
      onToolModeChange?.(mode);
    },
    [onToolModeChange]
  );

  const handleKBFocusChange = useCallback(
    (mode: KBFocusMode) => {
      onKBFocusChange?.(mode);
    },
    [onKBFocusChange]
  );

  // v7: Handle tool preference change
  const handleToolPreferenceChange = useCallback(
    (preference: ToolPreference) => {
      onToolPreferenceChange?.(preference);
    },
    [onToolPreferenceChange]
  );

  const handleModelChange = useCallback(
    (modelId: string) => {
      onModelChange?.(modelId);
    },
    [onModelChange]
  );

  const handleExecutorModelChange = useCallback(
    (modelId: string | null) => {
      onExecutorModelChange?.(modelId);
    },
    [onExecutorModelChange]
  );

  const handleCriticModelChange = useCallback(
    (modelId: string | null) => {
      onCriticModelChange?.(modelId);
    },
    [onCriticModelChange]
  );

  return (
    <div
      ref={containerRef}
      data-testid="preferences-menu"
      className={cn("relative", className)}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      { }
      <Button
        variant="ghost"
        ref={buttonRef}
        type="button"
        data-testid="preferences-menu-trigger"
        onClick={handleToggle}
        disabled={disabled || isLoading}
        aria-label="Open preferences menu"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md text-sm font-medium",
          "min-h-8 transition-colors duration-150",
          "bg-neutral-3 text-neutral-11 hover:bg-neutral-4",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          compact ? "px-2" : "px-3"
        )}>
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
          className={cn(
            "h-3 w-3 transition-transform duration-150",
            isOpen && "rotate-180"
          )}
          aria-hidden="true"
        />
      </Button>
      {/* Dropdown Menu */}
      {isOpen && (
        <div
          data-testid="preferences-dropdown"
          role="menu"
          aria-label="Preferences menu"
          className={cn(
            "absolute right-0 bottom-full mb-1 z-50",
            "min-w-[240px] max-h-[70vh] overflow-y-auto rounded-lg border border-neutral-6",
            "bg-neutral-2 shadow-lg",
            "py-2"
          )}
        >
          {/* Model Selection Section */}
          {availableModels.length > 0 && (
            <>
              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
                  <Cpu className="h-3 w-3" aria-hidden="true" />
                  Model
                </div>
                {isModelsLoading ? (
                  <div className="flex items-center justify-center py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-neutral-9" aria-label="Loading models" />
                  </div>
                ) : (
                  <div className="space-y-1 max-h-[200px] overflow-y-auto" role="listbox" aria-label="Model selection">
                    {availableModels.map((model) => (
                       
                      (<Button
                      variant="ghost"
                      key={model.id}
                      type="button"
                      role="option"
                      aria-selected={selectedModel === model.id}
                      onClick={() => handleModelChange(model.id)}
                      className={cn(
                        "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                        "hover:bg-neutral-4 transition-colors",
                        selectedModel === model.id
                          ? "text-primary-11 bg-primary-3"
                          : "text-neutral-12"
                      )}>
                        <div className="flex flex-col items-start gap-0.5">
                          <span className="font-medium">{model.name}</span>
                          <span className="text-xs text-neutral-10">{formatProviderDisplay(model)}</span>
                        </div>
                        {selectedModel === model.id && (
                          <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                        )}
                      </Button>)
                    ))}
                  </div>
                )}
              </div>
              <div className="border-t border-neutral-6 my-2" />
            </>
          )}

          {/* Executor/Critic Model Selection (Critique Loop) */}
          {critiqueLoopEnabled && availableModels.length > 0 && (
            <>
              {/* Executor Model Section */}
              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
                  <Sparkles className="h-3 w-3" aria-hidden="true" />
                  Executor Model
                </div>
                <p className="text-xs text-neutral-10 mb-2">
                  Generates initial response and refinements
                </p>
                <div className="space-y-1 max-h-[150px] overflow-y-auto" role="listbox" aria-label="Executor model selection">
                  {/* Auto option */}
                  { }
                  <Button
                    variant="ghost"
                    type="button"
                    role="option"
                    aria-selected={executorModel === null || executorModel === undefined}
                    onClick={() => handleExecutorModelChange(null)}
                    className={cn(
                      "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                      "hover:bg-neutral-4 transition-colors",
                      (executorModel === null || executorModel === undefined)
                        ? "text-primary-11 bg-primary-3"
                        : "text-neutral-12"
                    )}>
                    <span className="font-medium">Auto (based on complexity)</span>
                    {(executorModel === null || executorModel === undefined) && (
                      <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                    )}
                  </Button>
                  {availableModels.map((model) => (
                     
                    (<Button
                    variant="ghost"
                    key={model.id}
                    type="button"
                    role="option"
                    aria-selected={executorModel === model.id}
                    onClick={() => handleExecutorModelChange(model.id)}
                    className={cn(
                      "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                      "hover:bg-neutral-4 transition-colors",
                      executorModel === model.id
                        ? "text-primary-11 bg-primary-3"
                        : "text-neutral-12"
                    )}>
                      <div className="flex flex-col items-start gap-0.5">
                        <span className="font-medium">{model.name}</span>
                        <span className="text-xs text-neutral-10">{formatProviderDisplay(model)}</span>
                      </div>
                      {executorModel === model.id && (
                        <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                      )}
                    </Button>)
                  ))}
                </div>
              </div>

              <div className="border-t border-neutral-6 my-2" />

              {/* Critic Model Section */}
              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
                  <MessageSquare className="h-3 w-3" aria-hidden="true" />
                  Critic Model
                </div>
                <p className="text-xs text-neutral-10 mb-2">
                  Reviews and provides feedback for refinement
                </p>
                <div className="space-y-1 max-h-[150px] overflow-y-auto" role="listbox" aria-label="Critic model selection">
                  {/* Auto option */}
                  { }
                  <Button
                    variant="ghost"
                    type="button"
                    role="option"
                    aria-selected={criticModel === null || criticModel === undefined}
                    onClick={() => handleCriticModelChange(null)}
                    className={cn(
                      "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                      "hover:bg-neutral-4 transition-colors",
                      (criticModel === null || criticModel === undefined)
                        ? "text-primary-11 bg-primary-3"
                        : "text-neutral-12"
                    )}>
                    <span className="font-medium">Auto (cross-vendor diversity)</span>
                    {(criticModel === null || criticModel === undefined) && (
                      <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                    )}
                  </Button>
                  {availableModels.map((model) => (
                     
                    (<Button
                    variant="ghost"
                    key={model.id}
                    type="button"
                    role="option"
                    aria-selected={criticModel === model.id}
                    onClick={() => handleCriticModelChange(model.id)}
                    className={cn(
                      "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                      "hover:bg-neutral-4 transition-colors",
                      criticModel === model.id
                        ? "text-primary-11 bg-primary-3"
                        : "text-neutral-12"
                    )}>
                      <div className="flex flex-col items-start gap-0.5">
                        <span className="font-medium">{model.name}</span>
                        <span className="text-xs text-neutral-10">{formatProviderDisplay(model)}</span>
                      </div>
                      {criticModel === model.id && (
                        <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                      )}
                    </Button>)
                  ))}
                </div>
              </div>

              <div className="border-t border-neutral-6 my-2" />
            </>
          )}

          {/* Thinking Level Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Brain className="h-3 w-3" aria-hidden="true" />
              Thinking Level
            </div>
            <div className="space-y-1" role="listbox" aria-label="Thinking level">
              {THINKING_LEVELS.map((level) => (
                 
                (<Button
                variant="ghost"
                key={level.value}
                type="button"
                role="option"
                aria-selected={thinkingLevel === level.value}
                onClick={() => handleThinkingLevelChange(level.value)}
                className={cn(
                  "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                  "hover:bg-neutral-4 transition-colors",
                  thinkingLevel === level.value
                    ? "text-primary-11 bg-primary-3"
                    : "text-neutral-12"
                )}>
                  <span>{level.label}</span>
                  {thinkingLevel === level.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>)
              ))}
            </div>
          </div>

          <div className="border-t border-neutral-6 my-2" />

          {/* Tools Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Wrench className="h-3 w-3" aria-hidden="true" />
              Tools
            </div>
            <div className="space-y-1" role="listbox" aria-label="Tool mode">
              {TOOL_MODES.map((mode) => (
                 
                (<Button
                variant="ghost"
                key={mode.value}
                type="button"
                role="option"
                aria-selected={toolMode === mode.value}
                onClick={() => handleToolModeChange(mode.value)}
                className={cn(
                  "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                  "hover:bg-neutral-4 transition-colors",
                  toolMode === mode.value
                    ? "text-primary-11 bg-primary-3"
                    : "text-neutral-12"
                )}>
                  <span>{mode.label}</span>
                  {toolMode === mode.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>)
              ))}
            </div>
          </div>

          <div className="border-t border-neutral-6 my-2" />

          {/* v7: Tool Provider Preference Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Zap className="h-3 w-3" aria-hidden="true" />
              Tool Provider
            </div>
            <p className="text-xs text-neutral-10 mb-2">
              Choose between native LLM tools or server-side execution
            </p>
            <div className="space-y-1" role="listbox" aria-label="Tool provider preference">
              {TOOL_PREFERENCE_MODES.map((pref) => (
                 
                (<Button
                variant="ghost"
                key={pref.value}
                type="button"
                role="option"
                aria-selected={toolPreference === pref.value}
                onClick={() => handleToolPreferenceChange(pref.value)}
                className={cn(
                  "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                  "hover:bg-neutral-4 transition-colors",
                  toolPreference === pref.value
                    ? "text-primary-11 bg-primary-3"
                    : "text-neutral-12"
                )}>
                  <div className="flex flex-col items-start gap-0.5">
                    <span className="font-medium">{pref.label}</span>
                    <span className="text-xs text-neutral-10">{pref.description}</span>
                  </div>
                  {toolPreference === pref.value && (
                    <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  )}
                </Button>)
              ))}
            </div>
          </div>

          <div className="border-t border-neutral-6 my-2" />

          {/* KB Focus Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Database className="h-3 w-3" aria-hidden="true" />
              Knowledge Base
            </div>
            <div className="space-y-1" role="listbox" aria-label="KB focus mode">
              {KB_FOCUS_MODES.map((mode) => (
                 
                (<Button
                variant="ghost"
                key={mode.value}
                type="button"
                role="option"
                aria-selected={kbFocusMode === mode.value}
                onClick={() => handleKBFocusChange(mode.value)}
                className={cn(
                  "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                  "hover:bg-neutral-4 transition-colors",
                  kbFocusMode === mode.value
                    ? "text-primary-11 bg-primary-3"
                    : "text-neutral-12"
                )}>
                  <span>{mode.label}</span>
                  {kbFocusMode === mode.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>)
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

PreferencesMenu.displayName = "PreferencesMenu";
