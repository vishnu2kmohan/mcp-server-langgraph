/**
 * Data Visualization Palettes Stories
 *
 * Showcases ColorBrewer palettes and chart color constants used for data visualization.
 * All palettes are selected for WCAG accessibility and colorblind safety.
 *
 * @see https://colorbrewer2.org/
 * @see docs-internal/frontend/STYLE.md
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  CHART_PALETTES,
  PAUL_TOL_PALETTE,
  NODE_TYPE_COLORS,
  VEGA_LITE_THEME,
} from "../design-system/chart-colors";

// =============================================================================
// Color Swatch Components
// =============================================================================

interface PaletteSwatchProps {
  colors: readonly string[];
  name: string;
  scheme?: string;
}

function PaletteSwatch({ colors, name, scheme }: PaletteSwatchProps) {
  return (
    <div className="space-y-2">
      <div>
        <h4 className="text-sm font-medium text-neutral-12">{name}</h4>
        {scheme && (
          <code className="text-xs text-neutral-10">scheme: "{scheme}"</code>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {colors.map((color, index) => (
          <div key={index} className="text-center">
            <div
              className="w-12 h-12 rounded-md shadow-sm border border-neutral-6"
              style={{ backgroundColor: color }}
              title={color}
            />
            <span className="text-xs text-neutral-11 mt-1 block font-mono">
              {color}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface NodeTypeSwatchProps {
  nodeType: keyof typeof NODE_TYPE_COLORS;
}

function NodeTypeSwatch({ nodeType }: NodeTypeSwatchProps) {
  const config = NODE_TYPE_COLORS[nodeType];
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-neutral-6 bg-neutral-2">
      <div
        className="w-10 h-10 rounded-md border-2"
        style={{
          backgroundColor: config.fill,
          borderColor: config.stroke,
        }}
      />
      <div className="flex-1">
        <span className="text-sm font-medium text-neutral-12">
          {config.label}
        </span>
        <div className="text-xs text-neutral-10 font-mono">
          {nodeType} • {config.pattern}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Story Components
// =============================================================================

function CategoricalPalettes() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Categorical Palettes
        </h2>
        <p className="text-neutral-11">
          For discrete data with no inherent ordering. Set2 is the default
          choice (colorblind-safe up to 3 categories). Use Dark2 for higher
          contrast.
        </p>
      </div>

      <PaletteSwatch
        name="Set2 (Default)"
        scheme="set2"
        colors={CHART_PALETTES.categorical.colors}
      />

      <PaletteSwatch
        name="Dark2 (High Contrast)"
        scheme="dark2"
        colors={CHART_PALETTES.categoricalDark.colors}
      />

      <PaletteSwatch
        name="Paul Tol (8+ Categories)"
        colors={PAUL_TOL_PALETTE}
      />

      <div className="bg-warning-2 border border-warning-6 rounded-lg p-4">
        <h4 className="font-medium text-warning-11 mb-1">Accessibility Note</h4>
        <p className="text-sm text-warning-11">
          Categorical palettes are colorblind-safe for up to 3-4 categories. For
          more categories, always add redundant encoding (shapes, patterns,
          labels).
        </p>
      </div>
    </div>
  );
}

function SequentialPalettes() {
  // Generate approximate color ramps for display
  const sequentialExamples = {
    blues: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
    greens: ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"],
    purples: ["#fcfbfd", "#dadaeb", "#9e9ac8", "#6a51a3", "#3f007d"],
    viridis: ["#440154", "#414487", "#2a788e", "#22a884", "#fde725"],
  };

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Sequential Palettes
        </h2>
        <p className="text-neutral-11">
          For ordered/continuous data. Viridis is perceptually uniform and
          colorblind-safe for all users.
        </p>
      </div>

      <PaletteSwatch
        name="Blues"
        scheme="blues"
        colors={sequentialExamples.blues}
      />

      <PaletteSwatch
        name="Greens"
        scheme="greens"
        colors={sequentialExamples.greens}
      />

      <PaletteSwatch
        name="Purples"
        scheme="purples"
        colors={sequentialExamples.purples}
      />

      <PaletteSwatch
        name="Viridis (Recommended)"
        scheme="viridis"
        colors={sequentialExamples.viridis}
      />

      <div className="bg-success-2 border border-success-6 rounded-lg p-4">
        <h4 className="font-medium text-success-11 mb-1">Best Practice</h4>
        <p className="text-sm text-success-11">
          Use Viridis for heatmaps and continuous data. It maintains perceptual
          uniformity across the entire range and works well for all colorblind
          types.
        </p>
      </div>
    </div>
  );
}

function DivergingPalettes() {
  // Generate approximate diverging ramps for display
  const divergingExamples = {
    rdbu: [
      "#67001f",
      "#b2182b",
      "#f4a582",
      "#f7f7f7",
      "#92c5de",
      "#2166ac",
      "#053061",
    ],
    brbg: [
      "#543005",
      "#8c510a",
      "#d8b365",
      "#f5f5f5",
      "#5ab4ac",
      "#01665e",
      "#003c30",
    ],
    prgn: [
      "#40004b",
      "#762a83",
      "#c2a5cf",
      "#f7f7f7",
      "#a6dba0",
      "#1b7837",
      "#00441b",
    ],
  };

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Diverging Palettes
        </h2>
        <p className="text-neutral-11">
          For data with a meaningful midpoint. Brown-Teal (BrBG) is the most
          colorblind-safe option.
        </p>
      </div>

      <PaletteSwatch
        name="Blue-Red"
        scheme="rdbu"
        colors={divergingExamples.rdbu}
      />

      <PaletteSwatch
        name="Brown-Teal (Colorblind Safe)"
        scheme="brbg"
        colors={divergingExamples.brbg}
      />

      <PaletteSwatch
        name="Purple-Green"
        scheme="prgn"
        colors={divergingExamples.prgn}
      />

      <div className="bg-info-2 border border-info-6 rounded-lg p-4">
        <h4 className="font-medium text-info-11 mb-1">When to Use</h4>
        <p className="text-sm text-info-11">
          Use diverging palettes when your data has a natural midpoint (e.g.,
          positive/negative change, above/below average).
        </p>
      </div>
    </div>
  );
}

function NodeTypeColors() {
  const nodeTypes = Object.keys(NODE_TYPE_COLORS) as Array<
    keyof typeof NODE_TYPE_COLORS
  >;

  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          LangGraph Node Types
        </h2>
        <p className="text-neutral-11">
          Semantic colors for LangGraph workflow nodes. Each type includes a
          pattern for colorblind accessibility.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 max-w-2xl">
        {nodeTypes.map((nodeType) => (
          <NodeTypeSwatch key={nodeType} nodeType={nodeType} />
        ))}
      </div>

      <div className="bg-insight-2 border border-insight-6 rounded-lg p-4">
        <h4 className="font-medium text-insight-11 mb-1">Pattern Encoding</h4>
        <p className="text-sm text-insight-11">
          In high-contrast mode, patterns are overlaid on node colors to ensure
          nodes remain distinguishable for colorblind users.
        </p>
      </div>
    </div>
  );
}

function VegaLiteTheme() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Vega-Lite Theme Configuration
        </h2>
        <p className="text-neutral-11">
          Default theme configuration applied to all Vega-Lite charts in Agent
          Studio.
        </p>
      </div>

      <div className="bg-neutral-2 border border-neutral-6 rounded-lg p-4 overflow-x-auto">
        <pre className="text-xs font-mono text-neutral-12">
          {JSON.stringify(VEGA_LITE_THEME, null, 2)}
        </pre>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-neutral-12">Key Features</h3>
        <ul className="list-disc list-inside space-y-2 text-neutral-11 text-sm">
          <li>Transparent background for seamless integration</li>
          <li>Set2 default for categorical data (colorblind-safe)</li>
          <li>BrBG for diverging data (most colorblind-safe option)</li>
          <li>Viridis for heatmaps (perceptually uniform)</li>
          <li>CSS variables for axis/legend colors (theme-aware)</li>
          <li>Inter font family for consistency</li>
        </ul>
      </div>
    </div>
  );
}

function AccessibilityGuidelines() {
  return (
    <div className="space-y-8 p-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-12 mb-2">
          Accessibility Guidelines
        </h2>
        <p className="text-neutral-11">
          Best practices for accessible data visualization.
        </p>
      </div>

      <div className="space-y-4">
        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            1. Limit Categories
          </h4>
          <p className="text-sm text-neutral-11">
            Keep categorical data to 4-5 categories maximum. If more are needed,
            consider grouping or using interactive filtering.
          </p>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            2. Redundant Encoding
          </h4>
          <p className="text-sm text-neutral-11">
            Never rely on color alone. Add shapes, patterns, labels, or position
            to convey meaning.
          </p>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            3. Use Sequential for Continuous
          </h4>
          <p className="text-sm text-neutral-11">
            Sequential palettes (especially Viridis) are always safe for
            continuous data, regardless of colorblind type.
          </p>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            4. Test with Simulators
          </h4>
          <p className="text-sm text-neutral-11">
            Use tools like Color Oracle or Viz Palette to simulate colorblind
            vision before shipping charts.
          </p>
        </div>

        <div className="border border-neutral-6 rounded-lg p-4">
          <h4 className="font-medium text-neutral-12 mb-2">
            5. Provide Data Tables
          </h4>
          <p className="text-sm text-neutral-11">
            Always offer an accessible data table alternative for users who
            cannot perceive the visualization.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="border border-neutral-6 rounded-lg p-4">
          <span className="text-2xl font-bold text-neutral-12">4-5</span>
          <p className="text-xs text-neutral-10 mt-1">
            Max categories (colorblind-safe)
          </p>
        </div>
        <div className="border border-neutral-6 rounded-lg p-4">
          <span className="text-2xl font-bold text-neutral-12">3:1</span>
          <p className="text-xs text-neutral-10 mt-1">
            Min contrast for graphics
          </p>
        </div>
        <div className="border border-neutral-6 rounded-lg p-4">
          <span className="text-2xl font-bold text-neutral-12">2+</span>
          <p className="text-xs text-neutral-10 mt-1">
            Encodings per data point
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
  title: "Design System/Data Visualization Palettes",
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "ColorBrewer palettes and chart color configurations for accessible data visualization. All palettes are selected for WCAG compliance and colorblind safety.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Categorical: Story = {
  render: () => <CategoricalPalettes />,
  parameters: {
    docs: {
      description: {
        story:
          "Categorical palettes for discrete data without inherent ordering.",
      },
    },
  },
};

export const Sequential: Story = {
  render: () => <SequentialPalettes />,
  parameters: {
    docs: {
      description: {
        story: "Sequential palettes for ordered or continuous data.",
      },
    },
  },
};

export const Diverging: Story = {
  render: () => <DivergingPalettes />,
  parameters: {
    docs: {
      description: {
        story: "Diverging palettes for data with a meaningful midpoint.",
      },
    },
  },
};

export const NodeTypes: Story = {
  render: () => <NodeTypeColors />,
  parameters: {
    docs: {
      description: {
        story: "LangGraph node type colors with pattern accessibility.",
      },
    },
  },
};

export const VegaTheme: Story = {
  render: () => <VegaLiteTheme />,
  parameters: {
    docs: {
      description: {
        story: "Default Vega-Lite theme configuration for Agent Studio charts.",
      },
    },
  },
};

export const Accessibility: Story = {
  render: () => <AccessibilityGuidelines />,
  parameters: {
    docs: {
      description: {
        story: "Guidelines for creating accessible data visualizations.",
      },
    },
  },
};
