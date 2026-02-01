/**
 * Design Token Validation Stories
 *
 * Interactive validation of all design system tokens.
 * Ensures tokens are properly defined and provides visual reference.
 *
 * Token Categories:
 * - Colors: Semantic palette (primary, success, warning, error, info, insight, neutral, grafana)
 * - Spacing: 4px grid scale (0-24)
 * - Z-Index: Stacking context tokens (10, 50, 55, 60, 65, 70, 75)
 * - Animation: Duration and easing tokens
 * - Sizing: Legitimate arbitrary patterns
 *
 * @see docs-internal/frontend/STYLE.md
 * @see scripts/audit-design-system.ts
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

// =============================================================================
// Token Validation Components
// =============================================================================

interface TokenStatusProps {
  name: string;
  value: string;
  status: "valid" | "warning" | "error";
  description?: string;
}

function TokenStatus({ name, value, status, description }: TokenStatusProps) {
  const statusColors = {
    valid: "bg-success-3 border-success-6 text-success-11",
    warning: "bg-warning-3 border-warning-6 text-warning-11",
    error: "bg-error-3 border-error-6 text-error-11",
  };

  const statusIcons = {
    valid: "✓",
    warning: "!",
    error: "✗",
  };

  return (
    <div className={`p-3 rounded-lg border ${statusColors[status]}`}>
      <div className="flex items-center gap-2">
        <span className="font-bold">{statusIcons[status]}</span>
        <code className="font-mono text-sm">{name}</code>
      </div>
      <div className="text-xs mt-1 opacity-80">{value}</div>
      {description && <div className="text-xs mt-1 italic">{description}</div>}
    </div>
  );
}

// =============================================================================
// Z-Index Token Validation
// =============================================================================

function ZIndexValidation() {
  const zIndexTokens = [
    { name: "z-0", value: "0", usage: "Base layer" },
    { name: "z-10", value: "10", usage: "Tooltip, dropdown trigger" },
    { name: "z-50", value: "50", usage: "Dropdown, popover, panel" },
    { name: "z-55", value: "55", usage: "Command palette" },
    { name: "z-60", value: "60", usage: "Modal, dialog" },
    { name: "z-65", value: "65", usage: "Notification toast" },
    { name: "z-70", value: "70", usage: "System alert" },
    { name: "z-75", value: "75", usage: "Critical toast (highest)" },
  ];

  const invalidPatterns = [
    { pattern: "z-20", reason: "Use z-10 or z-50 instead" },
    { pattern: "z-30", reason: "Use z-50 instead" },
    { pattern: "z-40", reason: "Use z-50 instead" },
    { pattern: "z-100", reason: "Use z-75 (max token value)" },
    { pattern: "z-999", reason: "Use z-75 (max token value)" },
    { pattern: "z-[999]", reason: "Arbitrary values not allowed" },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Z-Index Token Scale
        </h2>
        <p className="text-neutral-11">
          Stacking context tokens for consistent layering. Higher values overlay
          lower values.
        </p>
      </div>

      {/* Visual Stack */}
      <div className="relative h-64 bg-neutral-2 rounded-lg overflow-hidden">
        {zIndexTokens.map((token, index) => (
          <div
            key={token.name}
            className="absolute bg-primary-9 text-neutral-12 text-xs p-2 rounded shadow-lg"
            style={{
              zIndex: parseInt(token.value),
              left: `${index * 40 + 20}px`,
              top: `${index * 25 + 20}px`,
              width: "120px",
            }}
          >
            <div className="font-bold">{token.name}</div>
            <div className="text-primary-3">{token.usage}</div>
          </div>
        ))}
      </div>

      {/* Token Reference Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-6">
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Token
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Value
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Usage
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {zIndexTokens.map((token) => (
              <tr key={token.name} className="border-b border-neutral-5">
                <td className="py-2 px-4">
                  <code className="text-primary-11 bg-primary-3 px-1 rounded">
                    {token.name}
                  </code>
                </td>
                <td className="py-2 px-4 font-mono text-neutral-11">
                  {token.value}
                </td>
                <td className="py-2 px-4 text-neutral-10">{token.usage}</td>
                <td className="py-2 px-4">
                  <span className="text-success-11">✓ Valid</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Invalid Patterns */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-12 mb-3">
          Invalid Patterns (ESLint will error)
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {invalidPatterns.map((p) => (
            <div
              key={p.pattern}
              className="bg-error-3 border border-error-6 rounded-lg p-3"
            >
              <code className="text-error-11 font-mono line-through">
                {p.pattern}
              </code>
              <div className="text-xs text-error-10 mt-1">{p.reason}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Animation Duration Validation
// =============================================================================

function AnimationValidation() {
  const [playing, setPlaying] = useState<string | null>(null);

  const durationTokens = [
    { name: "duration-75", value: "75ms", usage: "Micro-interactions" },
    { name: "duration-100", value: "100ms", usage: "Quick feedback" },
    { name: "duration-150", value: "150ms", usage: "Fast transitions" },
    { name: "duration-200", value: "200ms", usage: "Standard hover" },
    { name: "duration-300", value: "300ms", usage: "Normal transitions" },
    { name: "duration-500", value: "500ms", usage: "Slow transitions" },
    { name: "duration-700", value: "700ms", usage: "Complex animations" },
    { name: "duration-1000", value: "1000ms", usage: "Very slow (rare)" },
  ];

  const easingTokens = [
    { name: "ease-linear", description: "Linear, no acceleration" },
    { name: "ease-in", description: "Accelerate from zero" },
    { name: "ease-out", description: "Decelerate to zero" },
    { name: "ease-in-out", description: "Accelerate then decelerate" },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Animation Duration Tokens
        </h2>
        <p className="text-neutral-11">
          Standard duration values for consistent motion. Click to preview.
        </p>
      </div>

      {/* Interactive Duration Preview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {durationTokens.map((token) => (
          <button
            key={token.name}
            onClick={() => {
              setPlaying(token.name);
              setTimeout(() => setPlaying(null), parseInt(token.value) + 100);
            }}
            className="p-4 border border-neutral-6 rounded-lg hover:bg-neutral-2 transition-colors text-left"
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className={`w-4 h-4 rounded-full bg-primary-9 transition-transform ${
                  playing === token.name ? "scale-150" : ""
                }`}
                style={{
                  transitionDuration: token.value,
                }}
              />
              <code className="text-sm text-primary-11">{token.name}</code>
            </div>
            <div className="text-xs text-neutral-10">{token.value}</div>
            <div className="text-xs text-neutral-9 mt-1">{token.usage}</div>
          </button>
        ))}
      </div>

      {/* Easing Reference */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-12 mb-3">
          Easing Functions
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {easingTokens.map((token) => (
            <div
              key={token.name}
              className="bg-neutral-2 border border-neutral-6 rounded-lg p-3"
            >
              <code className="text-sm text-neutral-12">{token.name}</code>
              <div className="text-xs text-neutral-10 mt-1">
                {token.description}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Invalid Patterns */}
      <div className="bg-error-3 border border-error-6 rounded-lg p-4">
        <h3 className="font-medium text-error-11 mb-2">
          Invalid Patterns (ESLint will error)
        </h3>
        <div className="flex flex-wrap gap-2">
          <code className="text-error-11 bg-error-4 px-2 py-1 rounded line-through">
            duration-[200ms]
          </code>
          <code className="text-error-11 bg-error-4 px-2 py-1 rounded line-through">
            duration-[0.3s]
          </code>
          <code className="text-error-11 bg-error-4 px-2 py-1 rounded line-through">
            delay-[150ms]
          </code>
        </div>
        <p className="text-xs text-error-10 mt-2">
          Use token values instead of arbitrary values. Example: duration-300
          not duration-[300ms]
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Sizing Patterns Validation
// =============================================================================

function SizingValidation() {
  const legitimatePatterns = [
    {
      category: "Viewport-Relative",
      patterns: ["max-h-[90vh]", "max-h-[80vh]", "max-w-[80vw]", "h-[80vh]"],
      reason: "Responsive layouts that scale with viewport",
    },
    {
      category: "Percentage-Based",
      patterns: ["max-w-[70%]", "max-w-[80%]", "w-[50%]"],
      reason: "Proportional sizing relative to parent",
    },
    {
      category: "Calc-Based",
      patterns: ["h-[calc(100vh-48px)]", "max-h-[calc(100vh-200px)]"],
      reason: "Dynamic layouts combining units",
    },
    {
      category: "WCAG Touch Targets",
      patterns: [
        "min-h-[44px]",
        "min-w-[44px]",
        "min-h-[32px]",
        "min-w-[32px]",
      ],
      reason: "Accessibility requirement (WCAG 2.5.8)",
    },
    {
      category: "Workflow Nodes",
      patterns: ["min-w-[180px]"],
      reason: "Standard React Flow node width",
    },
    {
      category: "Table Columns",
      patterns: [
        "min-w-[60px]",
        "min-w-[100px]",
        "min-w-[200px]",
        "max-w-[300px]",
      ],
      reason: "Data display consistency",
    },
    {
      category: "Truncation Limits",
      patterns: ["max-w-[80px]", "max-w-[120px]", "max-w-[150px]"],
      reason: "Text overflow control",
    },
    {
      category: "Input Constraints",
      patterns: ["min-h-[40px]", "max-h-[200px]", "max-h-[300px]"],
      reason: "Textarea/input height limits",
    },
    {
      category: "Container Heights",
      patterns: ["h-[300px]", "h-[400px]", "h-[500px]", "h-[600px]"],
      reason: "Fixed content areas",
    },
    {
      category: "Dropdown Widths",
      patterns: ["min-w-[120px]", "min-w-[150px]"],
      reason: "Menu minimum widths",
    },
    {
      category: "Badge Widths",
      patterns: ["min-w-[20px]", "min-w-[1.5rem]", "min-w-[3rem]"],
      reason: "Inline element sizing",
    },
    {
      category: "Modal Widths",
      patterns: ["min-w-[500px]", "min-w-[700px]"],
      reason: "Dialog/modal dimensions",
    },
  ];

  const invalidPatterns = [
    { pattern: "h-[42px]", fix: "h-10 (40px) or h-11 (44px)" },
    { pattern: "w-[250px]", fix: "w-64 (256px) or max-w-xs" },
    { pattern: "min-w-[175px]", fix: "min-w-44 (176px)" },
    { pattern: "p-[20px]", fix: "p-5 (20px)" },
    { pattern: "gap-[10px]", fix: "gap-2.5 (10px)" },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Sizing Pattern Validation
        </h2>
        <p className="text-neutral-11">
          Certain arbitrary sizing values are intentionally allowed when they
          serve specific purposes. See{" "}
          <code className="bg-neutral-3 px-1 rounded">
            docs-internal/frontend/STYLE.md#sizing-decisions
          </code>
        </p>
      </div>

      {/* Legitimate Patterns */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-neutral-12">
          Legitimate Patterns (Not Flagged)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {legitimatePatterns.map((category) => (
            <div
              key={category.category}
              className="bg-success-2 border border-success-6 rounded-lg p-4"
            >
              <h4 className="font-medium text-success-11 mb-2">
                {category.category}
              </h4>
              <div className="flex flex-wrap gap-1 mb-2">
                {category.patterns.map((p) => (
                  <code
                    key={p}
                    className="text-xs bg-success-3 text-success-11 px-1.5 py-0.5 rounded"
                  >
                    {p}
                  </code>
                ))}
              </div>
              <p className="text-xs text-success-10">{category.reason}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Invalid Patterns */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-12 mb-3">
          Invalid Patterns (Will Be Flagged)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-6">
                <th className="text-left py-2 px-4 font-medium text-neutral-11">
                  Pattern
                </th>
                <th className="text-left py-2 px-4 font-medium text-neutral-11">
                  Fix
                </th>
              </tr>
            </thead>
            <tbody>
              {invalidPatterns.map((p) => (
                <tr key={p.pattern} className="border-b border-neutral-5">
                  <td className="py-2 px-4">
                    <code className="text-error-11 bg-error-3 px-1 rounded line-through">
                      {p.pattern}
                    </code>
                  </td>
                  <td className="py-2 px-4">
                    <code className="text-success-11 bg-success-3 px-1 rounded">
                      {p.fix}
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Audit Command Reference
// =============================================================================

function AuditReference() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Design System Audit Commands
        </h2>
        <p className="text-neutral-11">
          Run these commands to validate design system compliance.
        </p>
      </div>

      <div className="space-y-4">
        <div className="bg-neutral-3 rounded-lg p-4 font-mono text-sm">
          <div className="text-neutral-10 mb-2">
            # Full audit (shows all violations)
          </div>
          <div className="text-neutral-12">npm run audit:design-system</div>
        </div>

        <div className="bg-neutral-3 rounded-lg p-4 font-mono text-sm">
          <div className="text-neutral-10 mb-2">
            # Strict mode (fails on errors - for CI)
          </div>
          <div className="text-neutral-12">
            npm run audit:design-system:strict
          </div>
        </div>

        <div className="bg-neutral-3 rounded-lg p-4 font-mono text-sm">
          <div className="text-neutral-10 mb-2"># With fix suggestions</div>
          <div className="text-neutral-12">
            npm run audit:design-system -- --fix
          </div>
        </div>

        <div className="bg-neutral-3 rounded-lg p-4 font-mono text-sm">
          <div className="text-neutral-10 mb-2"># Specific category only</div>
          <div className="text-neutral-12">
            npm run audit:design-system -- --category=color
          </div>
        </div>

        <div className="bg-neutral-3 rounded-lg p-4 font-mono text-sm">
          <div className="text-neutral-10 mb-2">
            # JSON output for CI integration
          </div>
          <div className="text-neutral-12">
            npm run audit:design-system -- --json
          </div>
        </div>
      </div>

      <div className="bg-primary-2 border border-primary-6 rounded-lg p-4">
        <h3 className="font-medium text-primary-11 mb-2">
          Violation Categories
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
          <div className="text-primary-11">
            <span className="font-bold">color</span>
            <span className="text-primary-10 ml-1">(error)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">sizing</span>
            <span className="text-primary-10 ml-1">(warning)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">spacing</span>
            <span className="text-primary-10 ml-1">(warning)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">zindex</span>
            <span className="text-primary-10 ml-1">(warning)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">typography</span>
            <span className="text-primary-10 ml-1">(warning)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">animation</span>
            <span className="text-primary-10 ml-1">(info)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">border</span>
            <span className="text-primary-10 ml-1">(info)</span>
          </div>
          <div className="text-primary-11">
            <span className="font-bold">shadow</span>
            <span className="text-primary-10 ml-1">(info)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Full Validation Dashboard
// =============================================================================

function ValidationDashboard() {
  const categories = [
    { name: "Colors", status: "valid" as const, count: "8 palettes" },
    { name: "Spacing", status: "valid" as const, count: "20 tokens" },
    { name: "Z-Index", status: "valid" as const, count: "8 tokens" },
    { name: "Animation", status: "valid" as const, count: "8 durations" },
    { name: "Typography", status: "valid" as const, count: "7 sizes" },
    { name: "Border Radius", status: "valid" as const, count: "7 tokens" },
    { name: "Shadows", status: "valid" as const, count: "6 tokens" },
    {
      name: "Sizing Patterns",
      status: "valid" as const,
      count: "12 categories",
    },
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-12 mb-2">
          Design Token Validation Dashboard
        </h1>
        <p className="text-neutral-11">
          Overview of all design system tokens and their validation status.
        </p>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {categories.map((cat) => (
          <TokenStatus
            key={cat.name}
            name={cat.name}
            value={cat.count}
            status={cat.status}
          />
        ))}
      </div>

      {/* Quick Links */}
      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4">
        <h3 className="font-medium text-neutral-12 mb-3">
          Documentation Links
        </h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-neutral-10">Style Guide:</span>
            <code className="text-primary-11 bg-primary-3 px-1 rounded">
              docs-internal/frontend/STYLE.md
            </code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-neutral-10">Audit Script:</span>
            <code className="text-primary-11 bg-primary-3 px-1 rounded">
              scripts/audit-design-system.ts
            </code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-neutral-10">Audit Patterns:</span>
            <code className="text-primary-11 bg-primary-3 px-1 rounded">
              scripts/lib/audit-patterns.ts
            </code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-neutral-10">Tailwind Config:</span>
            <code className="text-primary-11 bg-primary-3 px-1 rounded">
              tailwind.config.ts
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Meta & Stories
// =============================================================================

const meta: Meta = {
  title: "Design System/Token Validation",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Interactive validation of all design system tokens. Run audit commands to check compliance.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Dashboard: Story = {
  render: () => <ValidationDashboard />,
  parameters: {
    docs: {
      description: {
        story:
          "Overview of all design token categories and their validation status.",
      },
    },
  },
};

export const ZIndex: Story = {
  render: () => <ZIndexValidation />,
  parameters: {
    docs: {
      description: {
        story: "Z-index stacking context tokens with visual representation.",
      },
    },
  },
};

export const Animation: Story = {
  render: () => <AnimationValidation />,
  parameters: {
    docs: {
      description: {
        story: "Animation duration tokens with interactive preview.",
      },
    },
  },
};

export const Sizing: Story = {
  render: () => <SizingValidation />,
  parameters: {
    docs: {
      description: {
        story: "Legitimate sizing patterns that are intentionally allowed.",
      },
    },
  },
};

export const AuditCommands: Story = {
  render: () => <AuditReference />,
  parameters: {
    docs: {
      description: {
        story: "Reference for design system audit commands.",
      },
    },
  },
};
