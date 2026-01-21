/**
 * SourceCitations Component Stories
 *
 * Storybook stories for the source citation display in message bubbles.
 * Showcases web search results, knowledge base references, and deduplication.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import type { SourceCitation } from "../../types/session";
import { SourceCitations } from "./SourceCitations";

// =============================================================================
// Storybook Configuration
// =============================================================================

const meta: Meta<typeof SourceCitations> = {
  title: "Chat/SourceCitations",
  component: SourceCitations,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Displays source citations from web search results and knowledge base references. Shown below assistant messages when sources are available. Supports deduplication by domain and relevance-based sorting.",
      },
    },
  },
  argTypes: {
    sources: {
      control: "object",
      description: "Array of source citations to display",
    },
    maxVisible: {
      control: { type: "number", min: 1, max: 20 },
      description: "Maximum number of sources to show before '+N more'",
    },
  },
};

export default meta;
type Story = StoryObj<typeof SourceCitations>;

// =============================================================================
// Mock Data
// =============================================================================

const webSearchSources: SourceCitation[] = [
  {
    title: "Python Documentation",
    url: "https://docs.python.org/3/tutorial",
    snippet: "The Python Tutorial — Python 3.13 documentation",
  },
  {
    title: "Real Python",
    url: "https://realpython.com/python-basics/",
    snippet: "Python Basics – Real Python tutorials for beginners",
  },
  {
    title: "Stack Overflow",
    url: "https://stackoverflow.com/questions/tagged/python",
    snippet: "Python questions on Stack Overflow",
  },
];

const kbSources: SourceCitation[] = [
  {
    title: "API Reference",
    url: "/kb/docs/api-reference.md",
    snippet: "Complete API documentation for the service",
    relevance_score: 0.95,
  },
  {
    title: "Getting Started Guide",
    url: "/kb/docs/getting-started.md",
    snippet: "Step-by-step guide for new users",
    relevance_score: 0.82,
  },
];

const mixedSources: SourceCitation[] = [
  ...webSearchSources.slice(0, 2),
  ...kbSources.slice(0, 1),
];

// =============================================================================
// Stories
// =============================================================================

export const Default: Story = {
  args: {
    sources: webSearchSources,
  },
  parameters: {
    docs: {
      description: {
        story: "Default display with three web search sources.",
      },
    },
  },
};

export const SingleSource: Story = {
  args: {
    sources: [webSearchSources[0]],
  },
  parameters: {
    docs: {
      description: {
        story: "Display with a single source.",
      },
    },
  },
};

export const ManySources: Story = {
  args: {
    sources: [
      ...webSearchSources,
      {
        title: "W3Schools Python",
        url: "https://www.w3schools.com/python/",
        snippet: "Python tutorials at W3Schools",
      },
      {
        title: "Python.org",
        url: "https://www.python.org/",
        snippet: "Official Python website",
      },
      {
        title: "GeeksforGeeks",
        url: "https://www.geeksforgeeks.org/python-programming-language/",
        snippet: "Python programming tutorials",
      },
      {
        title: "Codecademy",
        url: "https://www.codecademy.com/learn/learn-python-3",
        snippet: "Interactive Python course",
      },
    ],
    maxVisible: 5,
  },
  parameters: {
    docs: {
      description: {
        story: "Display with many sources, showing overflow indicator.",
      },
    },
  },
};

export const KnowledgeBaseSources: Story = {
  args: {
    sources: kbSources,
  },
  parameters: {
    docs: {
      description: {
        story: "Sources from knowledge base with relevance scores.",
      },
    },
  },
};

export const MixedSources: Story = {
  args: {
    sources: mixedSources,
  },
  parameters: {
    docs: {
      description: {
        story: "Mixed sources from both web search and knowledge base.",
      },
    },
  },
};

export const LongTitles: Story = {
  args: {
    sources: [
      {
        title:
          "A Very Long Title That Should Be Truncated in the Display Because It Exceeds the Maximum Width",
        url: "https://example.com/long-title",
        snippet: "This source has an unusually long title",
      },
      {
        title: "Short",
        url: "https://example.com/short",
      },
    ],
  },
  parameters: {
    docs: {
      description: {
        story: "Demonstrates truncation of long source titles.",
      },
    },
  },
};

export const NoTitle: Story = {
  args: {
    sources: [
      {
        title: "",
        url: "https://docs.python.org/3/tutorial/index.html",
        snippet: "Source without a title - domain should be shown",
      },
    ],
  },
  parameters: {
    docs: {
      description: {
        story: "Source without a title falls back to displaying the domain.",
      },
    },
  },
};

export const Empty: Story = {
  args: {
    sources: [],
  },
  parameters: {
    docs: {
      description: {
        story: "Component renders nothing when sources array is empty.",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InMessageContext: Story = {
  render: () => (
    <div className="max-w-2xl p-4">
      <div className="flex gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-insight-2 text-insight-10">
          <span className="text-xs font-semibold">AI</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm leading-relaxed prose prose-sm dark:prose-invert">
            <p>
              Python 3.13 introduces several new features including improved
              error messages, a new garbage collector implementation, and
              enhanced typing support. The Python documentation provides
              comprehensive information about all these changes.
            </p>
          </div>
          <SourceCitations sources={webSearchSources} />
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Source citations displayed in context of an AI response.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <div className="flex gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-insight-a4 text-insight-9">
          <span className="text-xs font-semibold">AI</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm leading-relaxed text-neutral-12">
            <p>Here are the search results for your query.</p>
          </div>
          <SourceCitations sources={webSearchSources} />
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Source citations in dark mode context.",
      },
    },
  },
};

export const AccessibilityShowcase: Story = {
  render: () => (
    <div className="p-4 space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-11">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-11 list-disc list-inside space-y-1">
          <li>Navigation landmark with aria-label</li>
          <li>Each link has descriptive aria-label</li>
          <li>Focus ring for keyboard navigation</li>
          <li>Opens in new tab (indicated in aria-label)</li>
          <li>External link icon is aria-hidden</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-5">
        <SourceCitations sources={webSearchSources.slice(0, 2)} />
        <p className="mt-4 text-xs text-neutral-10">
          Try navigating with Tab key. Each source link is focusable.
        </p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Demonstrates accessibility features including keyboard navigation, ARIA labels, and focus management.",
      },
    },
  },
};

// =============================================================================
// Grouped and Sorted Stories
// =============================================================================

export const GroupedByType: Story = {
  args: {
    sources: mixedSources,
    groupByType: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Sources grouped by type (Web vs Knowledge Base) with separate sections and headers. Uses the `groupByType` prop.",
      },
    },
  },
};

export const GroupedManySourcesWithOverflow: Story = {
  args: {
    sources: [
      ...webSearchSources,
      {
        title: "W3Schools Python",
        url: "https://www.w3schools.com/python/",
        snippet: "Python tutorials at W3Schools",
      },
      {
        title: "Python.org",
        url: "https://www.python.org/",
        snippet: "Official Python website",
      },
      {
        title: "GeeksforGeeks",
        url: "https://www.geeksforgeeks.org/python/",
        snippet: "Python programming tutorials",
      },
      ...kbSources,
      {
        title: "Troubleshooting Guide",
        url: "/kb/docs/troubleshooting.md",
        snippet: "Common issues and solutions",
        relevance_score: 0.78,
      },
      {
        title: "FAQ",
        url: "/kb/docs/faq.md",
        snippet: "Frequently asked questions",
        relevance_score: 0.65,
      },
    ],
    groupByType: true,
    maxVisible: 3,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Grouped sources with overflow indicators in each group. Each group respects the `maxVisible` limit independently.",
      },
    },
  },
};

export const KBOnlySources: Story = {
  args: {
    sources: [
      {
        title: "API Reference",
        url: "/kb/docs/api-reference.md",
        snippet: "Complete API documentation for the service",
        relevance_score: 0.95,
      },
      {
        title: "Getting Started Guide",
        url: "/kb/docs/getting-started.md",
        snippet: "Step-by-step guide for new users",
        relevance_score: 0.82,
      },
      {
        title: "Configuration Options",
        url: "kb://docs/config.md",
        snippet: "All configuration settings explained",
        relevance_score: 0.75,
      },
      {
        title: "Deployment Guide",
        url: "/kb/docs/deployment.md",
        snippet: "How to deploy to production",
        relevance_score: 0.68,
      },
    ],
  },
  parameters: {
    docs: {
      description: {
        story:
          "Sources exclusively from the knowledge base. Each source displays a BookOpen icon instead of the external link icon.",
      },
    },
  },
};

export const RelevanceSorted: Story = {
  render: () => {
    // Import sortByRelevance for demonstration
    const unsortedSources: SourceCitation[] = [
      {
        title: "Low Relevance Result",
        url: "https://example.com/low",
        snippet: "Not very relevant content",
        relevance_score: 0.25,
      },
      {
        title: "High Relevance Result",
        url: "https://example.com/high",
        snippet: "Highly relevant content",
        relevance_score: 0.95,
      },
      {
        title: "Medium Relevance Result",
        url: "https://example.com/medium",
        snippet: "Somewhat relevant content",
        relevance_score: 0.6,
      },
      {
        title: "No Score Result",
        url: "https://example.com/noscore",
        snippet: "Content without relevance score",
      },
    ];

    // Sort by relevance (highest first, no-score at end)
    const sortedSources = [...unsortedSources].sort((a, b) => {
      const scoreA = a.relevance_score ?? 0;
      const scoreB = b.relevance_score ?? 0;
      return scoreB - scoreA;
    });

    return (
      <div className="p-4 space-y-6">
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-neutral-11">
            Unsorted (Original Order)
          </h3>
          <SourceCitations sources={unsortedSources} />
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-neutral-11">
            Sorted by Relevance Score
          </h3>
          <p className="text-xs text-neutral-10">
            High (0.95) → Medium (0.6) → Low (0.25) → No Score
          </p>
          <SourceCitations sources={sortedSources} />
        </div>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story:
          "Demonstrates sorting sources by relevance_score using the `sortByRelevance` utility. Sources without scores are placed at the end.",
      },
    },
  },
};
