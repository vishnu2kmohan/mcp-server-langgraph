#!/usr/bin/env npx tsx
/**
 * Batch Story Generator for UI Components
 *
 * Generates basic Storybook stories for components without them.
 * Run: npx tsx scripts/generate-stories.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UI_DIR = path.join(__dirname, '../src/components/UI');

// Components that already have stories
const EXISTING_STORIES = new Set([
  'Badge', 'Button', 'Card', 'Checkbox', 'Dialog',
  'Input', 'Select', 'Skeleton', 'Textarea', 'Toggle'
]);

// Skip non-component files
const SKIP_FILES = new Set(['index']);

// Component-specific story templates
const STORY_TEMPLATES: Record<string, (name: string) => string> = {
  SearchInput: () => `/**
 * SearchInput Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SearchInput } from "./SearchInput";

const meta: Meta<typeof SearchInput> = {
  title: "Design System/SearchInput",
  component: SearchInput,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "A debounced search input with clear button.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof SearchInput>;

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("");
    return <SearchInput value={value} onChange={setValue} placeholder="Search..." />;
  },
};

export const WithValue: Story = {
  render: function Render() {
    const [value, setValue] = useState("example search");
    return <SearchInput value={value} onChange={setValue} />;
  },
};
`,

  Pagination: () => `/**
 * Pagination Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { PagePagination } from "./Pagination";

const meta: Meta<typeof PagePagination> = {
  title: "Design System/Pagination",
  component: PagePagination,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Page-based pagination component.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof PagePagination>;

export const Default: Story = {
  render: function Render() {
    const [page, setPage] = useState(1);
    return <PagePagination currentPage={page} totalPages={10} onPageChange={setPage} />;
  },
};

export const ManyPages: Story = {
  render: function Render() {
    const [page, setPage] = useState(50);
    return <PagePagination currentPage={page} totalPages={100} onPageChange={setPage} />;
  },
};
`,

  CursorPagination: () => `/**
 * CursorPagination Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { CursorPagination } from "./CursorPagination";

const meta: Meta<typeof CursorPagination> = {
  title: "Design System/CursorPagination",
  component: CursorPagination,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Cursor-based pagination for infinite lists.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof CursorPagination>;

export const Default: Story = {
  args: {
    hasNext: true,
    hasPrevious: true,
    onNext: () => console.log("Next"),
    onPrevious: () => console.log("Previous"),
  },
};

export const FirstPage: Story = {
  args: {
    hasNext: true,
    hasPrevious: false,
    onNext: () => console.log("Next"),
    onPrevious: () => console.log("Previous"),
  },
};
`,

  ErrorState: () => `/**
 * ErrorState Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ErrorState } from "./ErrorState";

const meta: Meta<typeof ErrorState> = {
  title: "Design System/ErrorState",
  component: ErrorState,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Standardized error display component.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ErrorState>;

export const Default: Story = {
  args: {
    title: "Something went wrong",
    message: "An unexpected error occurred. Please try again.",
  },
};

export const WithRetry: Story = {
  args: {
    title: "Failed to load data",
    message: "Unable to fetch the requested data.",
    onRetry: () => console.log("Retry clicked"),
    retryLabel: "Try Again",
  },
};
`,

  ConfirmDialog: () => `/**
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
          onConfirm={() => { console.log("Confirmed"); setOpen(false); }}
          title="Delete item?"
          message="This action cannot be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          variant="danger"
        />
      </>
    );
  },
};
`,

  StatusBadge: () => `/**
 * StatusBadge Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { StatusBadge } from "./StatusBadge";

const meta: Meta<typeof StatusBadge> = {
  title: "Design System/StatusBadge",
  component: StatusBadge,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Semantic status badges with design system colors.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StatusBadge>;

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <StatusBadge status="success">Success</StatusBadge>
      <StatusBadge status="warning">Warning</StatusBadge>
      <StatusBadge status="error">Error</StatusBadge>
      <StatusBadge status="info">Info</StatusBadge>
      <StatusBadge status="neutral">Neutral</StatusBadge>
    </div>
  ),
};
`,

  RiskBadge: () => `/**
 * RiskBadge Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { RiskBadge } from "./RiskBadge";

const meta: Meta<typeof RiskBadge> = {
  title: "Design System/RiskBadge",
  component: RiskBadge,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Risk level display with semantic colors.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof RiskBadge>;

export const AllLevels: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <RiskBadge level="critical" />
      <RiskBadge level="high" />
      <RiskBadge level="medium" />
      <RiskBadge level="low" />
      <RiskBadge level="none" />
    </div>
  ),
};
`,

  ConfidenceIndicator: () => `/**
 * ConfidenceIndicator Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

const meta: Meta<typeof ConfidenceIndicator> = {
  title: "Design System/ConfidenceIndicator",
  component: ConfidenceIndicator,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "AI confidence score display.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ConfidenceIndicator>;

export const AllLevels: Story = {
  render: () => (
    <div className="space-y-2">
      <ConfidenceIndicator value={0.95} label="High confidence" />
      <ConfidenceIndicator value={0.75} label="Medium confidence" />
      <ConfidenceIndicator value={0.45} label="Low confidence" />
    </div>
  ),
};
`,

  SortDropdown: () => `/**
 * SortDropdown Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SortDropdown, type SortOption, type SortOrder } from "./SortDropdown";

const meta: Meta<typeof SortDropdown> = {
  title: "Design System/SortDropdown",
  component: SortDropdown,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Sort field and order dropdown.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof SortDropdown>;

const options: SortOption[] = [
  { value: "name", label: "Name" },
  { value: "date", label: "Date" },
  { value: "size", label: "Size" },
];

export const Default: Story = {
  render: function Render() {
    const [field, setField] = useState("name");
    const [order, setOrder] = useState<SortOrder>("asc");
    return (
      <SortDropdown
        options={options}
        value={field}
        order={order}
        onValueChange={setField}
        onOrderChange={setOrder}
      />
    );
  },
};
`,

  StatusFilter: () => `/**
 * StatusFilter Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { StatusFilter, type StatusOption } from "./StatusFilter";

const meta: Meta<typeof StatusFilter> = {
  title: "Design System/StatusFilter",
  component: StatusFilter,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Status dropdown filter.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StatusFilter>;

const options: StatusOption[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
];

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("all");
    return <StatusFilter options={options} value={value} onChange={setValue} />;
  },
};
`,

  FilterChips: () => `/**
 * FilterChips Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { FilterChips, type FilterOption } from "./FilterChips";

const meta: Meta<typeof FilterChips> = {
  title: "Design System/FilterChips",
  component: FilterChips,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Clickable filter chips for enum filtering.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof FilterChips>;

const options: FilterOption[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
];

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("all");
    return <FilterChips options={options} value={value} onChange={setValue} />;
  },
};

export const MultiSelect: Story = {
  render: function Render() {
    const [values, setValues] = useState<string[]>(["active"]);
    return (
      <FilterChips
        options={options}
        value={values}
        onChange={(v) => setValues(Array.isArray(v) ? v : [v])}
        multiple
      />
    );
  },
};
`,

  Tooltip: () => `/**
 * Tooltip Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Tooltip } from "./Tooltip";
import { Button } from "./Button";

const meta: Meta<typeof Tooltip> = {
  title: "Design System/Tooltip",
  component: Tooltip,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tooltip for additional information on hover.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  render: () => (
    <div className="p-8">
      <Tooltip content="This is a tooltip">
        <Button>Hover me</Button>
      </Tooltip>
    </div>
  ),
};

export const Positions: Story = {
  render: () => (
    <div className="flex gap-4 p-8">
      <Tooltip content="Top tooltip" position="top">
        <Button>Top</Button>
      </Tooltip>
      <Tooltip content="Bottom tooltip" position="bottom">
        <Button>Bottom</Button>
      </Tooltip>
      <Tooltip content="Left tooltip" position="left">
        <Button>Left</Button>
      </Tooltip>
      <Tooltip content="Right tooltip" position="right">
        <Button>Right</Button>
      </Tooltip>
    </div>
  ),
};
`,

  OfflineBanner: () => `/**
 * OfflineBanner Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { OfflineBanner } from "./OfflineBanner";

const meta: Meta<typeof OfflineBanner> = {
  title: "Design System/OfflineBanner",
  component: OfflineBanner,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "PWA offline indicator banner.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof OfflineBanner>;

export const Default: Story = {
  render: () => <OfflineBanner />,
};
`,

  TierUsageBar: () => `/**
 * TierUsageBar Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { TierUsageBar } from "./TierUsageBar";

const meta: Meta<typeof TierUsageBar> = {
  title: "Design System/TierUsageBar",
  component: TierUsageBar,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tier-based usage indicator bar.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof TierUsageBar>;

export const AllLevels: Story = {
  render: () => (
    <div className="space-y-4 max-w-md">
      <TierUsageBar used={25} limit={100} label="Storage" />
      <TierUsageBar used={75} limit={100} label="API Calls" />
      <TierUsageBar used={95} limit={100} label="Bandwidth" />
    </div>
  ),
};
`,

  UpgradePrompt: () => `/**
 * UpgradePrompt Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { UpgradePrompt } from "./UpgradePrompt";

const meta: Meta<typeof UpgradePrompt> = {
  title: "Design System/UpgradePrompt",
  component: UpgradePrompt,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tier upgrade call-to-action prompt.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof UpgradePrompt>;

export const Default: Story = {
  args: {
    currentTier: "free",
    targetTier: "pro",
    onUpgrade: () => console.log("Upgrade clicked"),
  },
};
`,

  InlineEdit: () => `/**
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
`,

  ContextMenu: () => `/**
 * ContextMenu Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ContextMenu } from "./ContextMenu";

const meta: Meta<typeof ContextMenu> = {
  title: "Design System/ContextMenu",
  component: ContextMenu,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Right-click context menu.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ContextMenu>;

export const Default: Story = {
  render: () => (
    <div className="p-8">
      <p className="text-neutral-500">Right-click on the area below:</p>
      <ContextMenu
        items={[
          { label: "Edit", onClick: () => console.log("Edit") },
          { label: "Delete", onClick: () => console.log("Delete") },
          { label: "Copy", onClick: () => console.log("Copy") },
        ]}
      >
        <div className="w-64 h-32 border-2 border-dashed border-neutral-300 rounded-lg flex items-center justify-center">
          Right-click here
        </div>
      </ContextMenu>
    </div>
  ),
};
`,

  BulkActionBar: () => `/**
 * BulkActionBar Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { BulkActionBar } from "./BulkActionBar";

const meta: Meta<typeof BulkActionBar> = {
  title: "Design System/BulkActionBar",
  component: BulkActionBar,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Bulk action toolbar for multi-select operations.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof BulkActionBar>;

export const Default: Story = {
  args: {
    selectedCount: 5,
    onClear: () => console.log("Clear selection"),
    actions: [
      { label: "Delete", onClick: () => console.log("Delete"), variant: "danger" },
      { label: "Archive", onClick: () => console.log("Archive") },
    ],
  },
};
`,
};

// Generic story template for components without specific templates
function genericStoryTemplate(name: string): string {
  return `/**
 * ${name} Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ${name} } from "./${name}";

const meta: Meta<typeof ${name}> = {
  title: "Design System/${name}",
  component: ${name},
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "${name} component.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ${name}>;

export const Default: Story = {
  args: {},
};
`;
}

function main() {
  const files = fs.readdirSync(UI_DIR);
  const components = files
    .filter(f => f.endsWith('.tsx'))
    .filter(f => !f.includes('.test.'))
    .filter(f => !f.includes('.stories.'))
    .map(f => f.replace('.tsx', ''))
    .filter(name => !SKIP_FILES.has(name))
    .filter(name => !EXISTING_STORIES.has(name));

  console.log(`Found ${components.length} components without stories:`);
  console.log(components.join(', '));
  console.log('');

  let created = 0;
  for (const name of components) {
    const storyPath = path.join(UI_DIR, `${name}.stories.tsx`);

    // Skip if story already exists
    if (fs.existsSync(storyPath)) {
      console.log(`⏭️  ${name}.stories.tsx already exists`);
      continue;
    }

    // Use specific template or generic one
    const template = STORY_TEMPLATES[name];
    const content = template ? template(name) : genericStoryTemplate(name);

    fs.writeFileSync(storyPath, content);
    console.log(`✅ Created ${name}.stories.tsx`);
    created++;
  }

  console.log(`\n✨ Created ${created} new story files`);
}

main();
