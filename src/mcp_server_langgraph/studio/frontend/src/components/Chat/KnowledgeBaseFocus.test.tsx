/**
 * KnowledgeBaseFocus Component Tests
 *
 * TDD: These tests are written FIRST to define the expected behavior
 * of the KnowledgeBaseFocus dropdown component.
 *
 * Design based on research:
 * - Perplexity's "Focus" mode dropdown pattern
 * - ChatGPT's pill-based controls in chat input
 *
 * Tests verify:
 * 1. Renders as a pill/button in collapsed state
 * 2. Shows dropdown options when clicked
 * 3. Options include: All, Knowledge Base, Web, None
 * 4. Fires onChange callback with selected value
 * 5. Shows current selection as label
 * 6. Disabled state when isProcessing
 * 7. Accessible keyboard navigation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KnowledgeBaseFocus, type KBFocusMode } from "./KnowledgeBaseFocus";

import { TestProvider } from "@/test-utils";

describe("KnowledgeBaseFocus", () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Rendering Tests
  // =========================================================================

  it("renders as a pill button in collapsed state", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );

    const button = screen.getByTestId("kb-focus-button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-haspopup", "listbox");
    expect(button).toHaveAttribute("aria-expanded", "false");
  });

  it("shows current selection as label", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="kb_only" onChange={mockOnChange} />
      </TestProvider>,
    );

    expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
  });

  it("displays All label when value is all", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );

    expect(screen.getByText("All")).toBeInTheDocument();
  });

  it("displays Web label when value is web_only", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="web_only" onChange={mockOnChange} />
      </TestProvider>,
    );

    expect(screen.getByText("Web")).toBeInTheDocument();
  });

  it("displays None label when value is none", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="none" onChange={mockOnChange} />
      </TestProvider>,
    );

    expect(screen.getByText("None")).toBeInTheDocument();
  });

  // =========================================================================
  // Dropdown Interaction Tests
  // =========================================================================

  it("shows dropdown options when clicked", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);

    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    // Use getAllByRole since multiple options may match partial text
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(4);
    // Verify option descriptions are present (unique to options)
    expect(
      screen.getByText("Search web and knowledge base"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Search internal knowledge only"),
    ).toBeInTheDocument();
    expect(screen.getByText("Search external web only")).toBeInTheDocument();
    expect(screen.getByText("No context injection")).toBeInTheDocument();
  });

  it("fires onChange callback with selected value", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);

    // Find the "Knowledge Base" option by its exact text within an option
    const options = screen.getAllByRole("option");
    const kbOption = options.find((opt) =>
      opt.textContent?.includes("Search internal knowledge only"),
    );
    expect(kbOption).toBeDefined();
    await user.click(kbOption!);

    expect(mockOnChange).toHaveBeenCalledWith("kb_only");
  });

  it("closes dropdown after selection", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);

    // Find the "Knowledge Base" option by its description
    const options = screen.getAllByRole("option");
    const kbOption = options.find((opt) =>
      opt.textContent?.includes("Search internal knowledge only"),
    );
    await user.click(kbOption!);

    await waitFor(() => {
      expect(button).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("closes dropdown when clicking outside", async () => {
    render(
      <TestProvider>
        <div>
          <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
          <button data-testid="outside-button">Outside</button>
        </div>
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");

    await user.click(screen.getByTestId("outside-button"));

    await waitFor(() => {
      expect(button).toHaveAttribute("aria-expanded", "false");
    });
  });

  // =========================================================================
  // Disabled State Tests
  // =========================================================================

  it("is disabled when isProcessing is true", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="all"
          onChange={mockOnChange}
          disabled={true}
        />
      </TestProvider>,
    );

    const button = screen.getByTestId("kb-focus-button");
    expect(button).toBeDisabled();
  });

  it("does not open dropdown when disabled", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="all"
          onChange={mockOnChange}
          disabled={true}
        />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);

    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  // =========================================================================
  // Accessibility Tests
  // =========================================================================

  it("supports keyboard navigation with arrow keys", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    button.focus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("listbox")).toBeInTheDocument();

    // Navigate down with arrow key
    await user.keyboard("{ArrowDown}");

    // Press Enter to select
    await user.keyboard("{Enter}");

    expect(mockOnChange).toHaveBeenCalled();
  });

  it("closes dropdown on Escape key", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );
    const user = userEvent.setup();

    const button = screen.getByTestId("kb-focus-button");
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(button).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("has proper ARIA labels", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus value="all" onChange={mockOnChange} />
      </TestProvider>,
    );

    const button = screen.getByTestId("kb-focus-button");
    expect(button).toHaveAttribute("aria-label");
    expect(button.getAttribute("aria-label")).toMatch(/source/i);
  });

  // =========================================================================
  // Status Indicator Tests
  // =========================================================================

  it("shows status indicator when kbStatus is provided", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="kb_only"
          onChange={mockOnChange}
          kbStatus="ready"
        />
      </TestProvider>,
    );

    const indicator = screen.getByTestId("kb-status-indicator");
    expect(indicator).toBeInTheDocument();
    expect(indicator).toHaveClass("bg-success-9");
  });

  it("shows yellow indicator when kbStatus is misconfigured", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="kb_only"
          onChange={mockOnChange}
          kbStatus="misconfigured"
        />
      </TestProvider>,
    );

    const indicator = screen.getByTestId("kb-status-indicator");
    expect(indicator).toHaveClass("bg-warning-9");
  });

  it("shows gray indicator when kbStatus is unavailable", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="kb_only"
          onChange={mockOnChange}
          kbStatus="unavailable"
        />
      </TestProvider>,
    );

    const indicator = screen.getByTestId("kb-status-indicator");
    expect(indicator).toHaveClass("bg-neutral-4");
  });

  it("shows tooltip with config guidance when misconfigured", async () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="kb_only"
          onChange={mockOnChange}
          kbStatus="misconfigured"
          kbStatusMessage="Missing QDRANT_URL configuration"
        />
      </TestProvider>,
    );

    const indicator = screen.getByTestId("kb-status-indicator");
    expect(indicator).toHaveAttribute(
      "title",
      "Missing QDRANT_URL configuration",
    );
  });

  // =========================================================================
  // Compact Mode Tests
  // =========================================================================

  it("renders in compact mode with icon only", () => {
    render(
      <TestProvider>
        <KnowledgeBaseFocus
          value="all"
          onChange={mockOnChange}
          compact={true}
        />
      </TestProvider>,
    );

    const button = screen.getByTestId("kb-focus-button");
    // In compact mode, should show icon but not full text
    expect(button).toBeInTheDocument();
    // Should have a smaller size class or icon-only display
    expect(button).toHaveClass("p-2");
  });
});

describe("KBFocusMode type", () => {
  it("has correct values", () => {
    // Type checking - these should all be valid KBFocusMode values
    const modes: KBFocusMode[] = ["all", "kb_only", "web_only", "none"];
    expect(modes).toHaveLength(4);
  });
});
