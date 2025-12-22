/**
 * WorkspacePresets - Phase 2
 *
 * Per-persona workspace layout presets with preview
 * and customization support.
 */
import { useState, useCallback, useRef } from "react";
import {
  Layout,
  MessageSquare,
  Code,
  Minimize,
  Save,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface WorkspaceLayout {
  sessionNav: number;
  conversation: number;
  canvas: number;
}

export interface WorkspacePreset {
  id: string;
  name: string;
  description: string;
  layout: WorkspaceLayout;
  icon: string;
}

export interface WorkspacePresetsProps {
  presets: WorkspacePreset[];
  currentPreset: string;
  onApply: (preset: WorkspacePreset) => void;
  variant?: "grid" | "list";
  showPreview?: boolean;
  allowCustom?: boolean;
  onSaveCustom?: () => void;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

// Icon mapping - using LucideIcon type for proper compatibility
const iconMap: Record<string, LucideIcon> = {
  layout: Layout,
  "message-square": MessageSquare,
  code: Code,
  minimize: Minimize,
};

function getIcon(iconName: string) {
  return iconMap[iconName] || Layout;
}

// =============================================================================
// Layout Preview Component
// =============================================================================

function LayoutPreview({ layout }: { layout: WorkspaceLayout }) {
  return (
    <div
      data-testid="layout-preview"
      className="flex h-20 rounded border border-gray-200 dark:border-gray-700 overflow-hidden text-xs"
    >
      {layout.sessionNav > 0 && (
        <div
          className="bg-gray-200 dark:bg-gray-700 flex items-center justify-center border-r border-gray-300 dark:border-gray-600"
          style={{ width: `${layout.sessionNav}%` }}
        >
          {layout.sessionNav}%
        </div>
      )}
      <div
        className="bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center border-r border-gray-300 dark:border-gray-600"
        style={{ width: `${layout.conversation}%` }}
      >
        {layout.conversation}%
      </div>
      <div
        className="bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center"
        style={{ width: `${layout.canvas}%` }}
      >
        {layout.canvas}%
      </div>
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function WorkspacePresets({
  presets,
  currentPreset,
  onApply,
  variant = "grid",
  showPreview = false,
  allowCustom = false,
  onSaveCustom,
  className,
}: WorkspacePresetsProps) {
  const [hoveredPreset, setHoveredPreset] = useState<string | null>(null);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);

  const handleApply = useCallback(
    (preset: WorkspacePreset) => {
      if (preset.id !== currentPreset) {
        onApply(preset);
      }
    },
    [currentPreset, onApply],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = Math.min(focusedIndex + 1, presets.length - 1);
        setFocusedIndex(nextIndex);
        itemRefs.current[nextIndex]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = Math.max(focusedIndex - 1, 0);
        setFocusedIndex(prevIndex);
        itemRefs.current[prevIndex]?.focus();
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        e.preventDefault();
        const selectedPreset = presets[focusedIndex];
        if (selectedPreset) handleApply(selectedPreset);
      }
    },
    [focusedIndex, presets, handleApply],
  );

  const handleItemKeyDown = useCallback(
    (e: React.KeyboardEvent, preset: WorkspacePreset, index: number) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleApply(preset);
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = Math.min(index + 1, presets.length - 1);
        setFocusedIndex(nextIndex);
        itemRefs.current[nextIndex]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = Math.max(index - 1, 0);
        setFocusedIndex(prevIndex);
        itemRefs.current[prevIndex]?.focus();
      }
    },
    [handleApply, presets.length],
  );

  return (
    <div
      data-testid="workspace-presets"
      ref={containerRef}
      role="radiogroup"
      aria-label="Workspace layout presets"
      onKeyDown={handleKeyDown}
      className={cn(
        variant === "grid"
          ? "grid grid-cols-2 gap-3"
          : "list flex flex-col gap-2",
        className,
      )}
    >
      {presets.map((preset, index) => {
        const isSelected = preset.id === currentPreset;
        const isHovered = hoveredPreset === preset.id;
        const PresetIcon = getIcon(preset.icon);

        return (
          <div
            key={preset.id}
            data-testid={`preset-${preset.id}`}
            ref={(el) => {
              itemRefs.current[index] = el;
            }}
            role="radio"
            aria-checked={isSelected}
            tabIndex={index === 0 || isSelected ? 0 : -1}
            onClick={() => handleApply(preset)}
            onKeyDown={(e) => handleItemKeyDown(e, preset, index)}
            onMouseEnter={() => setHoveredPreset(preset.id)}
            onMouseLeave={() => setHoveredPreset(null)}
            onFocus={() => setFocusedIndex(index)}
            className={cn(
              "flex flex-col p-3 rounded-lg cursor-pointer transition-all",
              "border-2",
              isSelected
                ? "selected border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600",
              "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
            )}
          >
            <div className="flex items-center gap-2 mb-1">
              <PresetIcon
                size={16}
                className={cn(
                  isSelected
                    ? "text-primary-500"
                    : "text-gray-400 dark:text-gray-500",
                )}
              />
              <span
                className={cn(
                  "text-sm font-medium",
                  isSelected
                    ? "text-primary-700 dark:text-primary-300"
                    : "text-gray-900 dark:text-gray-100",
                )}
              >
                {preset.name}
              </span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {preset.description}
            </p>

            {/* Layout Preview on Hover */}
            {showPreview && isHovered && (
              <LayoutPreview layout={preset.layout} />
            )}
          </div>
        );
      })}

      {/* Save Custom Preset Button */}
      {allowCustom && (
        <button
          data-testid="save-custom-preset"
          type="button"
          onClick={onSaveCustom}
          className={cn(
            "flex items-center justify-center gap-2 p-3 rounded-lg",
            "border-2 border-dashed border-gray-300 dark:border-gray-600",
            "text-gray-500 dark:text-gray-400",
            "hover:border-primary-400 hover:text-primary-500",
            "transition-colors",
          )}
        >
          <Save size={16} />
          <span className="text-sm">Save Current Layout</span>
        </button>
      )}
    </div>
  );
}
