/**
 * ConfirmDialog Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { ConfirmDialog } from "./ConfirmDialog";
import { Button } from "./Button";

const meta: Meta<typeof ConfirmDialog> = {
  title: "Design System/ConfirmDialog",
  component: ConfirmDialog,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Styled confirmation dialog replacing native confirm().",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ConfirmDialog>;

export const Default: Story = {
  render: function Render() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button onClick={() => setOpen(true)}>Delete Item</Button>
        <ConfirmDialog
          open={open}
          onClose={() => setOpen(false)}
          onConfirm={() => {
            console.log("Confirmed");
            setOpen(false);
          }}
          title="Delete item?"
          message="This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          isDestructive
        />
      </>
    );
  },
};

export const NonDestructive: Story = {
  render: function Render() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Archive Item
        </Button>
        <ConfirmDialog
          open={open}
          onClose={() => setOpen(false)}
          onConfirm={() => {
            console.log("Confirmed");
            setOpen(false);
          }}
          title="Archive item?"
          message="You can restore this item later from the archive."
          confirmText="Archive"
          cancelText="Cancel"
        />
      </>
    );
  },
};
