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

import { Button } from "@/components/UI";

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
  className: _className = "",
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
      <Button
        variant="secondary"
        className="px-3 py-2 rounded-md text-neutral-11 hover:bg-neutral-2 focus:ring-primary-7"
        type="button"
        onClick={handleClick}
        aria-label={`Theme: ${config.label}`}
        aria-pressed={theme === "dark"}
        aria-haspopup={variant === "dropdown" ? "menu" : undefined}
        aria-expanded={variant === "dropdown" ? isDropdownOpen : undefined}
        onMouseEnter={() => compact && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <Icon
          size={18}
          data-testid={getIconTestId(theme)}
          className="flex-shrink-0"
        />
        {!compact && (
          <span className="text-sm font-medium">{config.label}</span>
        )}
      </Button>
      {/* Tooltip for compact mode */}
      {compact && showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-neutral-2 text-neutral-12 text-xs rounded shadow-lg whitespace-nowrap z-50"
        >
          {config.label}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-12 dark:border-t-neutral-11" />
        </div>
      )}
      {/* Dropdown menu */}
      {variant === "dropdown" && isDropdownOpen && (
        <div
          role="menu"
          className="absolute top-full right-0 mt-1 w-40 rounded-md bg-neutral-1 shadow-lg ring-1 ring-neutral-a1 dark:ring-neutral-a2 z-dropdown"
        >
          <div className="py-1">
            {THEME_CYCLE.map((themeOption) => {
              const optionConfig = THEME_CONFIG[themeOption];
              const OptionIcon = optionConfig.icon;
              const isSelected = theme === themeOption;

              return (
                <Button
                  variant="secondary"
                  className="w-full flex px-3 py-2 text-sm text-neutral-11 hover:bg-neutral-2"
                  key={themeOption}
                  role="menuitem"
                  onClick={() => handleSelectTheme(themeOption)}
                >
                  <OptionIcon size={16} className="flex-shrink-0" />
                  <span className="flex-1 text-left">{optionConfig.label}</span>
                  {isSelected && (
                    <Check
                      size={16}
                      className="text-primary-10 dark:text-primary-7"
                    />
                  )}
                </Button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ThemeToggle;
