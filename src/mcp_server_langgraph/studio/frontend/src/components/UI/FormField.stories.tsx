import type { Meta, StoryObj } from "@storybook/react-vite";
import { FormField } from "./FormField";
import { Input } from "./Input";

const meta: Meta<typeof FormField> = {
  title: "UI/FormField",
  component: FormField,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
};

export default meta;
type Story = StoryObj<typeof FormField>;

export const Default: Story = {
  args: {
    label: "Email",
    name: "email",
    children: <Input placeholder="Enter your email" />,
  },
};

export const WithHint: Story = {
  args: {
    label: "Password",
    name: "password",
    hint: "Must be at least 8 characters",
    children: <Input type="password" placeholder="Enter password" />,
  },
};

export const WithError: Story = {
  args: {
    label: "Email",
    name: "email",
    error: "Invalid email address",
    children: <Input placeholder="Enter your email" />,
  },
};

export const Required: Story = {
  args: {
    label: "Username",
    name: "username",
    required: true,
    children: <Input placeholder="Choose a username" />,
  },
};

export const RequiredWithError: Story = {
  args: {
    label: "Email",
    name: "email",
    required: true,
    error: "Email is required",
    children: <Input placeholder="Enter your email" />,
  },
};
