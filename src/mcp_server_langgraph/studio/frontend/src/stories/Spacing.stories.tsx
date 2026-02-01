/**
 * Spacing Stories
 *
 * Documents the 4px grid-based spacing system used throughout Agent Studio.
 * All spacing values are multiples of 4px for consistent visual rhythm.
 *
 * @see docs-internal/frontend/STYLE.md
 */

import type { Meta, StoryObj } from "@storybook/react-vite";

// =============================================================================
// Spacing Scale Display
// =============================================================================

interface SpacingRowProps {
  token: string;
  value: string;
  pixels: string;
  usage: string;
}

function SpacingRow({ token, value, pixels, usage }: SpacingRowProps) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-neutral-6">
      <div className="w-20 shrink-0">
        <code className="text-xs text-neutral-11">{token}</code>
      </div>
      <div className="w-16 shrink-0 text-right">
        <span className="text-xs text-neutral-10">{value}</span>
      </div>
      <div className="w-12 shrink-0 text-right">
        <span className="text-xs font-mono text-neutral-9">{pixels}</span>
      </div>
      <div className="w-40 shrink-0">
        <div
          className="h-4 bg-primary-9 rounded-sm"
          style={{ width: pixels }}
          title={`${pixels} wide`}
        />
      </div>
      <div className="flex-1">
        <span className="text-sm text-neutral-10">{usage}</span>
      </div>
    </div>
  );
}

function SpacingScale() {
  const spacingTokens = [
    { token: "space-0", value: "0", pixels: "0px", usage: "Reset" },
    {
      token: "space-0.5",
      value: "0.125rem",
      pixels: "2px",
      usage: "Micro adjustments only",
    },
    {
      token: "space-1",
      value: "0.25rem",
      pixels: "4px",
      usage: "Tight spacing, inline elements",
    },
    {
      token: "space-2",
      value: "0.5rem",
      pixels: "8px",
      usage: "Component internal padding",
    },
    { token: "space-3", value: "0.75rem", pixels: "12px", usage: "Small gaps" },
    {
      token: "space-4",
      value: "1rem",
      pixels: "16px",
      usage: "Standard padding",
    },
    {
      token: "space-5",
      value: "1.25rem",
      pixels: "20px",
      usage: "Medium gaps",
    },
    {
      token: "space-6",
      value: "1.5rem",
      pixels: "24px",
      usage: "Section spacing",
    },
    { token: "space-8", value: "2rem", pixels: "32px", usage: "Large gaps" },
    {
      token: "space-10",
      value: "2.5rem",
      pixels: "40px",
      usage: "Section breaks",
    },
    {
      token: "space-12",
      value: "3rem",
      pixels: "48px",
      usage: "Major sections",
    },
    {
      token: "space-16",
      value: "4rem",
      pixels: "64px",
      usage: "Page-level spacing",
    },
    {
      token: "space-20",
      value: "5rem",
      pixels: "80px",
      usage: "Hero sections",
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Spacing Scale (4px Grid)
        </h2>
        <p className="text-neutral-11">
          All spacing values are multiples of 4px for consistent visual rhythm.
        </p>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          <div className="flex items-center gap-4 py-2 border-b-2 border-neutral-6 font-medium text-sm text-neutral-11">
            <div className="w-20 shrink-0">Token</div>
            <div className="w-16 shrink-0 text-right">Value</div>
            <div className="w-12 shrink-0 text-right">Pixels</div>
            <div className="w-40 shrink-0">Visual</div>
            <div className="flex-1">Use Case</div>
          </div>
          {spacingTokens.map((token) => (
            <SpacingRow key={token.token} {...token} />
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Spacing Rules
// =============================================================================

function SpacingRules() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Spacing Rules
        </h2>
        <p className="text-neutral-11">
          Follow these rules for consistent spacing throughout the application.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            1. Internal &le; External
          </h4>
          <p className="text-sm text-neutral-11 mb-3">
            Padding inside elements should be less than or equal to margin
            between elements.
          </p>
          <div className="flex gap-4">
            <div className="bg-primary-3 border-2 border-primary-6 rounded p-3">
              <span className="text-sm text-primary-11">p-3 (12px)</span>
            </div>
            <div className="bg-primary-3 border-2 border-primary-6 rounded p-3">
              <span className="text-sm text-primary-11">gap-4 (16px)</span>
            </div>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            2. Gestalt Proximity
          </h4>
          <p className="text-sm text-neutral-11 mb-3">
            Related items closer together, unrelated farther apart.
          </p>
          <div className="space-y-4">
            <div className="flex gap-1">
              <div className="w-8 h-8 bg-success-9 rounded" />
              <div className="w-8 h-8 bg-success-9 rounded" />
              <div className="w-8 h-8 bg-success-9 rounded" />
            </div>
            <div className="flex gap-1">
              <div className="w-8 h-8 bg-warning-9 rounded" />
              <div className="w-8 h-8 bg-warning-9 rounded" />
            </div>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            3. Consistent Increments
          </h4>
          <p className="text-sm text-neutral-11 mb-3">
            Use 4px steps. Avoid odd values like 7px or 13px.
          </p>
          <div className="flex gap-2 items-end">
            <div className="flex flex-col items-center">
              <div className="w-4 h-4 bg-success-9 rounded-sm" />
              <span className="text-xs text-success-10 mt-1">4px</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-8 h-8 bg-success-9 rounded-sm" />
              <span className="text-xs text-success-10 mt-1">8px</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 bg-success-9 rounded-sm" />
              <span className="text-xs text-success-10 mt-1">12px</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 bg-success-9 rounded-sm" />
              <span className="text-xs text-success-10 mt-1">16px</span>
            </div>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">4. Touch Targets</h4>
          <p className="text-sm text-neutral-11 mb-3">
            Minimum 44x44px (Apple) or 48x48px (Google Material).
          </p>
          <div className="flex gap-4 items-center">
            <div className="w-11 h-11 bg-primary-9 rounded flex items-center justify-center">
              <span className="text-xs text-neutral-12">44px</span>
            </div>
            <div className="w-12 h-12 bg-primary-9 rounded flex items-center justify-center">
              <span className="text-xs text-neutral-12">48px</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Component Spacing Guidelines
// =============================================================================

function ComponentSpacing() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Component Spacing Guidelines
        </h2>
        <p className="text-neutral-11">
          Standard spacing patterns for common UI components.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-6">
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Component
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Internal Padding
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                External Margin
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">Button</td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  py-2 px-4
                </code>{" "}
                (sm),{}
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  py-3 px-6
                </code>{" "}
                (md)
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">gap-2</code>{" "}
                between buttons
              </td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">Card</td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">p-4</code>{" "}
                or{}
                <code className="text-xs bg-neutral-4 px-1 rounded">p-6</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">gap-4</code>{" "}
                between cards
              </td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">Input</td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  py-2 px-3
                </code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  space-y-4
                </code>{" "}
                between fields
              </td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">Modal</td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">p-6</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">N/A (overlay)</td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">
                Form Field
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  space-y-1.5
                </code>{" "}
                internal
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  space-y-4
                </code>{" "}
                between fields
              </td>
            </tr>
            <tr>
              <td className="py-3 px-4 font-medium text-neutral-12">Section</td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">py-6</code>{" "}
                to{}
                <code className="text-xs bg-neutral-4 px-1 rounded">py-8</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  space-y-12
                </code>{" "}
                to{}
                <code className="text-xs bg-neutral-4 px-1 rounded">
                  space-y-16
                </code>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// Spacing Utilities Reference
// =============================================================================

function SpacingUtilities() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Tailwind Spacing Utilities
        </h2>
        <p className="text-neutral-11">
          Common Tailwind classes for applying spacing.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Padding */}
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-3">Padding</h4>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <code className="text-neutral-11">p-{"{n}"}</code>
              <span className="text-neutral-10">All sides</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">px-{"{n}"}</code>
              <span className="text-neutral-10">Horizontal</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">py-{"{n}"}</code>
              <span className="text-neutral-10">Vertical</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">pt/pr/pb/pl-{"{n}"}</code>
              <span className="text-neutral-10">Single side</span>
            </div>
          </div>
        </div>

        {/* Margin */}
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-3">Margin</h4>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <code className="text-neutral-11">m-{"{n}"}</code>
              <span className="text-neutral-10">All sides</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">mx-{"{n}"}</code>
              <span className="text-neutral-10">Horizontal</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">my-{"{n}"}</code>
              <span className="text-neutral-10">Vertical</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">mt/mr/mb/ml-{"{n}"}</code>
              <span className="text-neutral-10">Single side</span>
            </div>
          </div>
        </div>

        {/* Gap */}
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-3">
            Gap (Flexbox/Grid)
          </h4>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <code className="text-neutral-11">gap-{"{n}"}</code>
              <span className="text-neutral-10">All gaps</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">gap-x-{"{n}"}</code>
              <span className="text-neutral-10">Column gap</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">gap-y-{"{n}"}</code>
              <span className="text-neutral-10">Row gap</span>
            </div>
          </div>
        </div>

        {/* Space Between */}
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-3">Space Between</h4>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between">
              <code className="text-neutral-11">space-x-{"{n}"}</code>
              <span className="text-neutral-10">Horizontal children</span>
            </div>
            <div className="flex justify-between">
              <code className="text-neutral-11">space-y-{"{n}"}</code>
              <span className="text-neutral-10">Vertical children</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-primary-2 border border-primary-6 rounded-lg p-4">
        <h4 className="font-medium text-primary-11 mb-1">Pro Tip</h4>
        <p className="text-sm text-primary-11">
          Prefer <code className="bg-primary-3 px-1 rounded">gap-*</code> over{}
          <code className="bg-primary-3 px-1 rounded">space-*</code> when using
          Flexbox or Grid. Gap doesn't add margin to the last child and works
          better with wrapping.
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Visual Examples
// =============================================================================

function VisualExamples() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Visual Examples
        </h2>
        <p className="text-neutral-11">
          Real-world examples of spacing patterns in action.
        </p>
      </div>

      {/* Form Example */}
      <div className="border border-neutral-6 rounded-lg p-6">
        <h4 className="font-medium text-neutral-12 mb-4">Form Layout</h4>
        <div className="max-w-md space-y-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-neutral-12">
              Email
            </label>
            <input
              type="text"
              placeholder="you@example.com"
              className="w-full px-3 py-2 bg-neutral-1 border border-neutral-6 rounded-md text-neutral-12 placeholder:text-neutral-9"
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-neutral-12">
              Password
            </label>
            <input
              type="password"
              placeholder="Enter password"
              className="w-full px-3 py-2 bg-neutral-1 border border-neutral-6 rounded-md text-neutral-12 placeholder:text-neutral-9"
            />
            <p className="text-sm text-neutral-10">Must be 8+ characters</p>
          </div>
          <div className="pt-2">
            <button className="px-4 py-2 bg-primary-9 text-neutral-12 rounded-md hover:bg-primary-10 transition-colors">
              Sign In
            </button>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-neutral-6">
          <p className="text-xs text-neutral-10 font-mono">
            space-y-4 between fields, space-y-1.5 within field, pt-2 before
            button
          </p>
        </div>
      </div>

      {/* Card Grid Example */}
      <div className="border border-neutral-6 rounded-lg p-6">
        <h4 className="font-medium text-neutral-12 mb-4">Card Grid</h4>
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="p-4 bg-neutral-2 border border-neutral-6 rounded-lg"
            >
              <div className="w-8 h-8 bg-primary-9 rounded mb-3" />
              <h5 className="font-medium text-neutral-12 mb-1">Card {n}</h5>
              <p className="text-sm text-neutral-10">
                Card content with p-4 internal padding.
              </p>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-neutral-6">
          <p className="text-xs text-neutral-10 font-mono">
            gap-4 between cards, p-4 inside cards, mb-3 below icon, mb-1 below
            title
          </p>
        </div>
      </div>

      {/* Button Group Example */}
      <div className="border border-neutral-6 rounded-lg p-6">
        <h4 className="font-medium text-neutral-12 mb-4">Button Groups</h4>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-primary-9 text-neutral-12 rounded-md">
            Primary
          </button>
          <button className="px-4 py-2 bg-neutral-4 text-neutral-12 border border-neutral-6 rounded-md">
            Secondary
          </button>
          <button className="px-4 py-2 text-neutral-11 hover:text-neutral-12">
            Tertiary
          </button>
        </div>
        <div className="mt-4 pt-4 border-t border-neutral-6">
          <p className="text-xs text-neutral-10 font-mono">
            gap-2 between buttons, px-4 py-2 inside buttons
          </p>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Meta & Stories
// =============================================================================

const meta: Meta = {
  title: "Design System/Spacing",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "4px grid-based spacing system for consistent visual rhythm. All values are multiples of 4px.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Scale: Story = {
  render: () => <SpacingScale />,
  parameters: {
    docs: {
      description: {
        story: "Complete spacing scale from 0 to 80px (20 units).",
      },
    },
  },
};

export const Rules: Story = {
  render: () => <SpacingRules />,
  parameters: {
    docs: {
      description: {
        story: "Core rules for applying spacing consistently.",
      },
    },
  },
};

export const Components: Story = {
  render: () => <ComponentSpacing />,
  parameters: {
    docs: {
      description: {
        story: "Standard spacing patterns for common UI components.",
      },
    },
  },
};

export const Utilities: Story = {
  render: () => <SpacingUtilities />,
  parameters: {
    docs: {
      description: {
        story: "Tailwind CSS utility classes for applying spacing.",
      },
    },
  },
};

export const Examples: Story = {
  render: () => <VisualExamples />,
  parameters: {
    docs: {
      description: {
        story: "Real-world examples of spacing patterns in action.",
      },
    },
  },
};
