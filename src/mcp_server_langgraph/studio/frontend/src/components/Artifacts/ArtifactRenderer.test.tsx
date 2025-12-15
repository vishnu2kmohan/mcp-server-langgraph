/**
 * ArtifactRenderer Tests
 *
 * TDD tests for the auto-detecting artifact renderer.
 * Tests cover:
 * - Auto-detection of artifact types
 * - Rendering correct component for each type
 * - Fallback for unknown types
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArtifactRenderer, detectArtifactType } from "./ArtifactRenderer";
import type { Artifact } from "../../types/artifacts";

describe("ArtifactRenderer", () => {
  describe("detectArtifactType", () => {
    it("should detect JSON from object data", () => {
      const result = detectArtifactType({ foo: "bar", nested: { value: 1 } });
      expect(result.type).toBe("json");
      expect(result.confidence).toBeGreaterThan(0.8);
    });

    it("should detect JSON from valid JSON string", () => {
      const result = detectArtifactType('{"key": "value"}');
      expect(result.type).toBe("json");
    });

    it("should detect mermaid from diagram syntax", () => {
      const mermaidCode = `graph TD
        A --> B`;
      const result = detectArtifactType(mermaidCode);
      expect(result.type).toBe("mermaid");
    });

    it("should detect mermaid from flowchart syntax", () => {
      const result = detectArtifactType("flowchart LR\n  A --> B");
      expect(result.type).toBe("mermaid");
    });

    it("should detect mermaid from sequenceDiagram syntax", () => {
      const result = detectArtifactType(
        "sequenceDiagram\n  Alice->>Bob: Hello",
      );
      expect(result.type).toBe("mermaid");
    });

    it("should detect code from markdown code blocks", () => {
      const result = detectArtifactType('```python\nprint("hello")\n```');
      expect(result.type).toBe("code");
    });

    it("should detect code from function definitions", () => {
      const result = detectArtifactType('function hello() { return "world"; }');
      expect(result.type).toBe("code");
    });

    it("should detect table from array of objects", () => {
      const data = [
        { name: "Alice", age: 30 },
        { name: "Bob", age: 25 },
      ];
      const result = detectArtifactType(data);
      expect(result.type).toBe("table");
    });

    it("should detect chart from data with numeric values", () => {
      const data = [
        { label: "Q1", value: 100 },
        { label: "Q2", value: 200 },
      ];
      const result = detectArtifactType(data, "chart");
      expect(result.type).toBe("chart");
    });

    it("should detect text as fallback", () => {
      const result = detectArtifactType(
        "Just some plain text without any special formatting",
      );
      expect(result.type).toBe("text");
    });

    it("should detect image from base64 data URL", () => {
      const result = detectArtifactType("data:image/png;base64,iVBORw0KGgo=");
      expect(result.type).toBe("image");
    });

    it("should detect image from http URL with image extension", () => {
      const result = detectArtifactType("https://example.com/image.png");
      expect(result.type).toBe("image");
    });
  });

  describe("Rendering", () => {
    it("should render JSONArtifact for json type", () => {
      const artifact: Artifact = {
        id: "1",
        type: "json",
        data: { key: "value" },
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-json")).toBeInTheDocument();
    });

    it("should render MermaidArtifact for mermaid type", () => {
      const artifact: Artifact = {
        id: "2",
        type: "mermaid",
        data: "graph TD\n  A --> B",
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
    });

    it("should render CodeArtifact for code type", () => {
      const artifact: Artifact = {
        id: "3",
        type: "code",
        data: 'console.log("hello")',
        config: { language: "javascript" },
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-code")).toBeInTheDocument();
    });

    it("should render TableArtifact for table type", () => {
      const artifact: Artifact = {
        id: "4",
        type: "table",
        data: [{ name: "Test", value: 1 }],
        config: {
          columns: [
            { id: "name", header: "Name" },
            { id: "value", header: "Value" },
          ],
        },
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-table")).toBeInTheDocument();
    });

    it("should render ChartArtifact for chart type", () => {
      const artifact: Artifact = {
        id: "5",
        type: "chart",
        data: [{ label: "A", value: 10 }],
        config: { chartType: "bar" },
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-chart")).toBeInTheDocument();
    });

    it("should render text fallback for unknown type", () => {
      const artifact: Artifact = {
        id: "6",
        type: "text",
        data: "Plain text content",
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-text")).toBeInTheDocument();
      expect(screen.getByText("Plain text content")).toBeInTheDocument();
    });

    it("should render image for image type", () => {
      const artifact: Artifact = {
        id: "7",
        type: "image",
        data: "https://example.com/image.png",
      };
      render(<ArtifactRenderer artifact={artifact} />);

      expect(screen.getByTestId("artifact-image")).toBeInTheDocument();
    });
  });

  describe("Auto-detection mode", () => {
    it("should auto-detect and render JSON from raw data", () => {
      render(<ArtifactRenderer data={{ key: "value" }} autoDetect />);

      expect(screen.getByTestId("artifact-json")).toBeInTheDocument();
    });

    it("should auto-detect and render mermaid from diagram string", () => {
      render(<ArtifactRenderer data="graph TD\n  A --> B" autoDetect />);

      expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
    });
  });
});
