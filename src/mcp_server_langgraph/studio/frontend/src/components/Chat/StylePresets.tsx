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

import { Button } from "@/components/UI";

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

/** Exported preset configs (single source of truth for temperature/maxTokens) */
// eslint-disable-next-line react-refresh/only-export-components
export const PRESET_CONFIGS: Record<
  PresetName,
  { temperature: number; maxTokens: number }
> = {
  creative: { temperature: 1.0, maxTokens: 4096 },
  balanced: { temperature: 0.7, maxTokens: 2048 },
  precise: { temperature: 0.3, maxTokens: 1024 },
};

const PRESETS: Record<
  PresetName,
  StylePreset & { label: string; description: string; icon: typeof Sparkles }
> = {
  creative: {
    name: "creative",
    label: "Creative",
    description:
      "Imaginative and varied responses (Temperature: 1.0, Max Tokens: 4096)",
    ...PRESET_CONFIGS.creative,
    icon: Sparkles,
  },
  balanced: {
    name: "balanced",
    label: "Balanced",
    description:
      "Balanced and coherent responses (Temperature: 0.7, Max Tokens: 2048)",
    ...PRESET_CONFIGS.balanced,
    icon: Scale,
  },
  precise: {
    name: "precise",
    label: "Precise",
    description:
      "Focused and accurate responses (Temperature: 0.3, Max Tokens: 1024)",
    ...PRESET_CONFIGS.precise,
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

  // Note: No separate onKeyDown handler needed — HTML <button> natively
  // fires onClick for Enter/Space, so a manual onKeyDown would double-fire.

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
          <Button
            variant={isActive ? "primary" : "secondary"}
            size={compact ? "sm" : "md"}
            className="rounded-lg"
            key={presetName}
            data-testid={`preset-${presetName}`}
            type="button"
            onClick={() => handleSelect(presetName)}
            disabled={disabled}
            title={preset.description}
            aria-label={`${preset.label} style: ${preset.description}`}
            aria-pressed={isActive}
          >
            <Icon size={compact ? 12 : 14} />
            <span>{preset.label}</span>
          </Button>
        );
      })}
    </div>
  );
}

export default StylePresets;
