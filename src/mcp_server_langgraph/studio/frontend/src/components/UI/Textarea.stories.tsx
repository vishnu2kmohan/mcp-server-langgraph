/**
 * Textarea Component Stories
 *
 * Storybook stories for the Textarea component.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Textarea } from "./Textarea";

const meta: Meta<typeof Textarea> = {
  title: "Design System/Textarea",
  component: Textarea,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A consistent, accessible textarea component with multiple variants. Uses CVA for type-safe variant management.",
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
    resize: {
      control: "select",
      options: ["none", "vertical", "horizontal", "both"],
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
type Story = StoryObj<typeof Textarea>;

export const Default: Story = {
  args: {
    placeholder: "Enter your message...",
    className: "w-80",
  },
};

export const WithValue: Story = {
  args: {
    defaultValue:
      "This is some sample text content that spans multiple lines.\n\nIt can contain line breaks too.",
    className: "w-80",
  },
};

export const ErrorVariant: Story = {
  args: {
    variant: "error",
    defaultValue: "Invalid content",
    className: "w-80",
  },
};

export const SuccessVariant: Story = {
  args: {
    variant: "success",
    defaultValue: "Valid content",
    className: "w-80",
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
    defaultValue: "Cannot edit this",
    className: "w-80",
  },
};

export const NoResize: Story = {
  args: {
    resize: "none",
    placeholder: "This textarea cannot be resized",
    className: "w-80",
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-80">
      <Textarea size="sm" placeholder="Small" rows={2} />
      <Textarea size="md" placeholder="Medium" rows={2} />
      <Textarea size="lg" placeholder="Large" rows={2} />
    </div>
  ),
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <div className="flex flex-col gap-4 w-80">
        <Textarea placeholder="Default in dark mode" />
        <Textarea variant="error" placeholder="Error in dark mode" />
        <Textarea variant="success" placeholder="Success in dark mode" />
        <Textarea disabled placeholder="Disabled in dark mode" />
      </div>
    </div>
  ),
};
