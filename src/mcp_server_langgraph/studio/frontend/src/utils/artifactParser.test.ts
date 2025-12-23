/**
 * Artifact Parser Tests
 *
 * TDD tests for parsing LLM responses to extract interactive artifacts.
 * Detects fenced code blocks with special languages (chart, mermaid, mdx, etc.)
 * and converts them to renderable Artifact types.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  parseArtifacts,
  extractCodeBlocks,
  detectArtifactType,
  parseChartConfig,
} from "./artifactParser";

describe("Artifact Parser", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("extractCodeBlocks", () => {
    it("should extract a single code block", () => {
      const content = `Here is some text.

\`\`\`javascript
console.log("hello");
\`\`\`

More text.`;

      const blocks = extractCodeBlocks(content);
      expect(blocks).toHaveLength(1);
      expect(blocks[0].language).toBe("javascript");
      expect(blocks[0].code).toBe('console.log("hello");');
      expect(blocks[0].startIndex).toBeGreaterThan(0);
    });

    it("should extract multiple code blocks", () => {
      const content = `
\`\`\`python
print("hello")
\`\`\`

Some text between.

\`\`\`typescript
const x: number = 1;
\`\`\`
`;

      const blocks = extractCodeBlocks(content);
      expect(blocks).toHaveLength(2);
      expect(blocks[0].language).toBe("python");
      expect(blocks[1].language).toBe("typescript");
    });

    it("should handle code blocks without language", () => {
      const content = `
\`\`\`
plain code
\`\`\`
`;

      const blocks = extractCodeBlocks(content);
      expect(blocks).toHaveLength(1);
      expect(blocks[0].language).toBe("");
      expect(blocks[0].code).toBe("plain code");
    });

    it("should handle empty content", () => {
      const blocks = extractCodeBlocks("");
      expect(blocks).toHaveLength(0);
    });

    it("should handle content with no code blocks", () => {
      const content = "Just plain text without any code blocks.";
      const blocks = extractCodeBlocks(content);
      expect(blocks).toHaveLength(0);
    });

    it("should preserve whitespace in code blocks", () => {
      const content = `
\`\`\`python
def hello():
    print("indented")
    return True
\`\`\`
`;

      const blocks = extractCodeBlocks(content);
      expect(blocks[0].code).toContain("    print");
    });

    it("should extract code block metadata", () => {
      const content = `
\`\`\`chart title="Sales Report"
{"type": "bar"}
\`\`\`
`;

      const blocks = extractCodeBlocks(content);
      expect(blocks[0].language).toBe("chart");
      expect(blocks[0].meta).toBe('title="Sales Report"');
    });
  });

  describe("detectArtifactType", () => {
    it("should detect chart artifact from language", () => {
      expect(detectArtifactType("chart")).toBe("chart");
      expect(detectArtifactType("recharts")).toBe("chart");
      expect(detectArtifactType("vega-lite")).toBe("chart");
    });

    it("should detect mermaid artifact", () => {
      expect(detectArtifactType("mermaid")).toBe("mermaid");
    });

    it("should detect table artifact", () => {
      expect(detectArtifactType("table")).toBe("table");
      expect(detectArtifactType("csv")).toBe("table");
    });

    it("should detect code artifact for programming languages", () => {
      expect(detectArtifactType("javascript")).toBe("code");
      expect(detectArtifactType("typescript")).toBe("code");
      expect(detectArtifactType("python")).toBe("code");
      expect(detectArtifactType("rust")).toBe("code");
    });

    it("should detect mdx artifact", () => {
      expect(detectArtifactType("mdx")).toBe("mdx");
    });

    it("should detect jsx/tsx as executable", () => {
      expect(detectArtifactType("jsx")).toBe("executable");
      expect(detectArtifactType("tsx")).toBe("executable");
    });

    it("should detect json artifact", () => {
      expect(detectArtifactType("json")).toBe("json");
    });

    it("should detect svg artifact", () => {
      expect(detectArtifactType("svg")).toBe("svg");
    });

    it("should default to code for unknown languages", () => {
      expect(detectArtifactType("unknown")).toBe("code");
      expect(detectArtifactType("")).toBe("text");
    });
  });

  describe("parseChartConfig", () => {
    it("should parse valid JSON chart config", () => {
      const code = `{
        "type": "line",
        "data": [{"x": 1, "y": 2}],
        "config": {"xAxisKey": "x", "yAxisKey": "y"}
      }`;

      const result = parseChartConfig(code);
      expect(result).not.toBeNull();
      expect(result?.type).toBe("line");
      expect(result?.data).toHaveLength(1);
    });

    it("should return null for invalid JSON", () => {
      const result = parseChartConfig("not valid json");
      expect(result).toBeNull();
    });

    it("should handle chart config without explicit type", () => {
      const code = `{
        "data": [{"month": "Jan", "value": 100}]
      }`;

      const result = parseChartConfig(code);
      expect(result).not.toBeNull();
      expect(result?.type).toBe("bar"); // Default type
    });
  });

  describe("parseArtifacts", () => {
    it("should parse content into text and artifact segments", () => {
      const content = `Here is a chart:

\`\`\`chart
{"type": "bar", "data": [{"x": "A", "y": 10}]}
\`\`\`

And some more text.`;

      const segments = parseArtifacts(content);

      expect(segments).toHaveLength(3);
      expect(segments[0].type).toBe("text");
      expect(segments[0].content).toContain("Here is a chart:");
      expect(segments[1].type).toBe("artifact");
      expect(segments[1].artifact?.type).toBe("chart");
      expect(segments[2].type).toBe("text");
      expect(segments[2].content).toContain("And some more text.");
    });

    it("should handle mermaid diagrams", () => {
      const content = `
\`\`\`mermaid
graph TD
    A --> B
    B --> C
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment).toBeDefined();
      expect(artifactSegment?.artifact?.type).toBe("mermaid");
      expect(artifactSegment?.artifact?.data).toContain("graph TD");
    });

    it("should handle MDX content", () => {
      const content = `
\`\`\`mdx
import { Chart } from '@/components';

# My Report

<Chart data={[{x: 1, y: 2}]} />
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment).toBeDefined();
      // MDX is treated as executable since it needs Sandpack to render
      expect(artifactSegment?.artifact?.type).toBe("executable");
      expect(artifactSegment?.artifact?.config?.language).toBe("mdx");
      expect(artifactSegment?.artifact?.metadata?.isMDX).toBe(true);
    });

    it("should handle regular code blocks as code artifacts", () => {
      const content = `
\`\`\`python
def hello():
    return "world"
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment?.artifact?.type).toBe("code");
      expect(artifactSegment?.artifact?.config?.language).toBe("python");
    });

    it("should handle content with no artifacts", () => {
      const content = "Just plain text without any code blocks.";

      const segments = parseArtifacts(content);

      expect(segments).toHaveLength(1);
      expect(segments[0].type).toBe("text");
      expect(segments[0].content).toBe(content);
    });

    it("should handle multiple consecutive artifacts", () => {
      const content = `
\`\`\`chart
{"type": "pie", "data": []}
\`\`\`

\`\`\`mermaid
pie title Pets
    "Dogs" : 386
    "Cats" : 85
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifacts = segments.filter((s) => s.type === "artifact");

      expect(artifacts).toHaveLength(2);
      expect(artifacts[0].artifact?.type).toBe("chart");
      expect(artifacts[1].artifact?.type).toBe("mermaid");
    });

    it("should generate unique IDs for artifacts", () => {
      const content = `
\`\`\`chart
{}
\`\`\`

\`\`\`chart
{}
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifacts = segments.filter((s) => s.type === "artifact");

      expect(artifacts[0].artifact?.id).not.toBe(artifacts[1].artifact?.id);
    });

    it("should handle JSON artifacts", () => {
      const content = `
\`\`\`json
{"key": "value", "nested": {"a": 1}}
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment?.artifact?.type).toBe("json");
    });

    it("should handle SVG artifacts", () => {
      const content = `
\`\`\`svg
<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="red" />
</svg>
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment?.artifact?.type).toBe("svg");
      expect(artifactSegment?.artifact?.data).toContain("<circle");
    });

    it("should handle executable JSX/TSX", () => {
      const content = `
\`\`\`tsx
export default function App() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
\`\`\`
`;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");

      expect(artifactSegment?.artifact?.type).toBe("executable");
    });
  });
});
