/**
 * ReferencePopover Component Stories
 *
 * Storybook stories for the ReferencePopover component.
 * Showcases all reference types, actions, and accessibility features.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { ReferencePopover } from "./ReferencePopover";
import type { ResolvedReference } from "@/types/references";

import { Button } from "@/components/UI";

const meta: Meta<typeof ReferencePopover> = {
  title: "References/ReferencePopover",
  component: ReferencePopover,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Popover component displaying detailed information about a reference. Shows description, metadata, copy button, and deep link navigation.",
      },
    },
  },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div className="relative p-8">
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ReferencePopover>;

// =============================================================================
// Test Fixtures
// =============================================================================

const toolReference: ResolvedReference = {
  type: "tool",
  qualifier: "filesystem",
  id: "read_file",
  displayName: "Read File Tool",
  description:
    "Reads a file from the filesystem and returns its contents. Supports various encodings and file types.",
  status: "valid",
  metadata: {
    connectionId: "conn-uuid-123",
    inputSchema: {
      path: { type: "string", description: "File path to read" },
      encoding: { type: "string", description: "Character encoding" },
    },
  },
};

const skillReference: ResolvedReference = {
  type: "skill",
  qualifier: "code-review",
  id: "code-review",
  displayName: "Code Review",
  description:
    "Analyzes code for quality, security vulnerabilities, and adherence to best practices.",
  status: "valid",
  metadata: {
    tags: ["quality", "security", "linting", "best-practices"],
    version: "2.1.0",
  },
};

const artifactReference: ResolvedReference = {
  type: "artifact",
  qualifier: "chart-monthly-sales",
  id: "chart-monthly-sales",
  displayName: "Monthly Sales Chart",
  description:
    "Interactive visualization of monthly sales performance by region.",
  status: "valid",
  metadata: {
    contentType: "image/svg+xml",
  },
};

const memoryReference: ResolvedReference = {
  type: "memory",
  qualifier: "note-architecture",
  id: "note-architecture",
  displayName: "Architecture Planning Notes",
  description:
    "Notes from the team discussion about microservices architecture migration strategy.",
  status: "valid",
  metadata: {
    category: "meetings",
    tags: ["architecture", "planning"],
  },
};

const planReference: ResolvedReference = {
  type: "plan",
  qualifier: "plan-auth-refactor",
  id: "plan-auth-refactor",
  displayName: "Authentication Refactoring Plan",
  description:
    "Step-by-step plan for migrating from session-based to JWT authentication.",
  status: "valid",
  metadata: {
    status: "approved",
    toolsNeeded: ["filesystem:read", "filesystem:write"],
  },
};

// =============================================================================
// Basic Reference Types
// =============================================================================

export const ToolPopover: Story = {
  args: {
    reference: toolReference,
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          'Tool reference popover showing description, parameter count, and "View in Connections" link.',
      },
    },
  },
};

export const SkillPopover: Story = {
  args: {
    reference: skillReference,
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          'Skill reference popover showing description, tags, and "View in Skills" link.',
      },
    },
  },
};

export const ArtifactPopover: Story = {
  args: {
    reference: artifactReference,
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          'Artifact reference popover showing description and "View in Artifacts" link.',
      },
    },
  },
};

export const MemoryPopover: Story = {
  args: {
    reference: memoryReference,
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "Memory note reference popover (Phase 4).",
      },
    },
  },
};

export const PlanPopover: Story = {
  args: {
    reference: planReference,
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "Execution plan reference popover (Phase 4).",
      },
    },
  },
};

// =============================================================================
// Status States
// =============================================================================

export const NotFoundReference: Story = {
  args: {
    reference: {
      type: "tool",
      qualifier: "missing-server",
      id: "nonexistent_tool",
      displayName: "nonexistent_tool",
      status: "not_found",
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Reference that could not be found. Deep link is hidden for invalid references.",
      },
    },
  },
};

export const UnauthorizedReference: Story = {
  args: {
    reference: {
      type: "artifact",
      qualifier: "secret-doc",
      id: "secret-doc",
      displayName: "Confidential Document",
      description: "You do not have permission to access this artifact.",
      status: "unauthorized",
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Reference the user is not authorized to access. Deep link is hidden.",
      },
    },
  },
};

// =============================================================================
// Edge Cases
// =============================================================================

export const NoDescription: Story = {
  args: {
    reference: {
      type: "tool",
      qualifier: "api",
      id: "call_endpoint",
      displayName: "Call Endpoint",
      status: "valid",
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Reference without a description - description section is hidden.",
      },
    },
  },
};

export const LongDescription: Story = {
  args: {
    reference: {
      type: "skill",
      qualifier: "comprehensive-analysis",
      id: "comprehensive-analysis",
      displayName: "Comprehensive Code Analysis",
      description:
        "This skill performs a thorough analysis of your codebase, examining code quality metrics, detecting potential bugs, identifying security vulnerabilities, checking for adherence to coding standards, measuring test coverage, and providing actionable recommendations for improvement. It integrates with various static analysis tools and produces detailed reports with prioritized findings.",
      status: "valid",
      metadata: {
        tags: ["analysis", "quality", "security", "testing", "metrics"],
      },
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "Reference with a long description that wraps naturally.",
      },
    },
  },
};

export const ManyTags: Story = {
  args: {
    reference: {
      type: "skill",
      qualifier: "full-stack",
      id: "full-stack",
      displayName: "Full Stack Developer",
      description: "A comprehensive skill for full-stack development tasks.",
      status: "valid",
      metadata: {
        tags: [
          "frontend",
          "backend",
          "database",
          "api",
          "testing",
          "deployment",
          "monitoring",
          "security",
        ],
      },
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "Skill reference with many tags displayed.",
      },
    },
  },
};

export const NoConnectionId: Story = {
  args: {
    reference: {
      type: "tool",
      qualifier: "server",
      id: "tool_name",
      displayName: "Tool Name",
      description: "A tool without connection ID metadata.",
      status: "valid",
      metadata: {},
    },
    isOpen: true,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Tool reference without connectionId - falls back to /connections URL.",
      },
    },
  },
};

// =============================================================================
// Interactive Stories
// =============================================================================

export const Interactive: Story = {
  render: () => {
    const [isOpen, setIsOpen] = useState(true);

    return (
      <div className="relative">
        <Button
          variant="primary"
          className="px-3 py-1.5 bg-primary-3 text-primary-11 rounded text-sm"
          type="button"
          onClick={() => setIsOpen(true)}
        >
          Show Popover
        </Button>
        <div className="absolute top-full left-0 mt-2">
          <ReferencePopover
            reference={toolReference}
            isOpen={isOpen}
            onClose={() => setIsOpen(false)}
          />
        </div>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story:
          "Interactive example with working open/close behavior. Click the button to show the popover, then click the X to close.",
      },
    },
  },
};

export const ClosedState: Story = {
  args: {
    reference: toolReference,
    isOpen: false,
    onClose: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "When isOpen is false, the component renders nothing.",
      },
    },
  },
};

// =============================================================================
// Dark Mode
// =============================================================================

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-1 p-6 rounded-lg">
      <ReferencePopover
        reference={toolReference}
        isOpen={true}
        onClose={() => {}}
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Reference popover in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Showcase
// =============================================================================

export const AllTypes: Story = {
  render: () => (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <h3 className="text-sm font-medium text-neutral-11 mb-2">Tool</h3>
        <ReferencePopover
          reference={toolReference}
          isOpen={true}
          onClose={() => {}}
        />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-11 mb-2">Skill</h3>
        <ReferencePopover
          reference={skillReference}
          isOpen={true}
          onClose={() => {}}
        />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-11 mb-2">Artifact</h3>
        <ReferencePopover
          reference={artifactReference}
          isOpen={true}
          onClose={() => {}}
        />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-11 mb-2">Memory</h3>
        <ReferencePopover
          reference={memoryReference}
          isOpen={true}
          onClose={() => {}}
        />
      </div>
    </div>
  ),
  parameters: {
    layout: "padded",
    docs: {
      description: {
        story: "All reference type popovers displayed together for comparison.",
      },
    },
  },
};
