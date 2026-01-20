/**
 * Dialog Component Stories
 *
 * Interactive documentation for the Dialog component.
 * Showcases all size variants and footer configurations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Dialog } from "./Dialog";
import { Button } from "./Button";

const meta: Meta<typeof Dialog> = {
  title: "Design System/Dialog",
  component: Dialog,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Modal dialog component with accessible behavior, size variants, and optional footer.",
      },
    },
  },
  argTypes: {
    size: {
      control: "select",
      options: ["sm", "md", "lg", "xl", "2xl", "full"],
      description: "Dialog width",
    },
    open: {
      control: "boolean",
      description: "Whether the dialog is visible",
    },
    title: {
      control: "text",
      description: "Dialog title text",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Dialog>;

/**
 * Interactive dialog with open/close state
 */
function InteractiveDialog({
  size,
  hasFooter = true,
}: {
  size?: "sm" | "md" | "lg" | "xl" | "2xl" | "full";
  hasFooter?: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Open Dialog</Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Dialog Title"
        size={size}
        footer={
          hasFooter ? (
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setOpen(false)}>Confirm</Button>
            </>
          ) : undefined
        }
      >
        <p className="text-neutral-11">
          This is the dialog content. Click the backdrop or press Escape to
          close.
        </p>
      </Dialog>
    </>
  );
}

/**
 * Default medium-sized dialog with footer actions
 */
export const Default: Story = {
  render: () => <InteractiveDialog size="md" />,
};

/**
 * All size variants
 */
export const Sizes: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <InteractiveDialog size="sm" />
      <InteractiveDialog size="md" />
      <InteractiveDialog size="lg" />
      <InteractiveDialog size="xl" />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Dialog supports multiple size variants: sm, md, lg, xl, 2xl, and full.",
      },
    },
  },
};

/**
 * Dialog without footer
 */
export const NoFooter: Story = {
  render: () => <InteractiveDialog hasFooter={false} />,
  parameters: {
    docs: {
      description: {
        story: "Footer is optional and can be omitted for simpler dialogs.",
      },
    },
  },
};

/**
 * Dialog with long content (scrollable)
 */
export const LongContent: Story = {
  render: () => {
    const [open, setOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setOpen(true)}>Open Long Dialog</Button>
        <Dialog
          open={open}
          onClose={() => setOpen(false)}
          title="Terms and Conditions"
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Decline
              </Button>
              <Button onClick={() => setOpen(false)}>Accept</Button>
            </>
          }
        >
          <div className="space-y-4 text-neutral-11">
            {Array.from({ length: 10 }).map((_, i) => (
              <p key={i}>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do
                eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut
                enim ad minim veniam, quis nostrud exercitation ullamco laboris.
              </p>
            ))}
          </div>
        </Dialog>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog content scrolls when it exceeds the maximum height (90vh).",
      },
    },
  },
};

/**
 * Confirmation dialog pattern
 */
export const ConfirmationPattern: Story = {
  render: () => {
    const [open, setOpen] = useState(false);

    return (
      <>
        <Button variant="danger" onClick={() => setOpen(true)}>
          Delete Item
        </Button>
        <Dialog
          open={open}
          onClose={() => setOpen(false)}
          title="Confirm Deletion"
          size="sm"
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => setOpen(false)}>
                Delete
              </Button>
            </>
          }
        >
          <p className="text-neutral-11">
            Are you sure you want to delete this item? This action cannot be
            undone.
          </p>
        </Dialog>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Common pattern for destructive action confirmation.",
      },
    },
  },
};

/**
 * Form dialog pattern
 */
export const FormPattern: Story = {
  render: () => {
    const [open, setOpen] = useState(false);

    return (
      <>
        <Button onClick={() => setOpen(true)}>Add New Item</Button>
        <Dialog
          open={open}
          onClose={() => setOpen(false)}
          title="Add New Item"
          size="md"
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setOpen(false)}>Save</Button>
            </>
          }
        >
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-11 mb-1">
                Name
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-neutral-5 rounded-lg bg-neutral-1 text-neutral-12"
                placeholder="Enter name..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-11 mb-1">
                Description
              </label>
              <textarea
                rows={3}
                className="w-full px-3 py-2 border border-neutral-5 rounded-lg bg-neutral-1 text-neutral-12"
                placeholder="Enter description..."
              />
            </div>
          </form>
        </Dialog>
      </>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Common pattern for form-based dialogs.",
      },
    },
  },
};
