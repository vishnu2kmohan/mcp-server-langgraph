/**
 * AccessibilitySettings Component
 *
 * Panel for managing accessibility preferences.
 * Features:
 * - Screen reader mode toggle
 * - Reduced motion preference
 * - High contrast mode
 * - Font size adjustment
 * - Enhanced focus indicators toggle
 * - Reset to defaults
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on GEMINI.md, AGENTS.md, CLAUDE.md patterns.
 */

import { Eye, Volume2, Palette, Type, Focus, RotateCcw } from "lucide-react";
import { useAccessibility, FontSize } from "../../hooks/useAccessibility";

import { Button, Toggle } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface AccessibilitySettingsProps {
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Setting Toggle Component (with icon wrapper)
// ==============================================================================

interface SettingToggleProps {
  id: string;
  testId: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description: string;
  icon: React.ReactNode;
}

function SettingToggle({
  id,
  testId,
  checked,
  onChange,
  label,
  description,
  icon,
}: SettingToggleProps) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-neutral-1">
      <div className="text-neutral-10 mt-0.5">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <Toggle
          id={id}
          data-testid={testId}
          checked={checked}
          onChange={onChange}
          label={label}
          description={description}
        />
      </div>
    </div>
  );
}

// ==============================================================================
// Font Size Selector Component
// ==============================================================================

interface FontSizeSelectorProps {
  value: FontSize;
  onChange: (size: FontSize) => void;
}

function FontSizeSelector({ value, onChange }: FontSizeSelectorProps) {
  const sizes: { key: FontSize; label: string; sample: string }[] = [
    { key: "small", label: "Small", sample: "Aa" },
    { key: "medium", label: "Medium", sample: "Aa" },
    { key: "large", label: "Large", sample: "Aa" },
  ];

  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-neutral-1">
      <div className="text-neutral-10 mt-0.5">
        <Type size={20} />
      </div>
      <div className="flex-1 min-w-0">
        <span className="block text-sm font-medium text-neutral-12">
          Font Size
        </span>
        <p className="text-sm text-neutral-10 mt-0.5">
          Adjust text size for better readability
        </p>
        <div
          className="flex gap-2 mt-3"
          role="radiogroup"
          aria-label="Font size"
        >
          {sizes.map((size) => (
            <Button
              className="flex flex-col px-4 py-2 rounded-lg border-2 focus:ring-primary-7 focus:ring-offset-2"
              key={size.key}
              type="button"
              role="radio"
              aria-checked={value === size.key}
              data-testid={`font-size-${size.key}`}
              onClick={() => onChange(size.key)}
            >
              <span
                className={`font-medium ${
                  size.key === "small"
                    ? "text-sm"
                    : size.key === "medium"
                      ? "text-base"
                      : "text-lg"
                }`}
              >
                {size.sample}
              </span>
              <span className="text-xs mt-1">{size.label}</span>
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// Main Component
// ==============================================================================

export function AccessibilitySettings({
  className = "",
}: AccessibilitySettingsProps) {
  const {
    screenReaderMode,
    reducedMotion,
    highContrast,
    fontSize,
    enhancedFocus,
    setScreenReaderMode,
    setReducedMotion,
    setHighContrast,
    setFontSize,
    setEnhancedFocus,
    resetToDefaults,
  } = useAccessibility();

  return (
    <div
      data-testid="accessibility-settings"
      className={`space-y-6 ${className}`}
    >
      <div>
        <h2 className="text-lg font-semibold text-neutral-12">
          Accessibility
        </h2>
        <p className="text-sm text-neutral-10 mt-1">
          Customize accessibility features to improve your experience
        </p>
      </div>
      <div className="space-y-3">
        <SettingToggle
          id="screen-reader-mode"
          testId="screen-reader-toggle"
          checked={screenReaderMode}
          onChange={setScreenReaderMode}
          label="Screen Reader Mode"
          description="Optimize the interface for screen reader users"
          icon={<Volume2 size={20} />}
        />

        <SettingToggle
          id="reduced-motion"
          testId="reduced-motion-toggle"
          checked={reducedMotion}
          onChange={setReducedMotion}
          label="Reduced Motion"
          description="Reduce animations and motion effects"
          icon={<Eye size={20} />}
        />

        <SettingToggle
          id="high-contrast"
          testId="high-contrast-toggle"
          checked={highContrast}
          onChange={setHighContrast}
          label="High Contrast"
          description="Increase color contrast for better visibility"
          icon={<Palette size={20} />}
        />

        <FontSizeSelector value={fontSize} onChange={setFontSize} />

        <SettingToggle
          id="enhanced-focus"
          testId="enhanced-focus-toggle"
          checked={enhancedFocus}
          onChange={setEnhancedFocus}
          label="Enhanced Focus Indicators"
          description="Make focus indicators more visible for keyboard navigation"
          icon={<Focus size={20} />}
        />
      </div>
      <div className="pt-4 border-t border-neutral-5">
        <Button
          variant="secondary"
          className="px-4 py-2 text-sm text-neutral-11 bg-neutral-1 border border-neutral-5 rounded-lg hover:bg-neutral-1 focus:ring-primary-7 focus:ring-offset-2"
          type="button"
          onClick={resetToDefaults}
        >
          <RotateCcw size={16} />
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}

export default AccessibilitySettings;
