/**
 * Theme Switcher Stories
 *
 * Interactive demonstration of the theme system.
 * Showcases color themes, dark mode, and code font switching.
 *
 * @see src/components/Settings/ThemeSettings.tsx
 * @see docs-internal/frontend/STYLE.md
 */

import { useState, useEffect } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Sun, Moon, Monitor, Palette, Code2 } from "lucide-react";
import type { ColorTheme, CodeFontTheme, ThemeMode } from "../types/preferences";

// =============================================================================
// Theme Demo Components
// =============================================================================

interface ThemePreviewCardProps {
  title: string;
  children: React.ReactNode;
}

function ThemePreviewCard({ title, children }: ThemePreviewCardProps) {
  return (
    <div className="border border-neutral-6 rounded-lg overflow-hidden">
      <div className="bg-neutral-4 px-4 py-2 border-b border-neutral-6">
        <span className="text-sm font-medium text-neutral-12">{title}</span>
      </div>
      <div className="p-4 bg-neutral-1">{children}</div>
    </div>
  );
}

function ComponentPreview() {
  return (
    <div className="space-y-4">
      {/* Buttons */}
      <div className="flex gap-2">
        <button className="px-4 py-2 bg-primary-9 text-neutral-12 rounded-md hover:bg-primary-10 transition-colors">
          Primary
        </button>
        <button className="px-4 py-2 bg-neutral-4 text-neutral-12 border border-neutral-6 rounded-md hover:bg-neutral-4 transition-colors">
          Secondary
        </button>
        <button className="px-4 py-2 bg-error-9 text-neutral-12 rounded-md hover:bg-error-10 transition-colors">
          Danger
        </button>
      </div>

      {/* Status Badges */}
      <div className="flex gap-2 flex-wrap">
        <span className="px-2 py-1 text-xs bg-success-3 text-success-11 rounded-full">Success</span>
        <span className="px-2 py-1 text-xs bg-warning-3 text-warning-11 rounded-full">Warning</span>
        <span className="px-2 py-1 text-xs bg-error-3 text-error-11 rounded-full">Error</span>
        <span className="px-2 py-1 text-xs bg-info-3 text-info-11 rounded-full">Info</span>
        <span className="px-2 py-1 text-xs bg-insight-3 text-insight-11 rounded-full">AI Insight</span>
      </div>

      {/* Input */}
      <input
        type="text"
        placeholder="Sample input field..."
        className="w-full px-3 py-2 bg-neutral-1 border border-neutral-6 rounded-md text-neutral-12 placeholder:text-neutral-9 focus:outline-none focus:ring-2 focus:ring-primary-7"
      />

      {/* Code Block */}
      <pre className="p-3 bg-neutral-4 rounded-md font-mono text-sm text-neutral-12 overflow-x-auto">
        <code>const theme = "violet-sage";</code>
      </pre>
    </div>
  );
}

// =============================================================================
// Interactive Theme Switcher
// =============================================================================

function InteractiveThemeSwitcher() {
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");
  const [colorTheme, setColorTheme] = useState<ColorTheme>("violet-sage");
  const [codeFont, setCodeFont] = useState<CodeFontTheme>("jetbrains");

  // Apply theme changes to document
  useEffect(() => {
    // Apply color theme
    document.documentElement.dataset.colorTheme = colorTheme;

    // Apply dark/light mode
    if (themeMode === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.classList.toggle("dark", prefersDark);
      document.documentElement.classList.toggle("light", !prefersDark);
    } else {
      document.documentElement.classList.toggle("dark", themeMode === "dark");
      document.documentElement.classList.toggle("light", themeMode === "light");
    }

    // Apply code font
    document.documentElement.dataset.codeFont = codeFont;
  }, [themeMode, colorTheme, codeFont]);

  const themeModes: Array<{ value: ThemeMode; label: string; icon: React.ReactNode }> = [
    { value: "light", label: "Light", icon: <Sun size={16} /> },
    { value: "dark", label: "Dark", icon: <Moon size={16} /> },
    { value: "system", label: "System", icon: <Monitor size={16} /> },
  ];

  const colorThemes: Array<{ value: ColorTheme; label: string; primary: string; neutral: string }> = [
    { value: "violet-sage", label: "Violet + Sage", primary: "var(--violet-9)", neutral: "var(--sage-6)" },
    { value: "teal-sage", label: "Teal + Sage", primary: "var(--teal-9)", neutral: "var(--sage-6)" },
    { value: "violet-olive", label: "Violet + Olive", primary: "var(--violet-9)", neutral: "var(--olive-6)" },
    { value: "teal-olive", label: "Teal + Olive", primary: "var(--teal-9)", neutral: "var(--olive-6)" },
  ];

  const codeFonts: Array<{ value: CodeFontTheme; label: string; family: string }> = [
    { value: "jetbrains", label: "JetBrains Mono", family: "'JetBrains Mono', monospace" },
    { value: "firacode", label: "Fira Code", family: "'Fira Code', monospace" },
    { value: "monaspace", label: "Monaspace", family: "'Monaspace Neon', monospace" },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Interactive Theme Switcher
        </h2>
        <p className="text-neutral-11">
          Toggle between theme options and see the changes in real-time.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Controls */}
        <div className="space-y-6">
          {/* Theme Mode */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-neutral-11">
              <Sun size={18} />
              <span className="text-sm font-medium">Appearance</span>
            </div>
            <div className="flex gap-2">
              {themeModes.map((mode) => (
                <button
                  key={mode.value}
                  onClick={() => setThemeMode(mode.value)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md border-2 transition-colors ${
                    themeMode === mode.value
                      ? "border-primary-9 bg-primary-3"
                      : "border-neutral-6 bg-neutral-2 hover:bg-neutral-4"
                  }`}
                >
                  <span className={themeMode === mode.value ? "text-primary-11" : "text-neutral-11"}>
                    {mode.icon}
                  </span>
                  <span className="text-sm text-neutral-12">{mode.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Color Theme */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-neutral-11">
              <Palette size={18} />
              <span className="text-sm font-medium">Color Theme</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {colorThemes.map((theme) => (
                <button
                  key={theme.value}
                  onClick={() => setColorTheme(theme.value)}
                  className={`flex items-center gap-3 p-3 rounded-md border-2 transition-colors text-left ${
                    colorTheme === theme.value
                      ? "border-primary-9 bg-primary-3"
                      : "border-neutral-6 bg-neutral-2 hover:bg-neutral-4"
                  }`}
                >
                  <div className="flex w-10 h-6 rounded overflow-hidden border border-neutral-6">
                    <div className="w-1/2" style={{ backgroundColor: theme.primary }} />
                    <div className="w-1/2" style={{ backgroundColor: theme.neutral }} />
                  </div>
                  <span className="text-sm text-neutral-12">{theme.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Code Font */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-neutral-11">
              <Code2 size={18} />
              <span className="text-sm font-medium">Code Font</span>
            </div>
            <div className="space-y-2">
              {codeFonts.map((font) => (
                <button
                  key={font.value}
                  onClick={() => setCodeFont(font.value)}
                  className={`flex items-center gap-4 w-full p-3 rounded-md border-2 transition-colors text-left ${
                    codeFont === font.value
                      ? "border-primary-9 bg-primary-3"
                      : "border-neutral-6 bg-neutral-2 hover:bg-neutral-4"
                  }`}
                >
                  <div
                    className="w-16 text-center py-1 px-2 bg-neutral-4 rounded"
                    style={{ fontFamily: font.family }}
                  >
                    <span className="text-sm text-neutral-12">0O1l</span>
                  </div>
                  <span className="text-sm text-neutral-12">{font.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Preview */}
        <div className="space-y-4">
          <ThemePreviewCard title="Component Preview">
            <ComponentPreview />
          </ThemePreviewCard>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Theme Comparison
// =============================================================================

function ThemeComparison() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Theme Comparison
        </h2>
        <p className="text-neutral-11">
          Side-by-side comparison of all color theme options.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Violet + Sage */}
        <div
          className="border border-neutral-6 rounded-lg overflow-hidden"
          data-color-theme="violet-sage"
        >
          <div className="bg-neutral-4 px-4 py-2 border-b border-neutral-6">
            <span className="text-sm font-medium text-neutral-12">Violet + Sage (Default)</span>
          </div>
          <div className="p-4 bg-neutral-1 space-y-3">
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--violet-9)" }} />
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--sage-6)" }} />
            </div>
            <p className="text-sm text-neutral-11">AI-native, innovation, purple-green harmony</p>
          </div>
        </div>

        {/* Teal + Sage */}
        <div
          className="border border-neutral-6 rounded-lg overflow-hidden"
          data-color-theme="teal-sage"
        >
          <div className="bg-neutral-4 px-4 py-2 border-b border-neutral-6">
            <span className="text-sm font-medium text-neutral-12">Teal + Sage</span>
          </div>
          <div className="p-4 bg-neutral-1 space-y-3">
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--teal-9)" }} />
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--sage-6)" }} />
            </div>
            <p className="text-sm text-neutral-11">Solarized-inspired, terminal classic</p>
          </div>
        </div>

        {/* Violet + Olive */}
        <div
          className="border border-neutral-6 rounded-lg overflow-hidden"
          data-color-theme="violet-olive"
        >
          <div className="bg-neutral-4 px-4 py-2 border-b border-neutral-6">
            <span className="text-sm font-medium text-neutral-12">Violet + Olive</span>
          </div>
          <div className="p-4 bg-neutral-1 space-y-3">
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--violet-9)" }} />
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--olive-6)" }} />
            </div>
            <p className="text-sm text-neutral-11">Warmer, earthy purple</p>
          </div>
        </div>

        {/* Teal + Olive */}
        <div
          className="border border-neutral-6 rounded-lg overflow-hidden"
          data-color-theme="teal-olive"
        >
          <div className="bg-neutral-4 px-4 py-2 border-b border-neutral-6">
            <span className="text-sm font-medium text-neutral-12">Teal + Olive</span>
          </div>
          <div className="p-4 bg-neutral-1 space-y-3">
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--teal-9)" }} />
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "var(--olive-6)" }} />
            </div>
            <p className="text-sm text-neutral-11">Warm terminal, nature feel</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Dark Mode Demo
// =============================================================================

function DarkModeDemo() {
  return (
    <div className="grid grid-cols-2 gap-0">
      {/* Light Mode */}
      <div className="light bg-neutral-1 p-6">
        <h3 className="text-lg font-semibold text-neutral-12 mb-4">Light Mode</h3>
        <ComponentPreview />
      </div>

      {/* Dark Mode */}
      <div className="dark bg-neutral-1 p-6">
        <h3 className="text-lg font-semibold text-neutral-12 mb-4">Dark Mode</h3>
        <ComponentPreview />
      </div>
    </div>
  );
}

// =============================================================================
// CSS Variables Reference
// =============================================================================

function CSSVariablesReference() {
  const semanticColors = [
    { name: "primary", description: "Primary accent (Violet/Teal based on theme)" },
    { name: "neutral", description: "General UI (Sage/Olive based on theme)" },
    { name: "success", description: "Success states (Grass)" },
    { name: "warning", description: "Warning states (Amber)" },
    { name: "error", description: "Error states (Ruby)" },
    { name: "info", description: "Informational (Sky)" },
    { name: "insight", description: "AI features (Violet)" },
    { name: "grafana", description: "Observability (Orange)" },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          CSS Variables Reference
        </h2>
        <p className="text-neutral-11">
          Semantic color variables that automatically adapt to the selected theme.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-6">
              <th className="text-left py-2 px-4 font-medium text-neutral-11">Semantic</th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">Variable Pattern</th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">Description</th>
            </tr>
          </thead>
          <tbody>
            {semanticColors.map((color) => (
              <tr key={color.name} className="border-b border-neutral-6">
                <td className="py-3 px-4 font-medium text-neutral-12 capitalize">{color.name}</td>
                <td className="py-3 px-4">
                  <code className="text-xs text-neutral-11">--{color.name}-1 to --{color.name}-12</code>
                </td>
                <td className="py-3 px-4 text-neutral-10">{color.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 font-mono text-xs">
        <p className="text-neutral-10 mb-2">/* Usage in CSS or Tailwind */</p>
        <p className="text-neutral-12">.button {"{"}</p>
        <p className="text-neutral-12 pl-4">background-color: var(--primary-9);</p>
        <p className="text-neutral-12 pl-4">color: white;</p>
        <p className="text-neutral-12">{"}"}</p>
        <br />
        <p className="text-neutral-10">{"<!-- Tailwind class -->"}</p>
        <p className="text-neutral-12">{"<button class=\"bg-primary-9 text-neutral-12\">Click me</button>"}</p>
      </div>
    </div>
  );
}

// =============================================================================
// Meta & Stories
// =============================================================================

const meta: Meta = {
  title: "Design System/Theme Switcher",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Interactive theme system with 4 color themes, dark/light mode, and code font selection. All themes use Radix Colors for WCAG compliance.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Interactive: Story = {
  render: () => <InteractiveThemeSwitcher />,
  parameters: {
    docs: {
      description: {
        story: "Interactive theme switcher with real-time preview.",
      },
    },
  },
};

export const Comparison: Story = {
  render: () => <ThemeComparison />,
  parameters: {
    docs: {
      description: {
        story: "Side-by-side comparison of all color theme options.",
      },
    },
  },
};

export const DarkVsLight: Story = {
  render: () => <DarkModeDemo />,
  parameters: {
    docs: {
      description: {
        story: "Dark mode and light mode comparison.",
      },
    },
  },
};

export const CSSVariables: Story = {
  render: () => <CSSVariablesReference />,
  parameters: {
    docs: {
      description: {
        story: "Reference guide for CSS custom properties used in theming.",
      },
    },
  },
};
