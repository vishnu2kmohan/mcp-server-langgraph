import type { Meta, StoryObj } from "@storybook/react-vite";
import { SelectionCard } from "./SelectionCard";
import { Cloud, Server, Database, Sparkles } from "lucide-react";
import { useState } from "react";

const meta: Meta<typeof SelectionCard> = {
  title: "UI/SelectionCard",
  component: SelectionCard,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
};

export default meta;
type Story = StoryObj<typeof SelectionCard>;

export const Default: Story = {
  args: {
    title: "Cloud Storage",
    description: "Store your data securely in the cloud",
    icon: <Cloud className="w-5 h-5" />,
    onClick: () => console.log("clicked"),
  },
};

export const Selected: Story = {
  args: {
    title: "Cloud Storage",
    description: "Store your data securely in the cloud",
    icon: <Cloud className="w-5 h-5" />,
    selected: true,
    onClick: () => console.log("clicked"),
  },
};

export const WithBadge: Story = {
  args: {
    title: "AI-Powered",
    description: "Let AI optimize your workflow automatically",
    icon: <Sparkles className="w-5 h-5" />,
    badge: "Recommended",
    onClick: () => console.log("clicked"),
  },
};

export const SelectionGroup: Story = {
  render: function SelectionGroupExample() {
    const [selected, setSelected] = useState<string>("cloud");

    const options = [
      { id: "cloud", title: "Cloud", description: "Cloud-based storage", icon: <Cloud className="w-5 h-5" /> },
      { id: "server", title: "On-Premise", description: "Self-hosted server", icon: <Server className="w-5 h-5" /> },
      { id: "database", title: "Database", description: "Direct database connection", icon: <Database className="w-5 h-5" /> },
    ];

    return (
      <div className="grid grid-cols-3 gap-4">
        {options.map((option) => (
          <SelectionCard
            key={option.id}
            title={option.title}
            description={option.description}
            icon={option.icon}
            selected={selected === option.id}
            onClick={() => setSelected(option.id)}
          />
        ))}
      </div>
    );
  },
};
