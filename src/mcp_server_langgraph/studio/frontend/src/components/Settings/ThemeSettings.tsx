/**
 * ThemeSettings Component
 *
 * Panel for managing theme and appearance preferences.
 * Features:
 * - Light/Dark/System theme toggle
 * - Color theme selection (Radix color palettes)
 * - Code font selection
 * - Visual previews for each option
 *
 * Uses Radix Colors for theme-aware design.
 * @see https://www.radix-ui.com/colors
 */

import {
  Sun,
  Moon,
  Monitor,
  Palette,
  Code2,
  RotateCcw,
} from "lucide-react";
import { usePreferences, useTheme } from "../../contexts/PreferencesContext";
import type { ColorTheme, CodeFontTheme, ThemeMode } from "../../types/preferences";

import { Button } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface ThemeSettingsProps {
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Theme Mode Configuration
// ==============================================================================

interface ThemeModeOption {
  value: ThemeMode;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const THEME_MODES: ThemeModeOption[] = [
  {
    value: "light",
    label: "Light",
    icon: <Sun size={20} />,
    description: "Always use light theme",
  },
  {
    value: "dark",
    label: "Dark",
    icon: <Moon size={20} />,
    description: "Always use dark theme",
  },
  {
    value: "system",
    label: "System",
    icon: <Monitor size={20} />,
    description: "Match system preference",
  },
];

// ==============================================================================
// Color Theme Configuration
// ==============================================================================

interface ColorThemeOption {
  value: ColorTheme;
  label: string;
  description: string;
  /** Primary and neutral color preview (CSS variable names) */
  primaryColor: string;
  neutralColor: string;
}

const COLOR_THEMES: ColorThemeOption[] = [
  {
    value: "violet-sage",
    label: "Violet & Slate",
    description: "Purple accent with cool blue-gray neutrals (default)",
    primaryColor: "var(--violet-9)",
    neutralColor: "var(--slate-8)",  // Use step 8 for more visible difference
  },
  {
    value: "teal-sage",
    label: "Teal & Slate",
    description: "Teal accent with cool blue-gray neutrals",
    primaryColor: "var(--teal-9)",
    neutralColor: "var(--slate-8)",
  },
  {
    value: "violet-olive",
    label: "Violet & Olive",
    description: "Purple accent with warm green-gray neutrals",
    primaryColor: "var(--violet-9)",
    neutralColor: "var(--olive-8)",  // Use step 8 for more visible difference
  },
  {
    value: "teal-olive",
    label: "Teal & Olive",
    description: "Teal accent with warm green-gray neutrals",
    primaryColor: "var(--teal-9)",
    neutralColor: "var(--olive-8)",
  },
];

// ==============================================================================
// Code Font Configuration
// ==============================================================================

interface CodeFontOption {
  value: CodeFontTheme;
  label: string;
  description: string;
  fontFamily: string;
}

const CODE_FONTS: CodeFontOption[] = [
  {
    value: "jetbrains",
    label: "JetBrains Mono",
    description: "Designed for developers, with code-specific ligatures",
    fontFamily: "'JetBrains Mono', monospace",
  },
  {
    value: "firacode",
    label: "Fira Code",
    description: "Popular open-source font with programming ligatures",
    fontFamily: "'Fira Code', monospace",
  },
  {
    value: "monaspace",
    label: "Monaspace",
    description: "GitHub's new variable font for code",
    fontFamily: "'Monaspace Neon', 'Monaspace Argon', monospace",
  },
];

// ==============================================================================
// Color Swatch Component
// ==============================================================================

interface ColorSwatchProps {
  primaryColor: string;
  neutralColor: string;
  isSelected: boolean;
}

function ColorSwatch({ primaryColor, neutralColor, isSelected }: ColorSwatchProps) {
  return (
    <div
      className={`
        flex overflow-hidden rounded-lg border-2 w-20 h-12 shadow-sm
        ${isSelected ? "border-primary-9" : "border-neutral-6"}
      `}
    >
      <div
        className="w-1/2 h-full"
        style={{ backgroundColor: primaryColor }}
      />
      <div
        className="w-1/2 h-full"
        style={{ backgroundColor: neutralColor }}
      />
    </div>
  );
}

// ==============================================================================
// Theme Mode Selector Component
// ==============================================================================

interface ThemeModeSelectorProps {
  value: ThemeMode;
  onChange: (mode: ThemeMode) => void;
}

function ThemeModeSelector({ value, onChange }: ThemeModeSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-neutral-11">
        <Sun size={18} />
        <span className="text-sm font-medium">Appearance</span>
      </div>
      <div
        className="flex gap-2"
        role="radiogroup"
        aria-label="Theme mode"
      >
        {THEME_MODES.map((mode) => (
          <Button
            key={mode.value}
            type="button"
            role="radio"
            variant="ghost"
            aria-checked={value === mode.value}
            data-testid={`theme-mode-${mode.value}`}
            onClick={() => onChange(mode.value)}
            className={`
              flex flex-col items-center gap-2 px-4 py-3 rounded-lg border-2
              transition-colors duration-fast
              ${value === mode.value
                ? "border-primary-9 bg-primary-3 text-primary-11"
                : "border-neutral-6 bg-neutral-2 text-neutral-11 hover:bg-neutral-3"
              }
            `}
          >
            <span className={value === mode.value ? "text-primary-11" : "text-neutral-11"}>
              {mode.icon}
            </span>
            <span className="text-sm font-medium text-neutral-12">
              {mode.label}
            </span>
          </Button>
        ))}
      </div>
    </div>
  );
}

// ==============================================================================
// Color Theme Selector Component
// ==============================================================================

interface ColorThemeSelectorProps {
  value: ColorTheme;
  onChange: (theme: ColorTheme) => void;
}

function ColorThemeSelector({ value, onChange }: ColorThemeSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-neutral-11">
        <Palette size={18} />
        <span className="text-sm font-medium">Color Theme</span>
      </div>
      <div
        className="grid grid-cols-2 gap-3"
        role="radiogroup"
        aria-label="Color theme"
      >
        {COLOR_THEMES.map((theme) => (
          <Button
            key={theme.value}
            type="button"
            role="radio"
            variant="ghost"
            aria-checked={value === theme.value}
            data-testid={`color-theme-${theme.value}`}
            onClick={() => onChange(theme.value)}
            className={`
              flex items-center gap-3 p-3 rounded-lg border-2
              transition-colors duration-fast text-left
              ${value === theme.value
                ? "border-primary-9 bg-primary-3"
                : "border-neutral-6 bg-neutral-2 hover:bg-neutral-3"
              }
            `}
          >
            <ColorSwatch
              primaryColor={theme.primaryColor}
              neutralColor={theme.neutralColor}
              isSelected={value === theme.value}
            />
            <div className="flex-1 min-w-0">
              <span className="block text-sm font-medium text-neutral-12 truncate">
                {theme.label}
              </span>
              <span className="block text-xs text-neutral-11 mt-0.5 truncate">
                {theme.description}
              </span>
            </div>
          </Button>
        ))}
      </div>
    </div>
  );
}

// ==============================================================================
// Code Font Selector Component
// ==============================================================================

interface CodeFontSelectorProps {
  value: CodeFontTheme;
  onChange: (font: CodeFontTheme) => void;
}

function CodeFontSelector({ value, onChange }: CodeFontSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-neutral-11">
        <Code2 size={18} />
        <span className="text-sm font-medium">Code Font</span>
      </div>
      <div
        className="space-y-2"
        role="radiogroup"
        aria-label="Code font"
      >
        {CODE_FONTS.map((font) => (
          <Button
            key={font.value}
            type="button"
            role="radio"
            variant="ghost"
            fullWidth
            aria-checked={value === font.value}
            data-testid={`code-font-${font.value}`}
            onClick={() => onChange(font.value)}
            className={`
              flex items-center gap-4 p-3 rounded-lg border-2
              transition-colors duration-fast text-left justify-start
              ${value === font.value
                ? "border-primary-9 bg-primary-3"
                : "border-neutral-6 bg-neutral-2 hover:bg-neutral-3"
              }
            `}
          >
            {/* Font preview */}
            <div
              className="w-20 text-center py-1 px-2 bg-neutral-4 rounded"
              style={{ fontFamily: font.fontFamily }}
            >
              <span className="text-sm text-neutral-12">0O1l</span>
            </div>
            <div className="flex-1 min-w-0">
              <span className="block text-sm font-medium text-neutral-12">
                {font.label}
              </span>
              <span className="block text-xs text-neutral-11 mt-0.5">
                {font.description}
              </span>
            </div>
          </Button>
        ))}
      </div>
    </div>
  );
}

// ==============================================================================
// Main Component
// ==============================================================================

export function ThemeSettings({ className = "" }: ThemeSettingsProps) {
  const { theme, setTheme } = useTheme();
  const { preferences, updateGeneralPreferences, resetToDefaults } = usePreferences();

  const handleColorThemeChange = (colorTheme: ColorTheme) => {
    updateGeneralPreferences({ colorTheme });
  };

  const handleCodeFontChange = (codeFontTheme: CodeFontTheme) => {
    updateGeneralPreferences({ codeFontTheme });
  };

  return (
    <div
      data-testid="theme-settings"
      className={`space-y-8 ${className}`}
    >
      <div>
        <h2 className="text-lg font-semibold text-neutral-12">
          Theme & Appearance
        </h2>
        <p className="text-sm text-neutral-11 mt-1">
          Customize the look and feel of Agent Studio
        </p>
      </div>

      <ThemeModeSelector value={theme} onChange={setTheme} />

      <ColorThemeSelector
        value={preferences.general.colorTheme}
        onChange={handleColorThemeChange}
      />

      <CodeFontSelector
        value={preferences.general.codeFontTheme}
        onChange={handleCodeFontChange}
      />

      <div className="pt-4 border-t border-neutral-6">
        <Button
          variant="secondary"
          type="button"
          onClick={resetToDefaults}
          data-testid="reset-theme-defaults"
        >
          <RotateCcw size={16} />
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}

export default ThemeSettings;
