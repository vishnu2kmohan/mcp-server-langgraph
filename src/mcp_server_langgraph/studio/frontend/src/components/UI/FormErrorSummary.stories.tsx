import type { Meta, StoryObj } from "@storybook/react-vite";
import { FormErrorSummary } from "./FormErrorSummary";

const meta: Meta<typeof FormErrorSummary> = {
  title: "UI/FormErrorSummary",
  component: FormErrorSummary,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
};

export default meta;
type Story = StoryObj<typeof FormErrorSummary>;

export const Default: Story = {
  args: {
    errors: {
      email: "Invalid email address",
      password: "Password must be at least 8 characters",
    },
  },
};

export const SingleError: Story = {
  args: {
    errors: {
      name: "Name is required",
    },
  },
};

export const ManyErrors: Story = {
  args: {
    errors: {
      firstName: "First name is required",
      lastName: "Last name is required",
      email: "Invalid email format",
      password: "Password must be at least 8 characters",
      confirmPassword: "Passwords do not match",
    },
    heading: "Please correct the following issues:",
  },
};

export const NoErrors: Story = {
  args: {
    errors: {},
  },
};
