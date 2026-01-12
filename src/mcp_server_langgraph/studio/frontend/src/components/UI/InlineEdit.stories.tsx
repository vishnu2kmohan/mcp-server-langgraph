/**
 * InlineEdit Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { InlineEdit } from "./InlineEdit";

const meta: Meta<typeof InlineEdit> = {
  title: "Design System/InlineEdit",
  component: InlineEdit,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Inline editable text field.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof InlineEdit>;

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("Click to edit");
    return <InlineEdit value={value} onSave={setValue} />;
  },
};
