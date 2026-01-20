/**
 * ChatInputForm Component Stories
 *
 * Storybook stories for the complete chat input form with Slack-style design.
 * Integrates AttachmentMenu, AttachmentPreviews, and RichTextInput.
 *
 * Note: Model selection is now handled by HeaderModelSelector in the session header.
 * @see HeaderModelSelector.stories.tsx for model selector stories.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { ChatInputForm, type ModelOption } from "./ChatInputForm";
import type { UploadFile } from "../../hooks/useFileUpload";

// Create mock File objects for stories
const createMockFile = (name: string, type: string, size: number): File => {
  const blob = new Blob([], { type });
  Object.defineProperty(blob, "size", { value: size });
  return new File([blob], name, { type, lastModified: Date.now() });
};

// Helper to create UploadFile with default complete status
const createUploadFile = (
  id: string,
  name: string,
  type: string,
  size: number,
  progress: number = 100,
  status: UploadFile["status"] = "complete"
): UploadFile => ({
  id,
  file: createMockFile(name, type, size),
  status,
  progress,
});

const SAMPLE_MODELS: ModelOption[] = [
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "Google", supportsThinking: true },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "Google", supportsThinking: true },
  { id: "claude-sonnet-4-5", name: "Claude 4.5 Sonnet", provider: "Anthropic", supportsThinking: true },
  { id: "claude-opus-4-5", name: "Claude 4.5 Opus", provider: "Anthropic", supportsThinking: true },
  { id: "gpt-5.1-instant", name: "GPT-5.1 Instant", provider: "OpenAI" },
  { id: "gpt-5.1-thinking", name: "GPT-5.1 Thinking", provider: "OpenAI", supportsThinking: true },
];

const SAMPLE_SLASH_COMMANDS = [
  { name: "help", description: "Show available commands", category: "general" as const },
  { name: "clear", description: "Clear conversation", category: "general" as const },
  { name: "copy", description: "Copy last response", category: "general" as const },
  { name: "export", description: "Export conversation", category: "general" as const },
];

const SAMPLE_MENTION_OPTIONS = [
  { type: "model" as const, value: "claude-4.5", label: "Claude 4.5" },
  { type: "file" as const, value: "README.md", label: "README.md" },
  { type: "user" as const, value: "alice", label: "Alice" },
];

const SAMPLE_UPLOAD_FILES: UploadFile[] = [
  createUploadFile("1", "document.pdf", "application/pdf", 102400),
  createUploadFile("2", "image.png", "image/png", 51200),
];

const SAMPLE_FETCHED_URLS = [
  { url: "https://example.com/article", title: "Example Article", content: "..." },
];

// Default drag handlers (no-op for stories)
const defaultDragHandlers = {
  onDragEnter: () => {},
  onDragLeave: () => {},
  onDragOver: (e: React.DragEvent) => e.preventDefault(),
  onDrop: () => {},
};

const meta: Meta<typeof ChatInputForm> = {
  title: "Chat/ChatInputForm",
  component: ChatInputForm,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Complete Slack-style chat input form. Integrates model selector, attachment menu, file previews, rich text input with formatting, voice input, and reasoning effort controls.",
      },
    },
  },
  argTypes: {
    input: { control: "text" },
    isProcessing: { control: "boolean" },
    isStreaming: { control: "boolean" },
    isListening: { control: "boolean" },
    isVoiceSupported: { control: "boolean" },
    isUploading: { control: "boolean" },
    isDragging: { control: "boolean" },
    showModelSelector: { control: "boolean" },
    enableRichTextMode: { control: "boolean" },
    submitOnEnter: { control: "boolean" },
    modelSupportsThinking: { control: "boolean" },
    enableThinking: { control: "boolean" },
    showKBFocus: { control: "boolean" },
    enableUrlFetch: { control: "boolean" },
    enableInlineSuggestions: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof ChatInputForm>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    input: "", onInputChange: (v) => console.log("Input:", v),
    onSubmit: () => console.log("Submit"),
    isProcessing: false,
    isListening: false,
    isVoiceSupported: true,
    voiceError: null,
    onStartListening: () => console.log("Start listening"),
    onStopListening: () => console.log("Stop listening"),
    uploadFiles: [],
    isUploading: false,
    isDragging: false,
    fileError: null,
    onSelectFiles: (files) => console.log("Files:", files),
    onRemoveFile: (id) => console.log("Remove:", id),
    dragHandlers: defaultDragHandlers,
    enableRichTextMode: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Default state with rich text mode enabled. Clean, minimal interface.",
      },
    },
  },
};

export const WithModelSelector: Story = {
  args: {
    ...Default.args,
    showModelSelector: true,
    selectedModel: "claude-sonnet-4-5",
    availableModels: SAMPLE_MODELS,
    onModelChange: (id) => console.log("Model:", id),
    recentModels: ["gemini-2.5-flash"],
    enableModelSearch: true,
  },
  parameters: {
    docs: {
      description: {
        story: "With model selector pill shown above the input.",
      },
    },
  },
};

export const WithAttachments: Story = {
  args: {
    ...Default.args,
    uploadFiles: SAMPLE_UPLOAD_FILES,
    fetchedUrls: SAMPLE_FETCHED_URLS,
    enableUrlFetch: true,
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
  },
  parameters: {
    docs: {
      description: {
        story: "With file and URL attachments displayed.",
      },
    },
  },
};

export const Processing: Story = {
  args: {
    ...Default.args,
    input: "Tell me about quantum computing",
    isProcessing: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Processing state - input disabled, spinner shown.",
      },
    },
  },
};

export const Streaming: Story = {
  args: {
    ...Default.args,
    input: "", isProcessing: true,
    isStreaming: true,
    onStopStreaming: () => console.log("Stop streaming"),
  },
  parameters: {
    docs: {
      description: {
        story: "Streaming state - stop button shown instead of send.",
      },
    },
  },
};

// =============================================================================
// Voice Input
// =============================================================================

export const VoiceListening: Story = {
  args: {
    ...Default.args,
    isListening: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Voice input active - microphone recording.",
      },
    },
  },
};

export const VoiceNotSupported: Story = {
  args: {
    ...Default.args,
    isVoiceSupported: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Voice input not supported - microphone hidden.",
      },
    },
  },
};

export const VoiceError: Story = {
  args: {
    ...Default.args,
    voiceError: "Microphone access denied",
  },
  parameters: {
    docs: {
      description: {
        story: "Voice input error state.",
      },
    },
  },
};

// =============================================================================
// Thinking / Reasoning
// =============================================================================

export const WithThinkingModel: Story = {
  args: {
    ...Default.args,
    showModelSelector: true,
    selectedModel: "claude-opus-4-5",
    availableModels: SAMPLE_MODELS,
    modelSupportsThinking: true,
    enableThinking: true,
    reasoningEffort: "medium",
    onReasoningEffortChange: (level) => console.log("Reasoning:", level),
    onEnableThinkingChange: (enabled) => console.log("Thinking:", enabled),
  },
  parameters: {
    docs: {
      description: {
        story: "With a thinking model selected - reasoning effort selector shown.",
      },
    },
  },
};

// =============================================================================
// Slash Commands
// =============================================================================

export const WithSlashCommands: Story = {
  args: {
    ...Default.args,
    input: "/",
    slashCommands: SAMPLE_SLASH_COMMANDS,
    onSlashCommandSelect: (cmd) => console.log("Command:", cmd),
  },
  parameters: {
    docs: {
      description: {
        story: "Type / to see slash command menu.",
      },
    },
  },
};

// =============================================================================
// KB Focus
// =============================================================================

export const WithKBFocus: Story = {
  args: {
    ...Default.args,
    showKBFocus: true,
    kbFocusValue: "all",
    kbStatus: "ready",
    onKBFocusChange: (mode) => console.log("KB Focus:", mode),
  },
  parameters: {
    docs: {
      description: {
        story: "With Knowledge Base Focus option in the + menu.",
      },
    },
  },
};

// =============================================================================
// Inline Suggestions
// =============================================================================

export const WithInlineSuggestion: Story = {
  args: {
    ...Default.args,
    input: "How do I ",
    enableInlineSuggestions: true,
    inlineSuggestion: "implement authentication?",
    onAcceptSuggestion: (s) => console.log("Accept:", s),
    onDismissSuggestion: () => console.log("Dismiss"),
  },
  parameters: {
    docs: {
      description: {
        story: "With inline AI suggestion (ghost text). Press Tab to accept.",
      },
    },
  },
};

// =============================================================================
// Drag and Drop
// =============================================================================

export const DragOver: Story = {
  args: {
    ...Default.args,
    isDragging: true,
  },
  parameters: {
    docs: {
      description: {
        story: "File drag over state - drop zone highlighted.",
      },
    },
  },
};

export const Uploading: Story = {
  args: {
    ...Default.args,
    isUploading: true,
    uploadFiles: [
      createUploadFile("1", "large-file.zip", "application/zip", 10485760, 45, "uploading"),
    ],
  },
  parameters: {
    docs: {
      description: {
        story: "File uploading state with progress.",
      },
    },
  },
};

// =============================================================================
// Rich Text Mode
// =============================================================================

export const RichTextMode: Story = {
  args: {
    ...Default.args,
    enableRichTextMode: true,
    mentionOptions: SAMPLE_MENTION_OPTIONS,
    richTextMaxLength: 1000,
  },
  parameters: {
    docs: {
      description: {
        story: "Rich text mode with formatting toolbar, mentions, and character limit.",
      },
    },
  },
};

export const PlainTextMode: Story = {
  args: {
    ...Default.args,
    enableRichTextMode: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Plain text mode (legacy) - simple textarea without formatting.",
      },
    },
  },
};

// =============================================================================
// Submit Modes
// =============================================================================

export const SubmitOnEnter: Story = {
  args: {
    ...Default.args,
    enableRichTextMode: true,
    submitOnEnter: true,
  },
  parameters: {
    docs: {
      description: {
        story: "ChatGPT-style: Enter submits, Shift+Enter for newline.",
      },
    },
  },
};

export const SubmitOnCtrlEnter: Story = {
  args: {
    ...Default.args,
    enableRichTextMode: true,
    submitOnEnter: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Legacy-style: Ctrl+Enter submits, Enter for newline.",
      },
    },
  },
};

// =============================================================================
// Interactive Stories
// =============================================================================

export const Interactive: Story = {
  render: function InteractiveStory() {
    const [input, setInput] = useState("");
    const [isProcessing, setIsProcessing] = useState(false);
    const [files, setFiles] = useState<UploadFile[]>([]);
    const [selectedModel, setSelectedModel] = useState("claude-sonnet-4-5");

    const handleSubmit = () => {
      if (!input.trim()) return;
      setIsProcessing(true);
      console.log("Submitted:", input);
      setTimeout(() => {
        setInput("");
        setIsProcessing(false);
        setFiles([]);
      }, 1500);
    };

    const handleSelectFiles = (newFiles: File[]) => {
      const uploadFiles: UploadFile[] = newFiles.map((f, i) => ({
        id: `file-${Date.now()}-${i}`,
        file: f,
        status: "complete" as const,
        progress: 100,
      }));
      setFiles((prev) => [...prev, ...uploadFiles]);
    };

    return (
      <div className="w-full max-w-2xl mx-auto">
        <ChatInputForm
          input={input}
          onInputChange={setInput}
          onSubmit={handleSubmit}
          isProcessing={isProcessing}
          isListening={false}
          isVoiceSupported={true}
          voiceError={null}
          onStartListening={() => console.log("Start")}
          onStopListening={() => console.log("Stop")}
          uploadFiles={files}
          isUploading={false}
          isDragging={false}
          fileError={null}
          onSelectFiles={handleSelectFiles}
          onRemoveFile={(id) => setFiles((f) => f.filter((x) => x.id !== id))}
          dragHandlers={defaultDragHandlers}
          enableRichTextMode={true}
          showModelSelector={true}
          selectedModel={selectedModel}
          availableModels={SAMPLE_MODELS}
          onModelChange={setSelectedModel}
          modelSupportsThinking={selectedModel.includes("opus") || selectedModel.includes("thinking")}
          enableThinking={true}
          reasoningEffort="medium"
          onReasoningEffortChange={(l) => console.log("Reasoning:", l)}
          mentionOptions={SAMPLE_MENTION_OPTIONS}
          showKBFocus={true}
          kbFocusValue="all"
          kbStatus="ready"
          onKBFocusChange={(m) => console.log("KB:", m)}
        />
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Fully interactive story with state management. Type, attach files, change models.",
      },
    },
  },
};

// =============================================================================
// Full Featured
// =============================================================================

export const FullFeatured: Story = {
  args: {
    input: "", onInputChange: (v) => console.log("Input:", v),
    onSubmit: () => console.log("Submit"),
    isProcessing: false,
    isStreaming: false,
    isListening: false,
    isVoiceSupported: true,
    voiceError: null,
    onStartListening: () => console.log("Start"),
    onStopListening: () => console.log("Stop"),
    uploadFiles: SAMPLE_UPLOAD_FILES,
    isUploading: false,
    isDragging: false,
    fileError: null,
    onSelectFiles: (files) => console.log("Files:", files),
    onRemoveFile: (id) => console.log("Remove:", id),
    dragHandlers: defaultDragHandlers,
    // Rich text
    enableRichTextMode: true,
    submitOnEnter: true,
    mentionOptions: SAMPLE_MENTION_OPTIONS,
    richTextMaxLength: 2000,
    // Model selector
    showModelSelector: true,
    selectedModel: "claude-opus-4-5",
    availableModels: SAMPLE_MODELS,
    onModelChange: (id) => console.log("Model:", id),
    recentModels: ["gemini-2.5-flash", "gpt-5.1-thinking"],
    enableModelSearch: true,
    // Thinking
    modelSupportsThinking: true,
    enableThinking: true,
    reasoningEffort: "high",
    onReasoningEffortChange: (l) => console.log("Reasoning:", l),
    // KB Focus
    showKBFocus: true,
    kbFocusValue: "all",
    kbStatus: "ready",
    onKBFocusChange: (m) => console.log("KB:", m),
    // URL fetch
    enableUrlFetch: true,
    fetchedUrls: SAMPLE_FETCHED_URLS,
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
    // Slash commands
    slashCommands: SAMPLE_SLASH_COMMANDS,
    onSlashCommandSelect: (cmd) => console.log("Command:", cmd),
    // Inline suggestions
    enableInlineSuggestions: true,
  },
  parameters: {
    docs: {
      description: {
        story: "All features enabled: model selector, attachments, rich text, thinking, KB focus, slash commands.",
      },
    },
  },
};

// =============================================================================
// Dark Mode
// =============================================================================

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-8 rounded-lg">
      <div className="w-full max-w-2xl mx-auto">
        <ChatInputForm
          input="" onInputChange={(v) => console.log("Input:", v)}
          onSubmit={() => console.log("Submit")}
          isProcessing={false}
          isListening={false}
          isVoiceSupported={true}
          voiceError={null}
          onStartListening={() => {}}
          onStopListening={() => {}}
          uploadFiles={SAMPLE_UPLOAD_FILES.slice(0, 1)}
          isUploading={false}
          isDragging={false}
          fileError={null}
          onSelectFiles={() => {}}
          onRemoveFile={() => {}}
          dragHandlers={defaultDragHandlers}
          enableRichTextMode={true}
          showModelSelector={true}
          selectedModel="claude-sonnet-4-5"
          availableModels={SAMPLE_MODELS}
          modelSupportsThinking={true}
          enableThinking={true}
          showKBFocus={true}
          kbFocusValue="kb_only"
          kbStatus="ready"
        />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "ChatInputForm in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Accessibility
// =============================================================================

export const AccessibilityShowcase: Story = {
  render: () => (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div className="space-y-2 p-4 bg-neutral-2 rounded-lg">
        <h3 className="text-sm font-semibold text-neutral-11">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-11 list-disc list-inside space-y-1">
          <li>Full keyboard navigation through all controls</li>
          <li>ARIA labels on all interactive elements</li>
          <li>Focus management in dropdown menus</li>
          <li>Screen reader announcements for state changes</li>
          <li>Escape closes all dropdowns/menus</li>
          <li>Tab cycles through: + menu, Aa toggle, textarea, voice, reasoning, send</li>
          <li>Arrow keys navigate within menus</li>
        </ul>
      </div>
      <ChatInputForm
        input="" onInputChange={(v) => console.log("Input:", v)}
        onSubmit={() => console.log("Submit")}
        isProcessing={false}
        isListening={false}
        isVoiceSupported={true}
        voiceError={null}
        onStartListening={() => {}}
        onStopListening={() => {}}
        uploadFiles={[]}
        isUploading={false}
        isDragging={false}
        fileError={null}
        onSelectFiles={() => {}}
        onRemoveFile={() => {}}
        dragHandlers={defaultDragHandlers}
        enableRichTextMode={true}
        showModelSelector={true}
        selectedModel="claude-sonnet-4-5"
        availableModels={SAMPLE_MODELS}
        modelSupportsThinking={true}
        enableThinking={true}
        showKBFocus={true}
        kbStatus="ready"
        mentionOptions={SAMPLE_MENTION_OPTIONS}
      />
      <p className="text-xs text-neutral-10 text-center">
        Try Tab, Arrow keys, Enter, and Escape to navigate.
      </p>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Demonstrates accessibility features of the complete ChatInputForm.",
      },
    },
  },
};
