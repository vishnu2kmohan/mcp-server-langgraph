/**
 * Typography Stories
 *
 * Showcases the typography system used throughout Agent Studio.
 * Uses Inter for UI text and JetBrains Mono for code.
 *
 * @see docs-internal/frontend/STYLE.md
 */

import type { Meta, StoryObj } from "@storybook/react-vite";

// =============================================================================
// Typography Scale Display
// =============================================================================

interface TypeScaleRowProps {
  name: string;
  className: string;
  size: string;
  lineHeight: string;
  usage: string;
}

function TypeScaleRow({
  name,
  className,
  size,
  lineHeight,
  usage,
}: TypeScaleRowProps) {
  return (
    <div className="flex items-baseline gap-6 py-4 border-b border-neutral-6">
      <div className="w-24 shrink-0">
        <code className="text-xs text-neutral-11">{name}</code>
      </div>
      <div className="w-24 shrink-0">
        <span className="text-xs text-neutral-10">
          {size} / {lineHeight}
        </span>
      </div>
      <div className="flex-1">
        <span className={`${className} text-neutral-12`}>
          The quick brown fox jumps over the lazy dog
        </span>
      </div>
      <div className="w-40 shrink-0">
        <span className="text-xs text-neutral-10">{usage}</span>
      </div>
    </div>
  );
}

// =============================================================================
// Story Components
// =============================================================================

function TypeScale() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Typography Scale
        </h2>
        <p className="text-neutral-11">
          Agent Studio uses a 4px-grid-aligned typography scale for consistent
          rhythm. All sizes are based on rem units (1rem = 16px).
        </p>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          <TypeScaleRow
            name="text-xs"
            className="text-xs"
            size="12px"
            lineHeight="16px"
            usage="Badges, captions"
          />
          <TypeScaleRow
            name="text-sm"
            className="text-sm"
            size="14px"
            lineHeight="20px"
            usage="Secondary text, labels"
          />
          <TypeScaleRow
            name="text-base"
            className="text-base"
            size="16px"
            lineHeight="24px"
            usage="Body text (default)"
          />
          <TypeScaleRow
            name="text-lg"
            className="text-lg"
            size="18px"
            lineHeight="28px"
            usage="Emphasis, lead text"
          />
          <TypeScaleRow
            name="text-xl"
            className="text-xl"
            size="20px"
            lineHeight="28px"
            usage="Subheadings"
          />
          <TypeScaleRow
            name="text-2xl"
            className="text-2xl"
            size="24px"
            lineHeight="32px"
            usage="Section headings"
          />
          <TypeScaleRow
            name="text-3xl"
            className="text-3xl"
            size="30px"
            lineHeight="36px"
            usage="Page titles"
          />
          <TypeScaleRow
            name="text-4xl"
            className="text-4xl"
            size="36px"
            lineHeight="40px"
            usage="Hero text"
          />
        </div>
      </div>
    </div>
  );
}

function FontFamilies() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Font Families
        </h2>
        <p className="text-neutral-11">
          Two font families are used: Inter for UI text and JetBrains Mono for
          code.
        </p>
      </div>

      <div className="space-y-6">
        <div className="border border-neutral-6 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-neutral-12 mb-2">
            Inter (font-sans)
          </h3>
          <p className="text-sm text-neutral-10 mb-4">
            Primary UI font. Excellent legibility at all sizes.
          </p>
          <div className="space-y-3 font-sans">
            <p className="font-normal text-neutral-12">
              Regular (400): The quick brown fox jumps over the lazy dog
            </p>
            <p className="font-medium text-neutral-12">
              Medium (500): The quick brown fox jumps over the lazy dog
            </p>
            <p className="font-semibold text-neutral-12">
              Semibold (600): The quick brown fox jumps over the lazy dog
            </p>
            <p className="font-bold text-neutral-12">
              Bold (700): The quick brown fox jumps over the lazy dog
            </p>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-neutral-12 mb-2">
            JetBrains Mono (font-mono)
          </h3>
          <p className="text-sm text-neutral-10 mb-4">
            Code font. Clear distinction between similar characters (0, O, l, 1,
            I).
          </p>
          <div className="space-y-3 font-mono">
            <p className="font-normal text-neutral-12">
              Regular (400): const hello = "world"; // 0O1lI
            </p>
            <p className="font-medium text-neutral-12">
              Medium (500): const hello = "world"; // 0O1lI
            </p>
            <p className="font-bold text-neutral-12">
              Bold (700): const hello = "world"; // 0O1lI
            </p>
          </div>
          <div className="mt-4 p-3 bg-neutral-2 rounded font-mono text-sm">
            <span className="text-neutral-12">function </span>
            <span className="text-primary-11">calculateTotal</span>
            <span className="text-neutral-12">(items: Item[]): </span>
            <span className="text-success-11">number</span>
            <span className="text-neutral-12"> {"{"}</span>
            <br />
            <span className="text-neutral-12">
              {}return items.reduce((sum, item) ={">"} sum + item.price, 0);
            </span>
            <br />
            <span className="text-neutral-12">{"}"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FontWeights() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">Font Weights</h2>
        <p className="text-neutral-11">
          Use appropriate weights for hierarchy. Avoid thin weights for body
          text.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-6">
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Weight
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Class
              </th>
              <th className="text-left py-2 px-4 font-medium text-neutral-11">
                Usage
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-normal text-neutral-12">
                400 (Normal)
              </td>
              <td className="py-3 px-4">
                <code className="text-xs text-neutral-11">font-normal</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                Body text, descriptions
              </td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-medium text-neutral-12">
                500 (Medium)
              </td>
              <td className="py-3 px-4">
                <code className="text-xs text-neutral-11">font-medium</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                Labels, buttons, tabs
              </td>
            </tr>
            <tr className="border-b border-neutral-6">
              <td className="py-3 px-4 font-semibold text-neutral-12">
                600 (Semibold)
              </td>
              <td className="py-3 px-4">
                <code className="text-xs text-neutral-11">font-semibold</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                Subheadings, emphasis
              </td>
            </tr>
            <tr>
              <td className="py-3 px-4 font-bold text-neutral-12">
                700 (Bold)
              </td>
              <td className="py-3 px-4">
                <code className="text-xs text-neutral-11">font-bold</code>
              </td>
              <td className="py-3 px-4 text-neutral-10">
                Headings, important text
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AccessibilityRules() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Typography Accessibility
        </h2>
        <p className="text-neutral-11">
          Follow these rules for WCAG 2.2 compliance.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            Minimum Body Size
          </h4>
          <p className="text-sm text-neutral-11 mb-2">
            Body text should be at least 16px (1rem). Smaller sizes are
            acceptable for captions and badges.
          </p>
          <div className="flex gap-4 mt-3">
            <div className="text-center">
              <div className="text-base text-success-11">16px</div>
              <span className="text-xs text-success-10">OK</span>
            </div>
            <div className="text-center">
              <div className="text-sm text-warning-11">14px</div>
              <span className="text-xs text-warning-10">Caution</span>
            </div>
            <div className="text-center">
              <div className="text-xs text-error-11">12px</div>
              <span className="text-xs text-error-10">Badges only</span>
            </div>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">Line Height</h4>
          <p className="text-sm text-neutral-11 mb-2">
            Use 1.4-1.6 line height for body text. This improves reading
            accuracy by approximately 20%.
          </p>
          <div className="flex gap-4 mt-3">
            <div className="text-center">
              <div className="text-lg text-neutral-12">1.5</div>
              <span className="text-xs text-success-10">Ideal</span>
            </div>
            <div className="text-center">
              <div className="text-lg text-neutral-12">1.4</div>
              <span className="text-xs text-success-10">Min</span>
            </div>
            <div className="text-center">
              <div className="text-lg text-neutral-12">1.6</div>
              <span className="text-xs text-success-10">Max</span>
            </div>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">Line Length</h4>
          <p className="text-sm text-neutral-11 mb-2">
            Keep lines between 50-75 characters. This is 27% faster for readers
            with dyslexia.
          </p>
          <div className="mt-3 bg-neutral-2 p-2 rounded text-sm text-neutral-11">
            <span className="bg-success-3">
              This line is about 60 characters long, which is ideal.
            </span>
          </div>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">Contrast Ratios</h4>
          <p className="text-sm text-neutral-11 mb-2">
            Body text: 4.5:1 minimum. Large text (24px+ or 18.66px+ bold): 3:1
            minimum.
          </p>
          <div className="flex gap-4 mt-3">
            <div className="text-center">
              <div className="text-lg font-bold text-neutral-12 bg-neutral-1 px-2 rounded">
                Aa
              </div>
              <span className="text-xs text-success-10">4.5:1+</span>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-neutral-10 bg-neutral-1 px-2 rounded">
                Aa
              </div>
              <span className="text-xs text-success-10">3:1+</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-primary-2 border border-primary-6 rounded-lg p-4">
        <h4 className="font-medium text-primary-11 mb-1">Pro Tip</h4>
        <p className="text-sm text-primary-11">
          Use <code className="bg-primary-3 px-1 rounded">max-w-prose</code>{" "}
          (65ch) to automatically constrain paragraph width to optimal reading
          length.
        </p>
      </div>
    </div>
  );
}

function HeadingHierarchy() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Heading Hierarchy
        </h2>
        <p className="text-neutral-11">
          Maintain proper heading hierarchy for accessibility. Never skip
          heading levels.
        </p>
      </div>

      <div className="space-y-4 max-w-2xl">
        <div className="border-l-4 border-primary-9 pl-4">
          <span className="text-xs font-mono text-neutral-10">h1</span>
          <h1 className="text-3xl font-bold text-neutral-12">Page Title</h1>
        </div>
        <div className="border-l-4 border-primary-8 pl-4 ml-4">
          <span className="text-xs font-mono text-neutral-10">h2</span>
          <h2 className="text-2xl font-semibold text-neutral-12">
            Section Heading
          </h2>
        </div>
        <div className="border-l-4 border-primary-7 pl-4 ml-8">
          <span className="text-xs font-mono text-neutral-10">h3</span>
          <h3 className="text-xl font-semibold text-neutral-12">
            Subsection Heading
          </h3>
        </div>
        <div className="border-l-4 border-primary-6 pl-4 ml-12">
          <span className="text-xs font-mono text-neutral-10">h4</span>
          <h4 className="text-lg font-medium text-neutral-12">Group Heading</h4>
        </div>
        <div className="border-l-4 border-primary-5 pl-4 ml-16">
          <span className="text-xs font-mono text-neutral-10">h5</span>
          <h5 className="text-base font-medium text-neutral-12">
            Minor Heading
          </h5>
        </div>
        <div className="border-l-4 border-primary-4 pl-4 ml-20">
          <span className="text-xs font-mono text-neutral-10">h6</span>
          <h6 className="text-sm font-medium text-neutral-12">Label Heading</h6>
        </div>
      </div>

      <div className="bg-warning-2 border border-warning-6 rounded-lg p-4">
        <h4 className="font-medium text-warning-11 mb-1">Common Mistake</h4>
        <p className="text-sm text-warning-11">
          Don't use headings for styling. If you need large text without
          semantic meaning, use{" "}
          <code className="bg-warning-3 px-1 rounded">text-2xl</code> on a
          {"<span>"} instead of {"<h2>"}.
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Meta & Stories
// =============================================================================

const meta: Meta = {
  title: "Design System/Typography",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Typography system for Agent Studio. Uses Inter for UI and JetBrains Mono for code, with a 4px-grid-aligned scale.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Scale: Story = {
  render: () => <TypeScale />,
  parameters: {
    docs: {
      description: {
        story: "Complete typography scale from text-xs to text-4xl.",
      },
    },
  },
};

export const Fonts: Story = {
  render: () => <FontFamilies />,
  parameters: {
    docs: {
      description: {
        story: "Font families used in Agent Studio: Inter and JetBrains Mono.",
      },
    },
  },
};

export const Weights: Story = {
  render: () => <FontWeights />,
  parameters: {
    docs: {
      description: {
        story: "Available font weights and their recommended usage.",
      },
    },
  },
};

export const Headings: Story = {
  render: () => <HeadingHierarchy />,
  parameters: {
    docs: {
      description: {
        story: "Proper heading hierarchy for accessibility.",
      },
    },
  },
};

export const Accessibility: Story = {
  render: () => <AccessibilityRules />,
  parameters: {
    docs: {
      description: {
        story: "Typography accessibility guidelines for WCAG 2.2 compliance.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-12 min-h-screen">
      <TypeScale />
      <FontFamilies />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Typography in dark mode context.",
      },
    },
  },
};
