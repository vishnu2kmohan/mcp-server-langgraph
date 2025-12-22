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

  return {
    id: generateArtifactId(),
    type: "chart",
    title: meta || "Chart",
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
  return {
    id: generateArtifactId(),
    type: "mermaid",
    title: meta || "Diagram",
    data: code,
  };
}

function createCodeArtifact(
  code: string,
  language: string,
  meta?: string,
): CodeArtifact {
  return {
    id: generateArtifactId(),
    type: "code",
    title: meta || `${language} code`,
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

  return {
    id: generateArtifactId(),
    type: "json",
    title: meta || "JSON",
    data,
  };
}

function createSVGArtifact(code: string, meta?: string): SVGArtifact {
  return {
    id: generateArtifactId(),
    type: "svg",
    title: meta || "SVG",
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
    const artifactType = detectArtifactType(block.language);
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
