/**
 * Artifact Parser
 *
 * Parses LLM responses to extract interactive artifacts from fenced code blocks.
 * Supports chart, mermaid, mdx, json, svg, and executable code detection.
 */

import type {
  Artifact,
  ArtifactType,
  ChartArtifact,
  MermaidArtifact,
  CodeArtifact,
  JSONArtifact,
  SVGArtifact,
  ExecutableArtifact,
  TextArtifact,
  ChartType,
} from "../types/artifacts";

// ============================================================================
// Types
// ============================================================================

export interface CodeBlock {
  language: string;
  code: string;
  meta?: string;
  startIndex: number;
  endIndex: number;
}

export interface ParsedSegment {
  type: "text" | "artifact";
  content: string;
  artifact?: Artifact;
}

interface ChartConfig {
  type: ChartType;
  data: unknown[];
  config?: Record<string, unknown>;
}

// Extended artifact type to include mdx
type ExtendedArtifactType = ArtifactType | "mdx";

// ============================================================================
// Language to Artifact Type Mapping
// ============================================================================

const CHART_LANGUAGES = new Set([
  "chart",
  "recharts",
  "vega-lite",
  "vega",
  "echarts",
]);
const MERMAID_LANGUAGES = new Set(["mermaid"]);
const TABLE_LANGUAGES = new Set(["table", "csv", "tsv"]);
const JSON_LANGUAGES = new Set(["json", "jsonc"]);
const SVG_LANGUAGES = new Set(["svg"]);
const MDX_LANGUAGES = new Set(["mdx"]);
const EXECUTABLE_LANGUAGES = new Set(["jsx", "tsx"]);

const CODE_LANGUAGES = new Set([
  "javascript",
  "typescript",
  "python",
  "rust",
  "go",
  "java",
  "c",
  "cpp",
  "csharp",
  "ruby",
  "php",
  "swift",
  "kotlin",
  "scala",
  "haskell",
  "elixir",
  "clojure",
  "sql",
  "bash",
  "shell",
  "sh",
  "zsh",
  "powershell",
  "yaml",
  "toml",
  "html",
  "css",
  "scss",
  "less",
  "graphql",
  "dockerfile",
  "makefile",
  "lua",
  "perl",
  "r",
  "matlab",
  "julia",
]);

// ============================================================================
// Utility Functions
// ============================================================================

let artifactIdCounter = 0;

function generateArtifactId(): string {
  return `artifact-${Date.now()}-${++artifactIdCounter}`;
}

// ============================================================================
// Smart Name Extraction Functions (Sprint Block 4)
// ============================================================================

/**
 * Extract a descriptive name from code content.
 * Looks for exported functions, classes, and const declarations.
 */
export function extractCodeName(code: string, language: string): string | null {
  const lang = language.toLowerCase();

  // JavaScript/TypeScript patterns
  if (
    ["javascript", "typescript", "js", "ts", "jsx", "tsx"].includes(lang) ||
    lang === ""
  ) {
    // export function name() or export default function name()
    const exportFuncMatch = code.match(
      /export\s+(?:default\s+)?function\s+(\w+)/,
    );
    if (exportFuncMatch?.[1]) return exportFuncMatch[1];

    // export class Name
    const exportClassMatch = code.match(
      /export\s+(?:default\s+)?class\s+(\w+)/,
    );
    if (exportClassMatch?.[1]) return exportClassMatch[1];

    // export const name = (arrow function)
    const exportConstMatch = code.match(
      /export\s+const\s+(\w+)\s*=\s*(?:async\s+)?\(/,
    );
    if (exportConstMatch?.[1]) return exportConstMatch[1];

    // Non-exported function (fallback) - require parenthesis to avoid false positives
    const funcMatch = code.match(/function\s+(\w+)\s*\(/);
    if (funcMatch?.[1]) return funcMatch[1];

    // Non-exported class (fallback)
    const classMatch = code.match(/class\s+(\w+)/);
    if (classMatch?.[1]) return classMatch[1];
  }

  // Python patterns
  if (lang === "python" || lang === "py") {
    // class ClassName:
    const classMatch = code.match(/^class\s+(\w+)\s*[:(]/m);
    if (classMatch?.[1]) return classMatch[1];

    // def function_name(
    const funcMatch = code.match(/^def\s+(\w+)\s*\(/m);
    if (funcMatch?.[1]) return funcMatch[1];
  }

  // Go patterns
  if (lang === "go") {
    // func FunctionName(
    const funcMatch = code.match(/func\s+(\w+)\s*\(/);
    if (funcMatch?.[1]) return funcMatch[1];

    // type TypeName struct
    const typeMatch = code.match(/type\s+(\w+)\s+struct/);
    if (typeMatch?.[1]) return typeMatch[1];
  }

  // Rust patterns
  if (lang === "rust" || lang === "rs") {
    // fn function_name(
    const funcMatch = code.match(/(?:pub\s+)?fn\s+(\w+)/);
    if (funcMatch?.[1]) return funcMatch[1];

    // struct StructName
    const structMatch = code.match(/(?:pub\s+)?struct\s+(\w+)/);
    if (structMatch?.[1]) return structMatch[1];
  }

  return null;
}

/**
 * Extract a descriptive name from Mermaid diagram content.
 * Looks for title directives and diagram type labels.
 */
export function extractMermaidName(code: string): string {
  // Check for YAML frontmatter title
  const frontmatterMatch = code.match(/---\s*\n[\s\S]*?title:\s*(.+?)\n/);
  if (frontmatterMatch?.[1]) return frontmatterMatch[1].trim();

  // Check for inline title (gantt, journey, pie)
  const inlineTitleMatch = code.match(/(?:gantt|journey|pie)\s+title\s+(.+)/i);
  if (inlineTitleMatch?.[1]) return inlineTitleMatch[1].trim();

  // Detect diagram type and return descriptive name
  const firstLine = code.trim().split("\n")[0]?.toLowerCase() || "";

  if (firstLine.startsWith("graph") || firstLine.startsWith("flowchart")) {
    return "Flowchart";
  }
  if (firstLine.startsWith("sequencediagram")) {
    return "Sequence Diagram";
  }
  if (firstLine.startsWith("classdiagram")) {
    return "Class Diagram";
  }
  if (firstLine.startsWith("erdiagram")) {
    return "ER Diagram";
  }
  if (firstLine.startsWith("statediagram")) {
    return "State Diagram";
  }
  if (firstLine.startsWith("gantt")) {
    return "Gantt Chart";
  }
  if (firstLine.startsWith("pie")) {
    return "Pie Chart";
  }
  if (firstLine.startsWith("journey")) {
    return "Journey Diagram";
  }
  if (firstLine.startsWith("gitgraph")) {
    return "Git Graph";
  }
  if (firstLine.startsWith("mindmap")) {
    return "Mind Map";
  }
  if (firstLine.startsWith("timeline")) {
    return "Timeline";
  }

  return "Diagram";
}

/**
 * Extract a descriptive name from SVG content.
 * Looks for title element, aria-label, or id attribute.
 */
export function extractSVGName(code: string): string | null {
  // Extract <title> element content
  const titleMatch = code.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (titleMatch?.[1]) return titleMatch[1].trim();

  // Extract aria-label attribute
  const ariaLabelMatch = code.match(/aria-label=["']([^"']+)["']/i);
  if (ariaLabelMatch?.[1]) return ariaLabelMatch[1].trim();

  // Extract id attribute from <svg> tag as fallback
  const svgIdMatch = code.match(/<svg[^>]*\sid=["']([^"']+)["']/i);
  if (svgIdMatch?.[1]) return svgIdMatch[1];

  return null;
}

/**
 * Extract a descriptive name from chart configuration.
 * Looks for title field or describes chart type.
 */
export function extractChartName(code: string): string | null {
  try {
    const parsed = JSON.parse(code);

    // Check for title at root level
    if (parsed.title && typeof parsed.title === "string") {
      return parsed.title;
    }

    // Check for title in config object
    if (parsed.config?.title && typeof parsed.config.title === "string") {
      return parsed.config.title;
    }

    // Describe by chart type
    if (parsed.type && typeof parsed.type === "string") {
      const type = parsed.type.charAt(0).toUpperCase() + parsed.type.slice(1);
      return `${type} Chart`;
    }

    return "Chart";
  } catch {
    return null;
  }
}

/**
 * Extract a descriptive name from JSON content.
 * Looks for name/title fields or describes by structure.
 */
export function extractJSONName(code: string): string | null {
  try {
    const parsed = JSON.parse(code);

    // Check for name field (prefer over title)
    if (parsed.name && typeof parsed.name === "string") {
      return parsed.name;
    }

    // Check for title field
    if (parsed.title && typeof parsed.title === "string") {
      return parsed.title;
    }

    // Describe arrays by length
    if (Array.isArray(parsed)) {
      return `Array (${parsed.length} items)`;
    }

    // Describe objects by first key
    if (typeof parsed === "object" && parsed !== null) {
      const keys = Object.keys(parsed);
      if (keys.length > 0) {
        return `${keys[0]} Object`;
      }
    }

    return "JSON";
  } catch {
    return null;
  }
}

/**
 * Detect if code content is SVG.
 * Used for auto-detecting SVG in code blocks without explicit language.
 */
export function detectSVGContent(code: string): boolean {
  const trimmed = code.trim();

  // Check for direct <svg tag
  if (trimmed.startsWith("<svg")) {
    return true;
  }

  // Check for XML declaration followed by SVG
  if (trimmed.startsWith("<?xml")) {
    return trimmed.includes("<svg");
  }

  return false;
}

// ============================================================================
// Code Block Extraction
// ============================================================================

/**
 * Extract all fenced code blocks from content.
 * Matches ```language meta\n...\n``` patterns.
 */
export function extractCodeBlocks(content: string): CodeBlock[] {
  const blocks: CodeBlock[] = [];

  // Match fenced code blocks: ```language meta\n...\n```
  // The regex captures:
  // 1. Optional language (word characters)
  // 2. Optional meta (rest of the first line)
  // 3. Code content (everything until closing ```)
  const codeBlockRegex = /```(\w*)([^\n]*)\n([\s\S]*?)```/g;

  let match: RegExpExecArray | null;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const [fullMatch, language, meta, code] = match;
    if (!code) continue;
    blocks.push({
      language: language || "",
      code: code.trimEnd(), // Only trim trailing whitespace to preserve indentation
      meta: meta?.trim() || undefined,
      startIndex: match.index,
      endIndex: match.index + fullMatch.length,
    });
  }

  return blocks;
}

// ============================================================================
// Artifact Type Detection
// ============================================================================

/**
 * Detect artifact type from code block language.
 */
export function detectArtifactType(language: string): ExtendedArtifactType {
  const lang = language.toLowerCase();

  if (!lang) return "text";
  if (CHART_LANGUAGES.has(lang)) return "chart";
  if (MERMAID_LANGUAGES.has(lang)) return "mermaid";
  if (TABLE_LANGUAGES.has(lang)) return "table";
  if (JSON_LANGUAGES.has(lang)) return "json";
  if (SVG_LANGUAGES.has(lang)) return "svg";
  if (MDX_LANGUAGES.has(lang)) return "mdx";
  if (EXECUTABLE_LANGUAGES.has(lang)) return "executable";
  if (CODE_LANGUAGES.has(lang)) return "code";

  // Default to code for unknown languages
  return "code";
}

// ============================================================================
// Chart Config Parsing
// ============================================================================

/**
 * Parse chart configuration from JSON code block.
 */
export function parseChartConfig(code: string): ChartConfig | null {
  try {
    const parsed = JSON.parse(code);

    // Ensure we have at least a data array
    const data = Array.isArray(parsed.data) ? parsed.data : [];
    const type: ChartType = parsed.type || "bar";
    const config = parsed.config || {};

    return { type, data, config };
  } catch {
    return null;
  }
}

// ============================================================================
// Artifact Creation
// ============================================================================

function createChartArtifact(
  code: string,
  meta?: string,
): ChartArtifact | null {
  const config = parseChartConfig(code);
  if (!config) return null;

  // Smart naming: use meta > extracted chart name > fallback
  const smartName = meta || extractChartName(code) || "Chart";

  return {
    id: generateArtifactId(),
    type: "chart",
    title: smartName,
    data: config.data as Array<
      Record<string, string | number | boolean | null>
    >,
    config: {
      chartType: config.type,
      ...(config.config as Record<string, unknown>),
    },
  };
}

function createMermaidArtifact(code: string, meta?: string): MermaidArtifact {
  // Smart naming: use meta > extracted mermaid name
  const smartName = meta || extractMermaidName(code);

  return {
    id: generateArtifactId(),
    type: "mermaid",
    title: smartName,
    data: code,
  };
}

function createCodeArtifact(
  code: string,
  language: string,
  meta?: string,
): CodeArtifact {
  // Smart naming: use meta > extracted code name > fallback
  const smartName =
    meta || extractCodeName(code, language) || `${language} code`;

  return {
    id: generateArtifactId(),
    type: "code",
    title: smartName,
    data: code,
    config: {
      language,
      showLineNumbers: true,
    },
  };
}

function createJSONArtifact(code: string, meta?: string): JSONArtifact {
  let data: unknown;
  try {
    data = JSON.parse(code);
  } catch {
    data = code;
  }

  // Smart naming: use meta > extracted JSON name > fallback
  const smartName = meta || extractJSONName(code) || "JSON";

  return {
    id: generateArtifactId(),
    type: "json",
    title: smartName,
    data,
  };
}

function createSVGArtifact(code: string, meta?: string): SVGArtifact {
  // Smart naming: use meta > extracted SVG name > fallback
  const smartName = meta || extractSVGName(code) || "SVG";

  return {
    id: generateArtifactId(),
    type: "svg",
    title: smartName,
    data: code,
  };
}

function createExecutableArtifact(
  code: string,
  language: string,
  meta?: string,
): ExecutableArtifact {
  return {
    id: generateArtifactId(),
    type: "executable",
    title: meta || "Interactive Component",
    data: code,
    config: {
      language,
      runtime: "webassembly", // Will be rendered with Sandpack
    },
  };
}

function createMDXArtifact(code: string, meta?: string): Artifact {
  // MDX is treated as executable since it needs Sandpack to render
  return {
    id: generateArtifactId(),
    type: "executable",
    title: meta || "Interactive Report",
    data: code,
    config: {
      language: "mdx",
      runtime: "webassembly",
    },
    metadata: {
      isMDX: true,
    },
  } as ExecutableArtifact;
}

function createTextArtifact(code: string): TextArtifact {
  return {
    id: generateArtifactId(),
    type: "text",
    data: code,
  };
}

// ============================================================================
// Main Parser
// ============================================================================

/**
 * Parse content into segments of text and artifacts.
 * Extracts fenced code blocks and converts them to appropriate artifact types.
 */
export function parseArtifacts(content: string): ParsedSegment[] {
  const blocks = extractCodeBlocks(content);

  if (blocks.length === 0) {
    return [{ type: "text", content }];
  }

  const segments: ParsedSegment[] = [];
  let lastIndex = 0;

  for (const block of blocks) {
    // Add text segment before this block
    if (block.startIndex > lastIndex) {
      const textContent = content.slice(lastIndex, block.startIndex).trim();
      if (textContent) {
        segments.push({ type: "text", content: textContent });
      }
    }

    // Create artifact from code block
    // First, detect artifact type from language
    let artifactType = detectArtifactType(block.language);

    // Auto-detect SVG in code blocks without explicit language
    if (artifactType === "text" && detectSVGContent(block.code)) {
      artifactType = "svg";
    }

    let artifact: Artifact | null = null;

    switch (artifactType) {
      case "chart":
        artifact = createChartArtifact(block.code, block.meta);
        // Fall back to code if chart parsing fails
        if (!artifact) {
          artifact = createCodeArtifact(block.code, block.language, block.meta);
        }
        break;

      case "mermaid":
        artifact = createMermaidArtifact(block.code, block.meta);
        break;

      case "json":
        artifact = createJSONArtifact(block.code, block.meta);
        break;

      case "svg":
        artifact = createSVGArtifact(block.code, block.meta);
        break;

      case "executable":
        artifact = createExecutableArtifact(
          block.code,
          block.language,
          block.meta,
        );
        break;

      case "mdx":
        artifact = createMDXArtifact(block.code, block.meta);
        break;

      case "code":
        artifact = createCodeArtifact(block.code, block.language, block.meta);
        break;

      case "table":
        // For now, treat table as code until we implement table parsing
        artifact = createCodeArtifact(block.code, block.language, block.meta);
        break;

      default:
        artifact = createTextArtifact(block.code);
    }

    if (artifact) {
      segments.push({
        type: "artifact",
        content: block.code,
        artifact,
      });
    }

    lastIndex = block.endIndex;
  }

  // Add remaining text after last block
  if (lastIndex < content.length) {
    const textContent = content.slice(lastIndex).trim();
    if (textContent) {
      segments.push({ type: "text", content: textContent });
    }
  }

  return segments;
}
