/**
 * ThemeToggle Component
 *
 * Toggle button for switching between light/dark/system themes.
 * Features:
 * - Cycle mode (click to cycle through themes)
 * - Dropdown mode (select from menu)
 * - Compact mode (icon only with tooltip)
 * - Smooth transitions
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { Sun, Moon, Monitor, Check } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export type Theme = "light" | "dark" | "system";

export interface ThemeToggleProps {
  /** Current theme */
  theme?: Theme;
  /** Callback when theme changes */
  onThemeChange?: (theme: Theme) => void;
  /** Toggle variant */
  variant?: "cycle" | "dropdown";
  /** Compact mode (icon only) */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Constants
// ==============================================================================

const THEME_CYCLE: Theme[] = ["light", "dark", "system"];

const THEME_CONFIG: Record<Theme, { label: string; icon: typeof Sun }> = {
  light: { label: "Light Mode", icon: Sun },
  dark: { label: "Dark Mode", icon: Moon },
  system: { label: "System", icon: Monitor },
};

// ==============================================================================
// Component
// ==============================================================================

export function ThemeToggle({
  theme = "system",
  onThemeChange,
  variant = "cycle",
  compact = false,
  className = "",
}: ThemeToggleProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const config = THEME_CONFIG[theme];
  const Icon = config.icon;

  // Handle click outside for dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
    return undefined;
  }, [isDropdownOpen]);

  // Handle theme cycle
  const handleClick = useCallback(() => {
    if (variant === "dropdown") {
      setIsDropdownOpen(!isDropdownOpen);
    } else {
      // Cycle to next theme
      const currentIndex = THEME_CYCLE.indexOf(theme);
      const nextIndex = (currentIndex + 1) % THEME_CYCLE.length;
      const nextTheme = THEME_CYCLE[nextIndex];
      if (nextTheme) onThemeChange?.(nextTheme);
    }
  }, [variant, theme, onThemeChange, isDropdownOpen]);

  // Handle dropdown selection
  const handleSelectTheme = useCallback(
    (selectedTheme: Theme) => {
      onThemeChange?.(selectedTheme);
      setIsDropdownOpen(false);
    },
    [onThemeChange],
  );

  // Get test id for icon
  const getIconTestId = (iconTheme: Theme) => {
    switch (iconTheme) {
      case "light":
        return "sun-icon";
      case "dark":
        return "moon-icon";
      case "system":
        return "monitor-icon";
    }
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        type="button"
        onClick={handleClick}
        aria-label={`Theme: ${config.label}`}
        aria-pressed={theme === "dark"}
        aria-haspopup={variant === "dropdown" ? "menu" : undefined}
        aria-expanded={variant === "dropdown" ? isDropdownOpen : undefined}
        onMouseEnter={() => compact && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex items-center gap-2 px-3 py-2 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${className}`}
      >
        <Icon
          size={18}
          data-testid={getIconTestId(theme)}
          className="flex-shrink-0"
        />
        {!compact && (
          <span className="text-sm font-medium">{config.label}</span>
        )}
      </button>

      {/* Tooltip for compact mode */}
      {compact && showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded shadow-lg whitespace-nowrap z-50"
        >
          {config.label}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
        </div>
      )}

      {/* Dropdown menu */}
      {variant === "dropdown" && isDropdownOpen && (
        <div
          role="menu"
          className="absolute top-full right-0 mt-1 w-40 rounded-md bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50"
        >
          <div className="py-1">
            {THEME_CYCLE.map((themeOption) => {
              const optionConfig = THEME_CONFIG[themeOption];
              const OptionIcon = optionConfig.icon;
              const isSelected = theme === themeOption;

              return (
                <button
                  key={themeOption}
                  role="menuitem"
                  onClick={() => handleSelectTheme(themeOption)}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <OptionIcon size={16} className="flex-shrink-0" />
                  <span className="flex-1 text-left">{optionConfig.label}</span>
                  {isSelected && (
                    <Check
                      size={16}
                      className="text-blue-600 dark:text-blue-400"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ThemeToggle;
