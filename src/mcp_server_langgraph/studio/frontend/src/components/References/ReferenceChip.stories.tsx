/**
 * ReferenceChip Component Stories
 *
 * Storybook stories for the ReferenceChip component.
 * Showcases all reference types, statuses, and accessibility features.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { createContext, useContext, type ReactNode } from "react";
import { ReferenceChip } from "./ReferenceChip";
import type {
  ResolvedReference,
  ReferenceResolverContextValue,
} from "@/types/references";

/**
 * Create a mock context value for Storybook.
 */
const createMockContextValue = (
  refs: ResolvedReference[],
  isLoading = false,
): ReferenceResolverContextValue => {
  const resolvedRefs = new Map<string, ResolvedReference>();
  refs.forEach((ref) => {
    const key = `${ref.type}:${ref.qualifier}:${ref.id}`;
    resolvedRefs.set(key, ref);
  });

  return {
    resolvedRefs,
    isLoading,
    error: undefined,
    resolve: async () => {},
  };
};

/**
 * Mock context for Storybook (bypasses RTK Query).
 */
const MockReferenceResolverContext =
  createContext<ReferenceResolverContextValue>({
    resolvedRefs: new Map(),
    isLoading: false,
    error: undefined,
    resolve: async () => {},
  });

/**
 * Mock hook for stories.
 */
// eslint-disable-next-line storybook/prefer-pascal-case -- Hook naming convention
export const useReferenceResolver = () =>
  useContext(MockReferenceResolverContext);

/**
 * Mock provider for Storybook.
 */
const createMockProvider = (refs: ResolvedReference[], isLoading = false) => {
  const contextValue = createMockContextValue(refs, isLoading);

  return ({ children }: { children: ReactNode }) => (
    <MockReferenceResolverContext.Provider value={contextValue}>
      {children}
    </MockReferenceResolverContext.Provider>
  );
};

const meta: Meta<typeof ReferenceChip> = {
  title: "References/ReferenceChip",
  component: ReferenceChip,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Inline chip component for [[type:qualifier:id]] markdown references. Displays type-specific icons and colors, resolves via context, and shows tooltips on hover.",
      },
    },
  },
  argTypes: {
    type: {
      control: "select",
      options: ["tool", "skill", "artifact", "memory", "plan"],
      description: "Reference type determines icon and color",
    },
    qualifier: {
      control: "text",
      description: "Server name for tools, or identifier for other types",
    },
    id: {
      control: "text",
      description: "Tool name, skill name, artifact ID, etc.",
    },
    label: {
      control: "text",
      description: "Optional custom display label",
    },
  },
};

export default meta;
type Story = StoryObj<typeof ReferenceChip>;

// =============================================================================
// Basic Reference Types
// =============================================================================

export const ToolReference: Story = {
  args: {
    type: "tool",
    qualifier: "filesystem",
    id: "read_file",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "tool",
          qualifier: "filesystem",
          id: "read_file",
          displayName: "Read File",
          description:
            "Reads a file from the filesystem and returns its contents",
          status: "valid",
          metadata: { connectionId: "conn-123" },
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story: "Tool reference with wrench icon and primary color scheme.",
      },
    },
  },
};

export const SkillReference: Story = {
  args: {
    type: "skill",
    qualifier: "code-review",
    id: "code-review",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "skill",
          qualifier: "code-review",
          id: "code-review",
          displayName: "Code Review",
          description: "Reviews code for quality, security, and best practices",
          status: "valid",
          metadata: { tags: ["quality", "review"], version: "1.2.0" },
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story: "Skill reference with sparkles icon and success color scheme.",
      },
    },
  },
};

export const ArtifactReference: Story = {
  args: {
    type: "artifact",
    qualifier: "chart-123",
    id: "chart-123",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "artifact",
          qualifier: "chart-123",
          id: "chart-123",
          displayName: "Sales Chart",
          description: "Monthly sales performance visualization",
          status: "valid",
          metadata: { contentType: "image/svg+xml" },
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story: "Artifact reference with file icon and neutral color scheme.",
      },
    },
  },
};

export const MemoryReference: Story = {
  args: {
    type: "memory",
    qualifier: "note-abc",
    id: "note-abc",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "memory",
          qualifier: "note-abc",
          id: "note-abc",
          displayName: "Meeting Notes",
          description: "Notes from the architecture planning session",
          status: "valid",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Memory reference with brain icon and info color scheme (Phase 4).",
      },
    },
  },
};

export const PlanReference: Story = {
  args: {
    type: "plan",
    qualifier: "plan-xyz",
    id: "plan-xyz",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "plan",
          qualifier: "plan-xyz",
          id: "plan-xyz",
          displayName: "Refactoring Plan",
          description: "Step-by-step plan for refactoring the auth module",
          status: "valid",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Plan reference with list icon and warning color scheme (Phase 4).",
      },
    },
  },
};

// =============================================================================
// Status States
// =============================================================================

export const ValidStatus: Story = {
  args: {
    type: "tool",
    qualifier: "fs",
    id: "read",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "tool",
          qualifier: "fs",
          id: "read",
          displayName: "Read",
          description: "File reading tool",
          status: "valid",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
};

export const NotFoundStatus: Story = {
  args: {
    type: "tool",
    qualifier: "nonexistent",
    id: "missing_tool",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "tool",
          qualifier: "nonexistent",
          id: "missing_tool",
          displayName: "missing_tool",
          status: "not_found",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Reference that could not be found. Shows reduced opacity and strikethrough.",
      },
    },
  },
};

export const UnauthorizedStatus: Story = {
  args: {
    type: "artifact",
    qualifier: "secret-doc",
    id: "secret-doc",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "artifact",
          qualifier: "secret-doc",
          id: "secret-doc",
          displayName: "secret-doc",
          status: "unauthorized",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Reference the user is not authorized to access. Shows reduced opacity and cursor-not-allowed.",
      },
    },
  },
};

export const LoadingStatus: Story = {
  args: {
    type: "skill",
    qualifier: "pending",
    id: "pending",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([], true);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story: "Reference being resolved. Shows pulse animation.",
      },
    },
  },
};

// =============================================================================
// Custom Labels
// =============================================================================

export const WithCustomLabel: Story = {
  args: {
    type: "tool",
    qualifier: "filesystem",
    id: "read_file",
    label: "Read File Tool",
  },
  decorators: [
    (Story) => {
      const Provider = createMockProvider([
        {
          type: "tool",
          qualifier: "filesystem",
          id: "read_file",
          displayName: "read_file",
          description: "Reads a file from the filesystem",
          status: "valid",
        },
      ]);
      return (
        <Provider>
          <Story />
        </Provider>
      );
    },
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Reference with custom label overrides the resolved displayName.",
      },
    },
  },
};

// =============================================================================
// Showcase Stories
// =============================================================================

export const AllTypes: Story = {
  render: () => {
    const Provider = createMockProvider([
      {
        type: "tool",
        qualifier: "fs",
        id: "read",
        displayName: "Read File",
        description: "Reads files",
        status: "valid",
      },
      {
        type: "skill",
        qualifier: "analyze",
        id: "analyze",
        displayName: "Analyze",
        description: "Analyzes data",
        status: "valid",
      },
      {
        type: "artifact",
        qualifier: "chart",
        id: "chart",
        displayName: "Chart",
        description: "A visualization",
        status: "valid",
      },
      {
        type: "memory",
        qualifier: "note",
        id: "note",
        displayName: "Note",
        description: "A memory note",
        status: "valid",
      },
      {
        type: "plan",
        qualifier: "plan",
        id: "plan",
        displayName: "Plan",
        description: "An execution plan",
        status: "valid",
      },
    ]);

    return (
      <Provider>
        <div className="flex flex-wrap gap-2">
          <ReferenceChip type="tool" qualifier="fs" id="read" />
          <ReferenceChip type="skill" qualifier="analyze" id="analyze" />
          <ReferenceChip type="artifact" qualifier="chart" id="chart" />
          <ReferenceChip type="memory" qualifier="note" id="note" />
          <ReferenceChip type="plan" qualifier="plan" id="plan" />
        </div>
      </Provider>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "All reference types displayed together for comparison.",
      },
    },
  },
};

export const AllStatuses: Story = {
  render: () => {
    const Provider = createMockProvider([
      {
        type: "tool",
        qualifier: "a",
        id: "valid",
        displayName: "Valid",
        status: "valid",
      },
      {
        type: "tool",
        qualifier: "b",
        id: "not_found",
        displayName: "Not Found",
        status: "not_found",
      },
      {
        type: "tool",
        qualifier: "c",
        id: "unauthorized",
        displayName: "Unauthorized",
        status: "unauthorized",
      },
    ]);

    return (
      <Provider>
        <div className="flex flex-wrap gap-2 items-center">
          <ReferenceChip type="tool" qualifier="a" id="valid" />
          <ReferenceChip type="tool" qualifier="b" id="not_found" />
          <ReferenceChip type="tool" qualifier="c" id="unauthorized" />
        </div>
      </Provider>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Comparison of valid, not_found, and unauthorized statuses.",
      },
    },
  },
};

export const InlineWithText: Story = {
  render: () => {
    const Provider = createMockProvider([
      {
        type: "tool",
        qualifier: "fs",
        id: "read_file",
        displayName: "Read File",
        description: "Reads a file from the filesystem",
        status: "valid",
      },
      {
        type: "skill",
        qualifier: "code-review",
        id: "code-review",
        displayName: "Code Review",
        description: "Reviews code quality",
        status: "valid",
      },
    ]);

    return (
      <Provider>
        <p className="text-neutral-12">
          Use the <ReferenceChip type="tool" qualifier="fs" id="read_file" />{" "}
          tool to read the configuration, then apply{" "}
          <ReferenceChip
            type="skill"
            qualifier="code-review"
            id="code-review"
          />{" "}
          to check for issues.
        </p>
      </Provider>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Reference chips rendered inline with paragraph text.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => {
    const Provider = createMockProvider([
      {
        type: "tool",
        qualifier: "fs",
        id: "read",
        displayName: "Read File",
        status: "valid",
      },
      {
        type: "skill",
        qualifier: "analyze",
        id: "analyze",
        displayName: "Analyze",
        status: "valid",
      },
      {
        type: "artifact",
        qualifier: "chart",
        id: "chart",
        displayName: "Chart",
        status: "valid",
      },
    ]);

    return (
      <Provider>
        <div className="dark bg-neutral-2 p-6 rounded-lg">
          <div className="flex flex-wrap gap-2">
            <ReferenceChip type="tool" qualifier="fs" id="read" />
            <ReferenceChip type="skill" qualifier="analyze" id="analyze" />
            <ReferenceChip type="artifact" qualifier="chart" id="chart" />
          </div>
        </div>
      </Provider>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Reference chips in dark mode context.",
      },
    },
  },
};
