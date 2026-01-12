/**
 * Card Component Stories
 *
 * Storybook stories for the Card component and its subcomponents.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./Card";
import { Button } from "./Button";

const meta: Meta<typeof Card> = {
  title: "Design System/Card",
  component: Card,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A flexible card component with composable subcomponents. Uses CVA for type-safe variant management.",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "elevated", "ghost"],
      description: "Visual variant of the card",
    },
    padding: {
      control: "select",
      options: ["none", "sm", "md", "lg"],
      description: "Padding size",
    },
    interactive: {
      control: "boolean",
      description: "Whether the card is interactive (hoverable)",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    children: "Card content goes here",
    className: "w-80",
  },
};

export const Elevated: Story = {
  args: {
    variant: "elevated",
    children: "Elevated card with shadow",
    className: "w-80",
  },
};

export const Ghost: Story = {
  args: {
    variant: "ghost",
    children: "Ghost card without border",
    className: "w-80",
  },
};

export const Interactive: Story = {
  args: {
    interactive: true,
    children: "Click me! I'm interactive",
    className: "w-80",
  },
};

export const WithComposition: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
      </CardHeader>
      <CardContent>
        This is the main content of the card. It can contain any content you
        need.
      </CardContent>
      <CardFooter>
        <Button variant="ghost" size="sm">
          Cancel
        </Button>
        <Button size="sm">Save</Button>
      </CardFooter>
    </Card>
  ),
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <Card variant="default" className="w-80">
        <CardContent>Default variant</CardContent>
      </Card>
      <Card variant="elevated" className="w-80">
        <CardContent>Elevated variant</CardContent>
      </Card>
      <Card variant="ghost" className="w-80">
        <CardContent>Ghost variant</CardContent>
      </Card>
    </div>
  ),
};

export const AllPaddings: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <Card padding="none" className="w-80">
        <div className="p-2 bg-neutral-100">No padding (content adds own)</div>
      </Card>
      <Card padding="sm" className="w-80">
        Small padding
      </Card>
      <Card padding="md" className="w-80">
        Medium padding (default)
      </Card>
      <Card padding="lg" className="w-80">
        Large padding
      </Card>
    </div>
  ),
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-col gap-4">
        <Card variant="default" className="w-80">
          <CardHeader>
            <CardTitle>Dark Mode Card</CardTitle>
          </CardHeader>
          <CardContent>Content in dark mode</CardContent>
        </Card>
        <Card variant="elevated" className="w-80">
          <CardContent>Elevated in dark mode</CardContent>
        </Card>
      </div>
    </div>
  ),
};
