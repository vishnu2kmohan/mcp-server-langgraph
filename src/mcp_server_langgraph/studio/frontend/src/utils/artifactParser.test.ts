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
  extractCodeName,
  extractMermaidName,
  extractSVGName,
  extractChartName,
  extractJSONName,
  detectSVGContent,
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

  // =========================================================================
  // Smart Name Extraction Tests (Sprint Block 4)
  // =========================================================================

  describe("extractCodeName", () => {
    it("should extract exported function name", () => {
      const code = `export function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}`;
      expect(extractCodeName(code, "javascript")).toBe("calculateTotal");
    });

    it("should extract exported class name", () => {
      const code = `export class UserAuthenticationService {
  constructor() {}
  login(email, password) {}
}`;
      expect(extractCodeName(code, "javascript")).toBe(
        "UserAuthenticationService",
      );
    });

    it("should extract default export function name", () => {
      const code = `export default function DataProcessor() {
  return null;
}`;
      expect(extractCodeName(code, "javascript")).toBe("DataProcessor");
    });

    it("should extract Python class name", () => {
      const code = `class DatabaseConnection:
    def __init__(self):
        pass`;
      expect(extractCodeName(code, "python")).toBe("DatabaseConnection");
    });

    it("should extract Python function name", () => {
      const code = `def process_payment(amount, currency):
    return {"status": "success"}`;
      expect(extractCodeName(code, "python")).toBe("process_payment");
    });

    it("should extract const arrow function name", () => {
      const code = `export const fetchUserData = async (userId) => {
  return await api.get(\`/users/\${userId}\`);
};`;
      expect(extractCodeName(code, "typescript")).toBe("fetchUserData");
    });

    it("should return null when no extractable name found", () => {
      const code = `console.log("hello world");`;
      expect(extractCodeName(code, "javascript")).toBeNull();
    });

    it("should prefer exported declarations over non-exported", () => {
      const code = `function helper() {}
export function mainFunction() {}`;
      expect(extractCodeName(code, "javascript")).toBe("mainFunction");
    });
  });

  describe("extractMermaidName", () => {
    it("should extract title directive", () => {
      const code = `---
title: User Authentication Flow
---
graph TD
    A[Start] --> B[Login]`;
      expect(extractMermaidName(code)).toBe("User Authentication Flow");
    });

    it("should extract pie chart title", () => {
      const code = `pie title Market Share Analysis
    "Chrome" : 62.85
    "Safari" : 19.25`;
      expect(extractMermaidName(code)).toBe("Market Share Analysis");
    });

    it("should describe flowchart type", () => {
      const code = `flowchart LR
    A --> B --> C`;
      expect(extractMermaidName(code)).toBe("Flowchart");
    });

    it("should describe sequence diagram", () => {
      const code = `sequenceDiagram
    participant A
    A->>B: Hello`;
      expect(extractMermaidName(code)).toBe("Sequence Diagram");
    });

    it("should describe class diagram", () => {
      const code = `classDiagram
    class Animal {
      +name: string
    }`;
      expect(extractMermaidName(code)).toBe("Class Diagram");
    });

    it("should describe ER diagram", () => {
      const code = `erDiagram
    CUSTOMER ||--o{ ORDER : places`;
      expect(extractMermaidName(code)).toBe("ER Diagram");
    });

    it("should describe state diagram", () => {
      const code = `stateDiagram-v2
    [*] --> Active`;
      expect(extractMermaidName(code)).toBe("State Diagram");
    });

    it("should describe gantt chart", () => {
      const code = `gantt
    title Project Timeline
    section Phase 1`;
      expect(extractMermaidName(code)).toBe("Project Timeline");
    });

    it("should describe journey diagram", () => {
      const code = `journey
    title My working day`;
      expect(extractMermaidName(code)).toBe("My working day");
    });

    it("should fallback to Diagram for unknown types", () => {
      const code = `unknownDiagram
    something --> else`;
      expect(extractMermaidName(code)).toBe("Diagram");
    });
  });

  describe("extractSVGName", () => {
    it("should extract title element", () => {
      const code = `<svg viewBox="0 0 100 100">
  <title>Company Logo</title>
  <circle cx="50" cy="50" r="40" />
</svg>`;
      expect(extractSVGName(code)).toBe("Company Logo");
    });

    it("should extract aria-label attribute", () => {
      const code = `<svg aria-label="Navigation Icon" viewBox="0 0 24 24">
  <path d="M12 2L2 22h20L12 2z" />
</svg>`;
      expect(extractSVGName(code)).toBe("Navigation Icon");
    });

    it("should extract aria-labelledby referenced title", () => {
      const code = `<svg aria-labelledby="iconTitle" viewBox="0 0 100 100">
  <title id="iconTitle">Settings Gear</title>
  <path d="..." />
</svg>`;
      expect(extractSVGName(code)).toBe("Settings Gear");
    });

    it("should extract id attribute as fallback", () => {
      const code = `<svg id="heroIllustration" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="blue" />
</svg>`;
      expect(extractSVGName(code)).toBe("heroIllustration");
    });

    it("should return null when no name found", () => {
      const code = `<svg viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" />
</svg>`;
      expect(extractSVGName(code)).toBeNull();
    });

    it("should prefer title over aria-label", () => {
      const code = `<svg aria-label="Alt Name" viewBox="0 0 100 100">
  <title>Primary Title</title>
</svg>`;
      expect(extractSVGName(code)).toBe("Primary Title");
    });
  });

  describe("extractChartName", () => {
    it("should extract title from chart config", () => {
      const code = `{
  "title": "Monthly Revenue",
  "type": "line",
  "data": []
}`;
      expect(extractChartName(code)).toBe("Monthly Revenue");
    });

    it("should extract nested title from config", () => {
      const code = `{
  "type": "bar",
  "config": { "title": "Sales by Region" },
  "data": []
}`;
      expect(extractChartName(code)).toBe("Sales by Region");
    });

    it("should describe chart type when no title", () => {
      const code = `{
  "type": "pie",
  "data": [{"label": "A", "value": 30}]
}`;
      expect(extractChartName(code)).toBe("Pie Chart");
    });

    it("should return null for invalid JSON", () => {
      const code = `not valid json`;
      expect(extractChartName(code)).toBeNull();
    });

    it("should capitalize chart type", () => {
      const code = `{
  "type": "scatter",
  "data": []
}`;
      expect(extractChartName(code)).toBe("Scatter Chart");
    });
  });

  describe("extractJSONName", () => {
    it("should use name field if present", () => {
      const code = `{
  "name": "user-config",
  "version": "1.0.0"
}`;
      expect(extractJSONName(code)).toBe("user-config");
    });

    it("should use title field if present", () => {
      const code = `{
  "title": "API Response",
  "data": {}
}`;
      expect(extractJSONName(code)).toBe("API Response");
    });

    it("should describe by root type for arrays", () => {
      const code = `[
  {"id": 1, "name": "Item 1"},
  {"id": 2, "name": "Item 2"}
]`;
      expect(extractJSONName(code)).toBe("Array (2 items)");
    });

    it("should describe by first key for objects", () => {
      const code = `{
  "users": [{"id": 1}],
  "total": 1
}`;
      expect(extractJSONName(code)).toBe("users Object");
    });

    it("should return null for invalid JSON", () => {
      const code = `not valid json`;
      expect(extractJSONName(code)).toBeNull();
    });

    it("should prefer name over title", () => {
      const code = `{
  "name": "config-name",
  "title": "Config Title"
}`;
      expect(extractJSONName(code)).toBe("config-name");
    });
  });

  describe("detectSVGContent", () => {
    it("should detect SVG starting with <svg tag", () => {
      const code = `<svg viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" />
</svg>`;
      expect(detectSVGContent(code)).toBe(true);
    });

    it("should detect SVG with XML declaration", () => {
      const code = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" />
</svg>`;
      expect(detectSVGContent(code)).toBe(true);
    });

    it("should return false for non-SVG content", () => {
      const code = `function hello() {
  console.log("hello");
}`;
      expect(detectSVGContent(code)).toBe(false);
    });

    it("should return false for HTML that mentions svg but is not SVG", () => {
      const code = `<div class="svg-container">
  <p>This mentions svg but is not SVG</p>
</div>`;
      expect(detectSVGContent(code)).toBe(false);
    });

    it("should handle whitespace before SVG tag", () => {
      const code = `
  <svg viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="40" />
  </svg>`;
      expect(detectSVGContent(code)).toBe(true);
    });
  });

  describe("parseArtifacts with SVG auto-detection", () => {
    it("should auto-detect SVG in code block without language", () => {
      const content = `Here is an SVG:

\`\`\`
<svg viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="blue" />
</svg>
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.type).toBe("svg");
    });

    it("should auto-detect SVG with XML declaration", () => {
      const content = `
\`\`\`
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="red" />
</svg>
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.type).toBe("svg");
    });

    it("should not auto-detect SVG when language is explicitly set", () => {
      const content = `
\`\`\`xml
<svg viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" />
</svg>
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      // xml is a code artifact, not svg
      expect(artifactSegment?.artifact?.type).toBe("code");
    });
  });

  describe("parseArtifacts with smart naming", () => {
    it("should use extracted function name for code artifact", () => {
      const content = `Here is some code:

\`\`\`typescript
export function validateEmail(email: string): boolean {
  return /^[^@]+@[^@]+\\.[^@]+$/.test(email);
}
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("validateEmail");
    });

    it("should use extracted title for mermaid diagram", () => {
      const content = `
\`\`\`mermaid
---
title: Database Schema
---
erDiagram
    USER ||--o{ ORDER : places
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("Database Schema");
    });

    it("should use extracted title for SVG", () => {
      const content = `
\`\`\`svg
<svg viewBox="0 0 100 100">
  <title>Loading Spinner</title>
  <circle cx="50" cy="50" r="40" />
</svg>
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("Loading Spinner");
    });

    it("should use extracted name for JSON", () => {
      const content = `
\`\`\`json
{
  "name": "package-config",
  "version": "2.0.0"
}
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("package-config");
    });

    it("should fallback to generic name when extraction fails", () => {
      const content = `
\`\`\`javascript
console.log("no function here");
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("javascript code");
    });

    it("should prefer meta title over extracted name", () => {
      const content = `
\`\`\`typescript User Validation Helper
export function validateUser() {}
\`\`\``;

      const segments = parseArtifacts(content);
      const artifactSegment = segments.find((s) => s.type === "artifact");
      expect(artifactSegment?.artifact?.title).toBe("User Validation Helper");
    });
  });
});
