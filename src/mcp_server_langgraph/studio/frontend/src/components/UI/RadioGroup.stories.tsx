/**
 * RadioGroup Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { RadioGroup, Radio } from "./RadioGroup";

const meta: Meta<typeof RadioGroup> = {
  title: "Design System/RadioGroup",
  component: RadioGroup,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "A radio group component with accessible controls. Supports labels, descriptions, and horizontal/vertical orientation.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof RadioGroup>;

/**
 * Default vertical radio group
 */
export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("option1");
    return (
      <RadioGroup name="default" value={value} onChange={setValue}>
        <Radio value="option1" label="Option 1" />
        <Radio value="option2" label="Option 2" />
        <Radio value="option3" label="Option 3" />
      </RadioGroup>
    );
  },
};

/**
 * With legend/label for the group
 */
export const WithLegend: Story = {
  render: function Render() {
    const [value, setValue] = useState("monthly");
    return (
      <RadioGroup
        name="billing"
        value={value}
        onChange={setValue}
        legend="Billing cycle"
      >
        <Radio value="monthly" label="Monthly" description="Pay each month" />
        <Radio
          value="yearly"
          label="Yearly"
          description="Pay once per year (save 20%)"
        />
      </RadioGroup>
    );
  },
};

/**
 * Horizontal orientation
 */
export const Horizontal: Story = {
  render: function Render() {
    const [value, setValue] = useState("sm");
    return (
      <RadioGroup
        name="size"
        value={value}
        onChange={setValue}
        orientation="horizontal"
        legend="Size"
      >
        <Radio value="sm" label="Small" />
        <Radio value="md" label="Medium" />
        <Radio value="lg" label="Large" />
        <Radio value="xl" label="Extra Large" />
      </RadioGroup>
    );
  },
};

/**
 * Disabled state
 */
export const Disabled: Story = {
  render: function Render() {
    const [value, setValue] = useState("option1");
    return (
      <div className="space-y-6">
        <RadioGroup
          name="disabled-group"
          value={value}
          onChange={setValue}
          disabled
        >
          <Radio value="option1" label="Option 1 (disabled group)" />
          <Radio value="option2" label="Option 2 (disabled group)" />
        </RadioGroup>

        <RadioGroup name="partial-disabled" value={value} onChange={setValue}>
          <Radio value="option1" label="Option 1 (enabled)" />
          <Radio value="option2" label="Option 2 (disabled)" disabled />
          <Radio value="option3" label="Option 3 (enabled)" />
        </RadioGroup>
      </div>
    );
  },
};

/**
 * All sizes comparison
 */
export const Sizes: Story = {
  render: function Render() {
    const [sm, setSm] = useState("a");
    const [md, setMd] = useState("a");
    const [lg, setLg] = useState("a");
    return (
      <div className="space-y-6">
        <RadioGroup
          name="size-sm"
          value={sm}
          onChange={setSm}
          size="sm"
          orientation="horizontal"
        >
          <Radio value="a" label="Small A" />
          <Radio value="b" label="Small B" />
        </RadioGroup>
        <RadioGroup
          name="size-md"
          value={md}
          onChange={setMd}
          size="md"
          orientation="horizontal"
        >
          <Radio value="a" label="Medium A" />
          <Radio value="b" label="Medium B" />
        </RadioGroup>
        <RadioGroup
          name="size-lg"
          value={lg}
          onChange={setLg}
          size="lg"
          orientation="horizontal"
        >
          <Radio value="a" label="Large A" />
          <Radio value="b" label="Large B" />
        </RadioGroup>
      </div>
    );
  },
};

/**
 * Rating variant - compact horizontal rating scale (e.g., surveys)
 */
export const RatingVariant: Story = {
  render: function Render() {
    const [rating, setRating] = useState("");
    return (
      <div className="space-y-4">
        <p className="text-sm text-neutral-11">
          How satisfied are you with our service?
        </p>
        <RadioGroup
          name="rating"
          value={rating}
          onChange={setRating}
          variant="rating"
        >
          <Radio value="1" label="1" />
          <Radio value="2" label="2" />
          <Radio value="3" label="3" />
          <Radio value="4" label="4" />
          <Radio value="5" label="5" />
        </RadioGroup>
        <p className="flex justify-between text-xs text-neutral-10">
          <span>Not satisfied</span>
          <span>Very satisfied</span>
        </p>
      </div>
    );
  },
};

/**
 * Card variant - bordered selection cards with descriptions
 */
export const CardVariant: Story = {
  render: function Render() {
    const [plan, setPlan] = useState("starter");
    const plans = [
      {
        value: "starter",
        label: "Starter",
        description: "Perfect for individuals",
      },
      { value: "pro", label: "Professional", description: "For growing teams" },
      {
        value: "enterprise",
        label: "Enterprise",
        description: "For large organizations",
      },
    ];
    return (
      <RadioGroup
        name="plan"
        value={plan}
        onChange={setPlan}
        legend="Select a plan"
        variant="card"
      >
        {plans.map((p) => (
          <Radio
            key={p.value}
            value={p.value}
            label={p.label}
            description={p.description}
          />
        ))}
      </RadioGroup>
    );
  },
};

/**
 * All variants comparison
 */
export const AllVariants: Story = {
  render: function Render() {
    const [defaultVal, setDefaultVal] = useState("a");
    const [cardVal, setCardVal] = useState("a");
    const [ratingVal, setRatingVal] = useState("3");
    return (
      <div className="space-y-8">
        <div>
          <h3 className="text-sm font-medium mb-2">Default Variant</h3>
          <RadioGroup
            name="variant-default"
            value={defaultVal}
            onChange={setDefaultVal}
          >
            <Radio value="a" label="Option A" description="Default styling" />
            <Radio
              value="b"
              label="Option B"
              description="Simple radio buttons"
            />
          </RadioGroup>
        </div>
        <div>
          <h3 className="text-sm font-medium mb-2">Card Variant</h3>
          <RadioGroup
            name="variant-card"
            value={cardVal}
            onChange={setCardVal}
            variant="card"
          >
            <Radio value="a" label="Option A" description="Card with border" />
            <Radio
              value="b"
              label="Option B"
              description="Highlights on selection"
            />
          </RadioGroup>
        </div>
        <div>
          <h3 className="text-sm font-medium mb-2">Rating Variant</h3>
          <RadioGroup
            name="variant-rating"
            value={ratingVal}
            onChange={setRatingVal}
            variant="rating"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <Radio key={n} value={String(n)} label={String(n)} />
            ))}
          </RadioGroup>
        </div>
      </div>
    );
  },
};
