/**
 * Input Component Stories
 *
 * Storybook stories for the Input component.
 * Showcases all variants, sizes, states, and icon configurations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  Search,
  Mail,
  Lock,
  Eye,
  User,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { Input } from "./Input";

const meta: Meta<typeof Input> = {
  title: "Design System/Input",
  component: Input,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A consistent, accessible input component with multiple variants. Uses CVA for type-safe variant management.",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "error", "success"],
      description: "Visual variant of the input",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Size of the input",
    },
    disabled: {
      control: "boolean",
      description: "Disable the input",
    },
    fullWidth: {
      control: "boolean",
      description: "Make input take full width",
    },
    type: {
      control: "select",
      options: ["text", "email", "password", "number", "search", "tel", "url"],
      description: "HTML input type",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Input>;

// =============================================================================
// Basic Stories
// =============================================================================

export const Default: Story = {
  args: {
    placeholder: "Enter text...",
  },
};

export const WithValue: Story = {
  args: {
    defaultValue: "Hello, World!",
  },
};

export const Placeholder: Story = {
  args: {
    placeholder: "Enter your email address...",
  },
};

// =============================================================================
// Variants
// =============================================================================

export const DefaultVariant: Story = {
  args: {
    variant: "default",
    placeholder: "Default input",
  },
};

export const ErrorVariant: Story = {
  args: {
    variant: "error",
    placeholder: "Error input",
    defaultValue: "Invalid value",
  },
};

export const SuccessVariant: Story = {
  args: {
    variant: "success",
    placeholder: "Success input",
    defaultValue: "Valid value",
  },
};

// =============================================================================
// Sizes
// =============================================================================

export const Small: Story = {
  args: {
    size: "sm",
    placeholder: "Small input",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    placeholder: "Medium input",
  },
};

export const Large: Story = {
  args: {
    size: "lg",
    placeholder: "Large input",
  },
};

// =============================================================================
// States
// =============================================================================

export const Disabled: Story = {
  args: {
    disabled: true,
    placeholder: "Disabled input",
    defaultValue: "Cannot edit",
  },
};

export const ReadOnly: Story = {
  args: {
    readOnly: true,
    defaultValue: "Read-only value",
  },
};

export const Required: Story = {
  args: {
    required: true,
    placeholder: "Required field *",
  },
};

// =============================================================================
// With Icons
// =============================================================================

export const WithLeftIcon: Story = {
  args: {
    leftIcon: <Search className="h-4 w-4" />,
    placeholder: "Search...",
  },
};

export const WithRightIcon: Story = {
  args: {
    rightIcon: <Mail className="h-4 w-4" />,
    placeholder: "Email address",
  },
};

export const WithBothIcons: Story = {
  args: {
    leftIcon: <Lock className="h-4 w-4" />,
    rightIcon: <Eye className="h-4 w-4" />,
    placeholder: "Password",
    type: "password",
  },
};

// =============================================================================
// Input Types
// =============================================================================

export const EmailInput: Story = {
  args: {
    type: "email",
    leftIcon: <Mail className="h-4 w-4" />,
    placeholder: "you@example.com",
  },
};

export const PasswordInput: Story = {
  args: {
    type: "password",
    leftIcon: <Lock className="h-4 w-4" />,
    placeholder: "Enter password",
  },
};

export const NumberInput: Story = {
  args: {
    type: "number",
    placeholder: "0",
    min: 0,
    max: 100,
  },
};

export const SearchInput: Story = {
  args: {
    type: "search",
    leftIcon: <Search className="h-4 w-4" />,
    placeholder: "Search...",
  },
};

// =============================================================================
// Showcase Stories
// =============================================================================

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-80">
      <Input variant="default" placeholder="Default variant" />
      <Input variant="error" placeholder="Error variant" />
      <Input variant="success" placeholder="Success variant" />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All input variants displayed together for comparison.",
      },
    },
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-80">
      <Input size="sm" placeholder="Small" />
      <Input size="md" placeholder="Medium" />
      <Input size="lg" placeholder="Large" />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All input sizes displayed together for comparison.",
      },
    },
  },
};

export const FormExample: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-80">
      <div>
        <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
          Username
        </label>
        <Input leftIcon={<User className="h-4 w-4" />} placeholder="johndoe" />
      </div>
      <div>
        <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
          Email
        </label>
        <Input
          type="email"
          leftIcon={<Mail className="h-4 w-4" />}
          placeholder="you@example.com"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
          Password
        </label>
        <Input
          type="password"
          leftIcon={<Lock className="h-4 w-4" />}
          placeholder="Enter password"
        />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Example form using Input components with labels.",
      },
    },
  },
};

export const ValidationStates: Story = {
  render: () => (
    <div className="flex flex-col gap-4 w-80">
      <div>
        <Input variant="default" placeholder="Default state" />
      </div>
      <div>
        <Input
          variant="error"
          defaultValue="invalid@"
          rightIcon={<AlertCircle className="h-4 w-4 text-error-500" />}
        />
        <p className="text-xs text-error-500 mt-1">
          Please enter a valid email address
        </p>
      </div>
      <div>
        <Input
          variant="success"
          defaultValue="valid@example.com"
          rightIcon={<CheckCircle className="h-4 w-4 text-success-500" />}
        />
        <p className="text-xs text-success-500 mt-1">Email is valid</p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Input validation states with error and success messages.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-col gap-4 w-80">
        <Input variant="default" placeholder="Default in dark mode" />
        <Input variant="error" placeholder="Error in dark mode" />
        <Input variant="success" placeholder="Success in dark mode" />
        <Input
          leftIcon={<Search className="h-4 w-4" />}
          placeholder="With icon in dark mode"
        />
        <Input disabled placeholder="Disabled in dark mode" />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Input variants in dark mode context.",
      },
    },
  },
};
