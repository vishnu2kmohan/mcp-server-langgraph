/**
 * StylePresets Component
 *
 * Quick-select buttons for response style presets that adjust
 * temperature and max tokens for different use cases:
 * - Creative: Higher temperature for imaginative responses
 * - Balanced: Default settings for general use
 * - Precise: Lower temperature for focused, accurate responses
 */

import { Sparkles, Scale, Target } from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type PresetName = "creative" | "balanced" | "precise";

export interface StylePreset {
  name: PresetName;
  temperature: number;
  maxTokens: number;
}

export interface StylePresetsProps {
  /** Callback when a preset is selected */
  onSelect: (preset: StylePreset) => void;
  /** Currently active preset name */
  activePreset?: PresetName;
  /** Whether the presets are disabled */
  disabled?: boolean;
  /** Compact mode for smaller display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const PRESETS: Record<
  PresetName,
  StylePreset & { label: string; description: string; icon: typeof Sparkles }
> = {
  creative: {
    name: "creative",
    label: "Creative",
    description:
      "Imaginative and varied responses (Temperature: 1.2, Max Tokens: 4096)",
    temperature: 1.2,
    maxTokens: 4096,
    icon: Sparkles,
  },
  balanced: {
    name: "balanced",
    label: "Balanced",
    description:
      "Balanced and coherent responses (Temperature: 0.7, Max Tokens: 2048)",
    temperature: 0.7,
    maxTokens: 2048,
    icon: Scale,
  },
  precise: {
    name: "precise",
    label: "Precise",
    description:
      "Focused and accurate responses (Temperature: 0.3, Max Tokens: 1024)",
    temperature: 0.3,
    maxTokens: 1024,
    icon: Target,
  },
};

// =============================================================================
// Component
// =============================================================================

export function StylePresets({
  onSelect,
  activePreset,
  disabled = false,
  compact = false,
  className = "",
}: StylePresetsProps) {
  const handleSelect = (presetName: PresetName) => {
    const preset = PRESETS[presetName];
    onSelect({
      name: preset.name,
      temperature: preset.temperature,
      maxTokens: preset.maxTokens,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent, presetName: PresetName) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleSelect(presetName);
    }
  };

  return (
    <div
      data-testid="style-presets-container"
      className={`flex items-center ${compact ? "gap-1" : "gap-2"} ${className}`}
    >
      {(Object.keys(PRESETS) as PresetName[]).map((presetName) => {
        const preset = PRESETS[presetName];
        const Icon = preset.icon;
        const isActive = activePreset === presetName;

        return (
          <button
            key={presetName}
            data-testid={`preset-${presetName}`}
            type="button"
            onClick={() => handleSelect(presetName)}
            onKeyDown={(e) => handleKeyDown(e, presetName)}
            disabled={disabled}
            title={preset.description}
            aria-label={`${preset.label} style: ${preset.description}`}
            aria-pressed={isActive}
            className={`
              inline-flex items-center gap-1.5
              ${compact ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm"}
              rounded-lg font-medium
              transition-colors
              focus:outline-none focus:ring-2 focus:ring-blue-500/50
              ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
              }
              ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            <Icon size={compact ? 12 : 14} />
            <span>{preset.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export default StylePresets;
