/**
 * WorkspacePresets Tests - Phase 2
 *
 * Tests for per-persona workspace layout presets.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { WorkspacePresets, type WorkspacePreset } from "./WorkspacePresets";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Data
// =============================================================================

const mockPresets: WorkspacePreset[] = [
  {
    id: "default",
    name: "Default Layout",
    description: "Standard chat + canvas layout",
    layout: {
      sessionNav: 20,
      conversation: 40,
      canvas: 40,
    },
    icon: "layout",
  },
  {
    id: "focus-chat",
    name: "Focus Chat",
    description: "Expanded conversation panel",
    layout: {
      sessionNav: 10,
      conversation: 65,
      canvas: 25,
    },
    icon: "message-square",
  },
  {
    id: "focus-canvas",
    name: "Focus Canvas",
    description: "Expanded canvas panel",
    layout: {
      sessionNav: 10,
      conversation: 25,
      canvas: 65,
    },
    icon: "code",
  },
  {
    id: "minimal",
    name: "Minimal",
    description: "Collapsed navigation",
    layout: {
      sessionNav: 0,
      conversation: 50,
      canvas: 50,
    },
    icon: "minimize",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("WorkspacePresets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render presets container", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("workspace-presets")).toBeInTheDocument();
    });

    it("should render all preset options", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByText("Default Layout")).toBeInTheDocument();
      expect(screen.getByText("Focus Chat")).toBeInTheDocument();
      expect(screen.getByText("Focus Canvas")).toBeInTheDocument();
      expect(screen.getByText("Minimal")).toBeInTheDocument();
    });

    it("should display preset descriptions", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(
        screen.getByText("Standard chat + canvas layout"),
      ).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should highlight current preset", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="focus-chat"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      const focusChatPreset = screen.getByTestId("preset-focus-chat");
      expect(focusChatPreset).toHaveClass("selected");
    });

    it("should call onApply when preset clicked", () => {
      const onApply = vi.fn();
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={onApply}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByText("Focus Canvas"));
      expect(onApply).toHaveBeenCalledWith(mockPresets[2]);
    });

    it("should not call onApply when clicking current preset", () => {
      const onApply = vi.fn();
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={onApply}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByText("Default Layout"));
      expect(onApply).not.toHaveBeenCalled();
    });
  });

  describe("Layout Preview", () => {
    it("should show layout preview on hover", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
            showPreview
          />
        </TestProvider>,
      );
      fireEvent.mouseEnter(screen.getByTestId("preset-focus-canvas"));
      expect(screen.getByTestId("layout-preview")).toBeInTheDocument();
    });

    it("should display layout percentages in preview", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
            showPreview
          />
        </TestProvider>,
      );
      fireEvent.mouseEnter(screen.getByTestId("preset-focus-canvas"));
      expect(screen.getByText("60%")).toBeInTheDocument(); // Canvas percentage
    });
  });

  describe("Grid vs List View", () => {
    it("should render as grid by default", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("workspace-presets")).toHaveClass("grid");
    });

    it("should render as list when variant is list", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
            variant="list"
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("workspace-presets")).toHaveClass("list");
    });
  });

  describe("Custom Presets", () => {
    it("should show save button when allowCustom is true", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
            allowCustom
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("save-custom-preset")).toBeInTheDocument();
    });

    it("should call onSaveCustom when save clicked", () => {
      const onSaveCustom = vi.fn();
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
            allowCustom
            onSaveCustom={onSaveCustom}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("save-custom-preset"));
      expect(onSaveCustom).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have radiogroup role", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("should have radio role for preset items", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getAllByRole("radio")).toHaveLength(4);
    });

    it("should indicate selected preset with aria-checked", () => {
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="focus-chat"
            onApply={() => {}}
          />
        </TestProvider>,
      );
      const focusChatPreset = screen.getByTestId("preset-focus-chat");
      expect(focusChatPreset).toHaveAttribute("aria-checked", "true");
    });
  });

  describe("Keyboard Navigation", () => {
    it("should navigate with arrow keys", () => {
      const onApply = vi.fn();
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={onApply}
          />
        </TestProvider>,
      );
      // Focus the first preset, navigate right, then press Enter to verify focus moved
      const firstPreset = screen.getByTestId("preset-default");
      firstPreset.focus();
      fireEvent.keyDown(firstPreset, { key: "ArrowRight" });
      fireEvent.keyDown(screen.getByTestId("preset-focus-chat"), {
        key: "Enter",
      });
      expect(onApply).toHaveBeenCalledWith(mockPresets[1]);
    });

    it("should select preset on Enter", () => {
      const onApply = vi.fn();
      render(
        <TestProvider>
          <WorkspacePresets
            presets={mockPresets}
            currentPreset="default"
            onApply={onApply}
          />
        </TestProvider>,
      );
      const focusChatPreset = screen.getByTestId("preset-focus-chat");
      focusChatPreset.focus();
      fireEvent.keyDown(focusChatPreset, { key: "Enter" });
      expect(onApply).toHaveBeenCalledWith(mockPresets[1]);
    });
  });
});
