/**
 * UnifiedMessageList Storybook Stories
 *
 * Showcases the UnifiedMessageList component in various states
 * including streaming, ratings, traces, and full-featured mode.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { UnifiedMessageList } from "./UnifiedMessageList";
import type { ChatMessage } from "../types/session";

// =============================================================================
// Sample Data
// =============================================================================

const SAMPLE_MESSAGES: ChatMessage[] = [
  {
    id: "1",
    role: "user",
    content: "Hello! Can you help me understand how React hooks work?",
    timestamp: Date.now() - 120000,
  },
  {
    id: "2",
    role: "assistant",
    content:
      "Hi! I'd be happy to help you understand React hooks.\n\n## What are React Hooks?\n\nHooks are functions that let you use state and other React features without writing a class component. They were introduced in React 16.8.\n\n### Common Hooks:\n\n1. **useState** - Adds state to functional components\n2. **useEffect** - Handles side effects\n3. **useContext** - Accesses context values\n4. **useRef** - Creates mutable references\n\nWould you like me to explain any specific hook in detail?",
    timestamp: Date.now() - 60000,
    agentMetadata: {
      confidence: 0.92,
      executionTrace: {
        traceId: "trace-abc-123",
        steps: [
          { name: "parse_input", status: "completed", duration: 50 },
          { name: "retrieve_context", status: "completed", duration: 120 },
          { name: "generate_response", status: "completed", duration: 200 },
        ],
      },
    },
    usage: { promptTokens: 45, completionTokens: 180, totalTokens: 225 },
    sources: [
      {
        title: "React Documentation",
        url: "https://react.dev/reference/react/hooks",
      },
      { title: "React Hooks Guide", url: "https://react.dev/learn" },
    ],
  },
  {
    id: "3",
    role: "user",
    content: "Can you explain useState in more detail with an example?",
    timestamp: Date.now() - 30000,
  },
  {
    id: "4",
    role: "assistant",
    content:
      "## useState Hook\n\nThe `useState` hook lets you add state to functional components.\n\n```typescript\nimport { useState } from 'react';\n\nfunction Counter() {\n  const [count, setCount] = useState(0);\n\n  return (\n    <button onClick={() => setCount(count + 1)}>\n      Count: {count}\n    </button>\n  );\n}\n```\n\n### Key Points:\n\n- **Initial value**: Pass the initial state to `useState(initialValue)`\n- **Returns array**: `[currentState, setterFunction]`\n- **Updates trigger re-render**: Calling the setter causes a re-render",
    timestamp: Date.now(),
    agentMetadata: {
      confidence: 0.95,
    },
    usage: { promptTokens: 60, completionTokens: 150, totalTokens: 210 },
  },
];

const STREAMING_MESSAGE: ChatMessage = {
  id: "streaming-message",
  role: "assistant",
  content: "I'm currently generating a response about useEffect...",
  timestamp: Date.now(),
  isStreaming: true,
};

const MESSAGE_WITH_THINKING: ChatMessage = {
  id: "thinking-msg",
  role: "assistant",
  content: "Based on my analysis, the best approach would be...",
  timestamp: Date.now(),
  thinkingContent:
    "Let me think about this step by step:\n\n1. First, I need to understand the user's question about React hooks.\n2. They specifically asked about useState.\n3. I should provide a clear explanation with code examples.\n4. I'll include the key concepts: initial value, destructuring, and re-rendering.",
  thinkingTokens: 450,
  modelName: "claude-opus-4.5",
  agentMetadata: {
    confidence: 0.94,
  },
};

// =============================================================================
// Meta
// =============================================================================

const meta: Meta<typeof UnifiedMessageList> = {
  title: "Conversation/UnifiedMessageList",
  component: UnifiedMessageList,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  decorators: [
    (Story) => (
      <div className="h-[600px] border border-neutral-6 rounded-lg overflow-hidden">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof UnifiedMessageList>;

// =============================================================================
// Stories
// =============================================================================

export const Default: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
  },
};

export const Empty: Story = {
  args: {
    messages: [],
    showEmptyState: true,
  },
};

export const Loading: Story = {
  args: {
    messages: SAMPLE_MESSAGES.slice(0, 2),
    isLoading: true,
  },
};

export const Streaming: Story = {
  args: {
    messages: [...SAMPLE_MESSAGES, STREAMING_MESSAGE],
    isStreaming: true,
  },
};

export const StreamingEmpty: Story = {
  args: {
    messages: [SAMPLE_MESSAGES[0], { ...STREAMING_MESSAGE, content: "" }],
    isStreaming: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Shows typing indicator when streaming starts but no content yet",
      },
    },
  },
};

export const WithAvatars: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    showAvatars: true,
    userInitials: "JD",
  },
};

export const WithTokenUsage: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    showTokenUsage: true,
    modelProvider: "openai",
    showCost: true,
  },
};

export const WithRatings: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    showRating: true,
    messageRatings: { "2": "up" },
    onRateMessage: (id, rating) => console.log("Rate:", id, rating),
    onRatingFeedback: (id, feedback) => console.log("Feedback:", id, feedback),
  },
};

export const WithAgentTraces: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    showAgentTraces: true,
    enableTraceAI: true,
  },
};

export const WithThinkingTrace: Story = {
  args: {
    messages: [SAMPLE_MESSAGES[0], MESSAGE_WITH_THINKING],
  },
};

export const WithHallucinationReporting: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    enableHallucinationReporting: true,
    onReportHallucination: (report) => console.log("Report:", report),
  },
};

export const ScrolledUp: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    isScrolledUp: true,
    onScrollToBottom: () => console.log("Scroll to bottom"),
  },
};

export const WithFollowUpSuggestions: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    followUpSuggestions: [
      { id: "1", text: "Tell me about useEffect", category: "hooks" },
      { id: "2", text: "How do I use useContext?", category: "hooks" },
      { id: "3", text: "What about custom hooks?", category: "advanced" },
    ],
    onSuggestionSelect: (suggestion) => console.log("Selected:", suggestion),
  },
};

export const FullFeatured: Story = {
  args: {
    messages: SAMPLE_MESSAGES,
    showAvatars: true,
    showTokenUsage: true,
    showAgentTraces: true,
    showRating: true,
    enableInteractiveArtifacts: true,
    enableHallucinationReporting: true,
    enableTraceAI: true,
    modelProvider: "anthropic",
    showCost: true,
    messageRatings: { "2": "up" },
    userInitials: "JD",
    followUpSuggestions: [
      { id: "1", text: "Tell me more", category: "general" },
    ],
    onRateMessage: (id, rating) => console.log("Rate:", id, rating),
    onRatingFeedback: (id, feedback) => console.log("Feedback:", id, feedback),
    onReportHallucination: (report) => console.log("Report:", report),
    onSuggestionSelect: (suggestion) => console.log("Selected:", suggestion),
  },
  parameters: {
    docs: {
      description: {
        story: "All features enabled for comprehensive demonstration",
      },
    },
  },
};
