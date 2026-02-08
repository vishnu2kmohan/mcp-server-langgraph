/**
 * MermaidArtifact Tests
 *
 * TDD tests for the Mermaid diagram artifact component.
 * Tests cover:
 * - Rendering diagram code
 * - Copy functionality
 * - Open in mermaid.live
 * - Expandable view
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MermaidArtifact } from "./MermaidArtifact";

import { TestProvider } from "@/test-utils";

describe("MermaidArtifact", () => {
  const sampleDiagram = `graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E`;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render mermaid diagram code", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      expect(screen.getByText(/graph TD/)).toBeInTheDocument();
    });

    it("should display title when provided", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} title="Workflow Diagram" />
        </TestProvider>,
      );

      expect(screen.getByText("Workflow Diagram")).toBeInTheDocument();
    });

    it("should show Mermaid label when no title", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      expect(screen.getByText("Mermaid Diagram")).toBeInTheDocument();
    });
  });

  describe("Copy Functionality", () => {
    it("should have copy button", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      expect(screen.getByTitle("Copy code")).toBeInTheDocument();
    });

    it("should copy code to clipboard when clicked", async () => {
      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText: mockWriteText },
      });

      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      const copyButton = screen.getByTitle("Copy code");
      await act(async () => {
        fireEvent.click(copyButton);
      });

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith(sampleDiagram);
      });
    });
  });

  describe("Open in Mermaid.live", () => {
    it("should have open in mermaid.live button", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      expect(screen.getByTitle("Open in Mermaid Live")).toBeInTheDocument();
    });

    it("should open mermaid.live with encoded diagram", () => {
      const mockOpen = vi.fn();
      vi.stubGlobal("open", mockOpen);

      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );

      const openButton = screen.getByTitle("Open in Mermaid Live");
      fireEvent.click(openButton);

      expect(mockOpen).toHaveBeenCalled();
      const call = mockOpen.mock.calls[0][0] as string;
      expect(call).toContain("mermaid.live");
    });
  });

  describe("Expand/Collapse", () => {
    it("should have expand button when expandable is true", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} expandable />
        </TestProvider>,
      );

      expect(screen.getByTitle(/Expand|Collapse/i)).toBeInTheDocument();
    });

    it("should toggle expanded state when clicked", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} expandable />
        </TestProvider>,
      );

      const expandButton = screen.getByTitle(/Expand/i);
      fireEvent.click(expandButton);

      expect(screen.getByTitle(/Collapse/i)).toBeInTheDocument();
    });
  });

  describe("Different Diagram Types", () => {
    it("should render flowchart diagram", () => {
      const flowchart = `flowchart LR
    A --> B --> C`;
      render(
        <TestProvider>
          <MermaidArtifact code={flowchart} />
        </TestProvider>,
      );

      expect(screen.getByText(/flowchart LR/)).toBeInTheDocument();
    });

    it("should render sequence diagram", () => {
      const sequence = `sequenceDiagram
    Alice->>Bob: Hello Bob`;
      render(
        <TestProvider>
          <MermaidArtifact code={sequence} />
        </TestProvider>,
      );

      expect(screen.getByText(/sequenceDiagram/)).toBeInTheDocument();
    });

    it("should render class diagram", () => {
      const classDiagram = `classDiagram
    Animal <|-- Duck`;
      render(
        <TestProvider>
          <MermaidArtifact code={classDiagram} />
        </TestProvider>,
      );

      expect(screen.getByText(/classDiagram/)).toBeInTheDocument();
    });
  });

  describe("Theme", () => {
    it("should apply default theme", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} theme="default" />
        </TestProvider>,
      );

      const container = screen.getByTestId("mermaid-container");
      expect(container).toBeInTheDocument();
    });

    it("should apply dark theme", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} theme="dark" />
        </TestProvider>,
      );

      const container = screen.getByTestId("mermaid-container");
      expect(container).toHaveClass("dark");
    });
  });

  describe("ArtifactExporter Integration", () => {
    it("should show export menu when export button clicked", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should show PNG option in export menu", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /png/i }),
      ).toBeInTheDocument();
    });

    it("should show SVG option in export menu", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /svg/i }),
      ).toBeInTheDocument();
    });

    it("should show Code option in export menu for mermaid diagrams", () => {
      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /code/i }),
      ).toBeInTheDocument();
    });

    it("should trigger export when format selected", () => {
      // Mock URL methods in JSDOM environment
      const mockUrl = "blob:test";
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;

      URL.createObjectURL = vi.fn().mockReturnValue(mockUrl);
      URL.revokeObjectURL = vi.fn();

      render(
        <TestProvider>
          <MermaidArtifact code={sampleDiagram} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);

      const codeOption = screen.getByRole("menuitem", { name: /code/i });
      fireEvent.click(codeOption);

      expect(URL.createObjectURL).toHaveBeenCalled();

      // Restore original methods
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });
  });
});
