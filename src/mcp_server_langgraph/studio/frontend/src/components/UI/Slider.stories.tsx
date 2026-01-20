/**
 * Slider Component Stories
 *
 * Storybook documentation for the Slider component.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Slider } from "./Slider";

const meta: Meta<typeof Slider> = {
  title: "Design System/Slider",
  component: Slider,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "A range slider component for selecting numeric values. Supports labels, value display, custom formatting, tick marks, and multiple sizes.",
      },
    },
  },
  argTypes: {
    value: {
      control: "number",
      description: "Current slider value",
    },
    min: {
      control: "number",
      description: "Minimum value (default: 0)",
    },
    max: {
      control: "number",
      description: "Maximum value (default: 100)",
    },
    step: {
      control: "number",
      description: "Step increment (default: 1)",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Slider size",
    },
    label: {
      control: "text",
      description: "Optional label text",
    },
    showValue: {
      control: "boolean",
      description: "Show current value display",
    },
    disabled: {
      control: "boolean",
      description: "Whether the slider is disabled",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Slider>;

/**
 * Default slider
 */
export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState(50);
    return <Slider value={value} onChange={setValue} />;
  },
};

/**
 * Slider with label
 */
export const WithLabel: Story = {
  render: function Render() {
    const [value, setValue] = useState(50);
    return <Slider value={value} onChange={setValue} label="Volume" />;
  },
};

/**
 * Slider with value display
 */
export const WithValueDisplay: Story = {
  render: function Render() {
    const [value, setValue] = useState(75);
    return (
      <Slider value={value} onChange={setValue} label="Brightness" showValue />
    );
  },
};

/**
 * Slider with custom value formatter
 */
export const WithFormatter: Story = {
  render: function Render() {
    const [value, setValue] = useState(0.5);
    return (
      <Slider
        value={value}
        onChange={setValue}
        min={0}
        max={1}
        step={0.01}
        label="Opacity"
        showValue
        formatValue={(v) => `${(v * 100).toFixed(0)}%`}
      />
    );
  },
};

/**
 * Temperature slider (0-1 range)
 */
export const Temperature: Story = {
  render: function Render() {
    const [value, setValue] = useState(0.7);
    return (
      <Slider
        value={value}
        onChange={setValue}
        min={0}
        max={1}
        step={0.1}
        label="Temperature"
        showValue
        formatValue={(v) => v.toFixed(1)}
        marks={[
          { value: 0, label: "Precise" },
          { value: 1, label: "Creative" },
        ]}
      />
    );
  },
};

/**
 * Slider with tick marks
 */
export const WithMarks: Story = {
  render: function Render() {
    const [value, setValue] = useState(50);
    return (
      <Slider
        value={value}
        onChange={setValue}
        label="Quality"
        showValue
        marks={[
          { value: 0, label: "Low" },
          { value: 50, label: "Medium" },
          { value: 100, label: "High" },
        ]}
      />
    );
  },
};

/**
 * Disabled slider
 */
export const Disabled: Story = {
  render: function Render() {
    return (
      <div className="space-y-4">
        <Slider
          value={30}
          onChange={() => {}}
          disabled
          label="Disabled slider"
          showValue
        />
        <Slider
          value={70}
          onChange={() => {}}
          disabled
          label="Disabled with marks"
          showValue
          marks={[
            { value: 0, label: "Min" },
            { value: 100, label: "Max" },
          ]}
        />
      </div>
    );
  },
};

/**
 * All sizes comparison
 */
export const Sizes: Story = {
  render: function Render() {
    const [sm, setSm] = useState(50);
    const [md, setMd] = useState(50);
    const [lg, setLg] = useState(50);
    return (
      <div className="space-y-6">
        <div>
          <span className="text-sm text-neutral-11 mb-2 block">
            Small
          </span>
          <Slider value={sm} onChange={setSm} size="sm" showValue />
        </div>
        <div>
          <span className="text-sm text-neutral-11 mb-2 block">
            Medium (default)
          </span>
          <Slider value={md} onChange={setMd} size="md" showValue />
        </div>
        <div>
          <span className="text-sm text-neutral-11 mb-2 block">
            Large
          </span>
          <Slider value={lg} onChange={setLg} size="lg" showValue />
        </div>
      </div>
    );
  },
};

/**
 * Model configuration example
 */
export const ModelConfigExample: Story = {
  render: () => {
    const [temperature, setTemperature] = useState(0.7);
    const [topP, setTopP] = useState(1.0);
    const [maxTokens, setMaxTokens] = useState(2048);

    return (
      <div className="max-w-md space-y-6 p-4 bg-neutral-1 rounded-lg border border-neutral-5">
        <h3 className="text-lg font-semibold text-neutral-12">
          Model Configuration
        </h3>
        <div className="space-y-4">
          <Slider
            value={temperature}
            onChange={setTemperature}
            min={0}
            max={2}
            step={0.1}
            label="Temperature"
            showValue
            formatValue={(v) => v.toFixed(1)}
            marks={[
              { value: 0, label: "Deterministic" },
              { value: 2, label: "Random" },
            ]}
          />
          <Slider
            value={topP}
            onChange={setTopP}
            min={0}
            max={1}
            step={0.05}
            label="Top P"
            showValue
            formatValue={(v) => v.toFixed(2)}
          />
          <Slider
            value={maxTokens}
            onChange={setMaxTokens}
            min={256}
            max={8192}
            step={256}
            label="Max Tokens"
            showValue
            formatValue={(v) => v.toLocaleString()}
          />
        </div>
      </div>
    );
  },
};

/**
 * Dark mode demonstration
 */
export const DarkMode: Story = {
  render: function Render() {
    const [value1, setValue1] = useState(30);
    const [value2, setValue2] = useState(70);
    return (
      <div className="dark bg-neutral-2 p-6 rounded-lg">
        <div className="space-y-4">
          <Slider
            value={value1}
            onChange={setValue1}
            label="Setting A"
            showValue
          />
          <Slider
            value={value2}
            onChange={setValue2}
            label="Setting B"
            showValue
            disabled
          />
        </div>
      </div>
    );
  },
};
