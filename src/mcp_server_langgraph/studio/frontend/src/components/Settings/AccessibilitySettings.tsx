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

// ==============================================================================
// Types
// ==============================================================================

export interface AccessibilitySettingsProps {
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Toggle Component
// ==============================================================================

interface ToggleProps {
  id: string;
  testId: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description: string;
  icon: React.ReactNode;
}

function Toggle({
  id,
  testId,
  checked,
  onChange,
  label,
  description,
  icon,
}: ToggleProps) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
      <div className="text-gray-500 dark:text-gray-400 mt-0.5">{icon}</div>
      <div className="flex-1 min-w-0">
        <label
          htmlFor={id}
          className="block text-sm font-medium text-gray-900 dark:text-gray-100"
        >
          {label}
        </label>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          {description}
        </p>
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        data-testid={testId}
        onClick={() => onChange(!checked)}
        onKeyDown={(e) => {
          if (e.key === " " || e.key === "Enter") {
            e.preventDefault();
            onChange(!checked);
          }
        }}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          checked ? "bg-blue-600" : "bg-gray-200 dark:bg-gray-600"
        }`}
      >
        <span className="sr-only">{label}</span>
        <span
          aria-hidden="true"
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
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
    <div className="flex items-start gap-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
      <div className="text-gray-500 dark:text-gray-400 mt-0.5">
        <Type size={20} />
      </div>
      <div className="flex-1 min-w-0">
        <span className="block text-sm font-medium text-gray-900 dark:text-gray-100">
          Font Size
        </span>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Adjust text size for better readability
        </p>
        <div
          className="flex gap-2 mt-3"
          role="radiogroup"
          aria-label="Font size"
        >
          {sizes.map((size) => (
            <button
              key={size.key}
              type="button"
              role="radio"
              aria-checked={value === size.key}
              data-testid={`font-size-${size.key}`}
              onClick={() => onChange(size.key)}
              className={`flex flex-col items-center justify-center px-4 py-2 rounded-lg border-2 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                value === size.key
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                  : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300"
              }`}
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
            </button>
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Accessibility
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Customize accessibility features to improve your experience
        </p>
      </div>

      <div className="space-y-3">
        <Toggle
          id="screen-reader-mode"
          testId="screen-reader-toggle"
          checked={screenReaderMode}
          onChange={setScreenReaderMode}
          label="Screen Reader Mode"
          description="Optimize the interface for screen reader users"
          icon={<Volume2 size={20} />}
        />

        <Toggle
          id="reduced-motion"
          testId="reduced-motion-toggle"
          checked={reducedMotion}
          onChange={setReducedMotion}
          label="Reduced Motion"
          description="Reduce animations and motion effects"
          icon={<Eye size={20} />}
        />

        <Toggle
          id="high-contrast"
          testId="high-contrast-toggle"
          checked={highContrast}
          onChange={setHighContrast}
          label="High Contrast"
          description="Increase color contrast for better visibility"
          icon={<Palette size={20} />}
        />

        <FontSizeSelector value={fontSize} onChange={setFontSize} />

        <Toggle
          id="enhanced-focus"
          testId="enhanced-focus-toggle"
          checked={enhancedFocus}
          onChange={setEnhancedFocus}
          label="Enhanced Focus Indicators"
          description="Make focus indicators more visible for keyboard navigation"
          icon={<Focus size={20} />}
        />
      </div>

      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={resetToDefaults}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          <RotateCcw size={16} />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}

export default AccessibilitySettings;
