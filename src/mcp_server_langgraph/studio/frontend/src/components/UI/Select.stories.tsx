/**
 * Select Component Stories
 *
 * Storybook stories for the Select component.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Select } from "./Select";

const meta: Meta<typeof Select> = {
  title: "Design System/Select",
  component: Select,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A consistent, accessible select component with multiple variants. Uses CVA for type-safe variant management.",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "error", "success"],
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
    disabled: {
      control: "boolean",
    },
    fullWidth: {
      control: "boolean",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Select>;

const defaultOptions = [
  { value: "1", label: "Option 1" },
  { value: "2", label: "Option 2" },
  { value: "3", label: "Option 3" },
];

export const Default: Story = {
  args: {
    options: defaultOptions,
    placeholder: "Select an option",
    className: "w-64",
  },
};

export const WithValue: Story = {
  args: {
    options: defaultOptions,
    value: "2",
    className: "w-64",
  },
};

export const ErrorVariant: Story = {
  args: {
    options: defaultOptions,
    variant: "error",
    placeholder: "Select an option",
    className: "w-64",
  },
};

export const SuccessVariant: Story = {
  args: {
    options: defaultOptions,
    variant: "success",
    value: "1",
    className: "w-64",
  },
};

export const Disabled: Story = {
  args: {
    options: defaultOptions,
    disabled: true,
    value: "1",
    className: "w-64",
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-64">
      <Select options={defaultOptions} size="sm" placeholder="Small" />
      <Select options={defaultOptions} size="md" placeholder="Medium" />
      <Select options={defaultOptions} size="lg" placeholder="Large" />
    </div>
  ),
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-col gap-4 w-64">
        <Select options={defaultOptions} placeholder="Default" />
        <Select options={defaultOptions} variant="error" placeholder="Error" />
        <Select options={defaultOptions} variant="success" value="1" />
        <Select options={defaultOptions} disabled value="2" />
      </div>
    </div>
  ),
};
