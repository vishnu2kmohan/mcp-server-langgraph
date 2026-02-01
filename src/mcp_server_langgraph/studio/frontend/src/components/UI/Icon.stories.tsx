import type { Meta, StoryObj } from "@storybook/react-vite";
import { Icon } from "./Icon";
import {
  Download,
  CheckCircle,
  AlertTriangle,
  Settings,
  Trash2,
  Plus,
  Search,
} from "lucide-react";

const meta: Meta<typeof Icon> = {
  title: "UI/Icon",
  component: Icon,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
  },
  argTypes: {
    size: {
      control: "select",
      options: ["xs", "sm", "md", "lg", "xl", "2xl", "3xl"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Icon>;

export const Default: Story = {
  args: {
    icon: Download,
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-end gap-4">
      <Icon icon={Settings} size="xs" />
      <Icon icon={Settings} size="sm" />
      <Icon icon={Settings} size="md" />
      <Icon icon={Settings} size="lg" />
      <Icon icon={Settings} size="xl" />
      <Icon icon={Settings} size="2xl" />
      <Icon icon={Settings} size="3xl" />
    </div>
  ),
};

export const WithLabel: Story = {
  args: {
    icon: CheckCircle,
    "aria-label": "Success",
    className: "text-success-9",
  },
};

export const CommonIcons: Story = {
  render: () => (
    <div className="flex gap-4">
      <Icon icon={Plus} className="text-primary-9" />
      <Icon icon={Search} className="text-neutral-10" />
      <Icon icon={Settings} className="text-neutral-10" />
      <Icon icon={CheckCircle} className="text-success-9" />
      <Icon icon={AlertTriangle} className="text-warning-9" />
      <Icon icon={Trash2} className="text-error-9" />
    </div>
  ),
};
