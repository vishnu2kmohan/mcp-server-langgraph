/**
 * Source Utilities Tests
 *
 * Tests for source citation utility functions.
 */
import { describe, it, expect } from "vitest";
import {
  extractDomain,
  truncateSnippet,
  dedupeByDomain,
  getSourceDisplayTitle,
  getSourceAriaLabel,
  sortByRelevance,
  isKBSource,
  groupSourcesByType,
} from "./sourceUtils";
import type { SourceCitation } from "../types/session";

// =============================================================================
// extractDomain Tests
// =============================================================================

describe("extractDomain", () => {
  it("should extract domain from valid URL", () => {
    expect(extractDomain("https://docs.python.org/3/tutorial")).toBe(
      "docs.python.org"
    );
  });

  it("should remove www prefix", () => {
    expect(extractDomain("https://www.example.com/page")).toBe("example.com");
  });

  it("should handle URLs without www", () => {
    expect(extractDomain("https://realpython.com/guide")).toBe("realpython.com");
  });

  it("should handle URLs with ports", () => {
    expect(extractDomain("http://localhost:3000/api")).toBe("localhost");
  });

  it("should handle URLs with subdomains", () => {
    expect(extractDomain("https://api.github.com/repos")).toBe("api.github.com");
  });

  it("should return original string for invalid URLs", () => {
    expect(extractDomain("not-a-url")).toBe("not-a-url");
  });

  it("should return original string for empty URL", () => {
    expect(extractDomain("")).toBe("");
  });

  it("should handle URLs with authentication", () => {
    expect(extractDomain("https://user:pass@example.com/path")).toBe(
      "example.com"
    );
  });

  it("should handle file URLs", () => {
    // File URLs don't have a hostname, should return original
    expect(extractDomain("file:///path/to/file")).toBe("");
  });

  it("should handle URLs with query parameters", () => {
    expect(extractDomain("https://example.com/search?q=test&page=1")).toBe(
      "example.com"
    );
  });

  it("should handle URLs with fragments", () => {
    expect(extractDomain("https://docs.python.org/guide#section-1")).toBe(
      "docs.python.org"
    );
  });

  it("should handle international domain names (punycode)", () => {
    // URL class converts IDN to punycode
    expect(extractDomain("https://münchen.example.de/page")).toBe(
      "xn--mnchen-3ya.example.de"
    );
  });

  it("should handle URLs with encoded characters", () => {
    expect(extractDomain("https://example.com/path%20with%20spaces")).toBe(
      "example.com"
    );
  });
});

// =============================================================================
// truncateSnippet Tests
// =============================================================================

describe("truncateSnippet", () => {
  it("should return null for null snippet", () => {
    expect(truncateSnippet(null)).toBeNull();
  });

  it("should return null for undefined snippet", () => {
    expect(truncateSnippet(undefined)).toBeNull();
  });

  it("should return null for empty string", () => {
    expect(truncateSnippet("")).toBeNull();
  });

  it("should return original string if shorter than max length", () => {
    const short = "This is a short snippet.";
    expect(truncateSnippet(short)).toBe(short);
  });

  it("should return original string if exactly max length", () => {
    const exact = "a".repeat(120);
    expect(truncateSnippet(exact, 120)).toBe(exact);
  });

  it("should truncate and add ellipsis if longer than max length", () => {
    const long = "a".repeat(150);
    const result = truncateSnippet(long, 120);
    expect(result).toBe("a".repeat(120) + "...");
    expect(result?.length).toBe(123); // 120 chars + "..."
  });

  it("should use default max length of 120", () => {
    const long = "a".repeat(200);
    const result = truncateSnippet(long);
    expect(result).toBe("a".repeat(120) + "...");
  });

  it("should respect custom max length", () => {
    const text = "This is some text that needs truncation";
    const result = truncateSnippet(text, 10);
    expect(result).toBe("This is so...");
  });
});

// =============================================================================
// dedupeByDomain Tests
// =============================================================================

describe("dedupeByDomain", () => {
  it("should return empty array for empty input", () => {
    expect(dedupeByDomain([])).toEqual([]);
  });

  it("should return single source unchanged", () => {
    const sources = [{ url: "https://example.com", title: "Test" }];
    expect(dedupeByDomain(sources)).toEqual(sources);
  });

  it("should keep first source per domain", () => {
    const sources = [
      { url: "https://docs.python.org/3/tutorial", title: "Tutorial" },
      { url: "https://docs.python.org/3/reference", title: "Reference" },
      { url: "https://realpython.com/guide", title: "Real Python" },
    ];

    const result = dedupeByDomain(sources);

    expect(result).toHaveLength(2);
    expect(result[0].title).toBe("Tutorial");
    expect(result[1].title).toBe("Real Python");
  });

  it("should preserve order of first occurrences", () => {
    const sources = [
      { url: "https://a.com/1", title: "A1" },
      { url: "https://b.com/1", title: "B1" },
      { url: "https://a.com/2", title: "A2" },
      { url: "https://c.com/1", title: "C1" },
      { url: "https://b.com/2", title: "B2" },
    ];

    const result = dedupeByDomain(sources);

    expect(result).toHaveLength(3);
    expect(result.map((s) => s.title)).toEqual(["A1", "B1", "C1"]);
  });

  it("should handle www prefix consistently", () => {
    const sources = [
      { url: "https://www.example.com/page1", title: "With WWW" },
      { url: "https://example.com/page2", title: "Without WWW" },
    ];

    const result = dedupeByDomain(sources);

    // Both should be treated as same domain
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("With WWW");
  });

  it("should work with SourceCitation type", () => {
    const sources: SourceCitation[] = [
      { url: "https://example.com/1", title: "First" },
      { url: "https://example.com/2", title: "Second", snippet: "text" },
    ];

    const result = dedupeByDomain(sources);
    expect(result).toHaveLength(1);
  });
});

// =============================================================================
// getSourceDisplayTitle Tests
// =============================================================================

describe("getSourceDisplayTitle", () => {
  it("should return title if present", () => {
    const source: SourceCitation = {
      url: "https://example.com",
      title: "Example Site",
    };
    expect(getSourceDisplayTitle(source)).toBe("Example Site");
  });

  it("should return domain if title is empty", () => {
    const source: SourceCitation = {
      url: "https://example.com/page",
      title: "",
    };
    expect(getSourceDisplayTitle(source)).toBe("example.com");
  });

  it("should return domain if title is whitespace only", () => {
    const source: SourceCitation = {
      url: "https://docs.python.org",
      title: "   ",
    };
    expect(getSourceDisplayTitle(source)).toBe("docs.python.org");
  });

  it("should handle source without title", () => {
    const source = { url: "https://github.com/repo" } as SourceCitation;
    expect(getSourceDisplayTitle(source)).toBe("github.com");
  });
});

// =============================================================================
// getSourceAriaLabel Tests
// =============================================================================

describe("getSourceAriaLabel", () => {
  it("should create accessible label with title", () => {
    const source: SourceCitation = {
      url: "https://example.com",
      title: "Example Site",
    };
    expect(getSourceAriaLabel(source)).toBe(
      "Source: Example Site (opens in new tab)"
    );
  });

  it("should create accessible label with domain when no title", () => {
    const source: SourceCitation = {
      url: "https://docs.python.org/guide",
      title: "",
    };
    expect(getSourceAriaLabel(source)).toBe(
      "Source: docs.python.org (opens in new tab)"
    );
  });

  it("should indicate external link behavior", () => {
    const source: SourceCitation = {
      url: "https://example.com",
      title: "Test",
    };
    const label = getSourceAriaLabel(source);
    expect(label).toContain("opens in new tab");
  });
});

// =============================================================================
// sortByRelevance Tests
// =============================================================================

describe("sortByRelevance", () => {
  it("should return empty array for empty input", () => {
    expect(sortByRelevance([])).toEqual([]);
  });

  it("should sort sources by relevance_score descending", () => {
    const sources: SourceCitation[] = [
      { title: "Low", url: "https://low.com", relevance_score: 0.3 },
      { title: "High", url: "https://high.com", relevance_score: 0.95 },
      { title: "Medium", url: "https://medium.com", relevance_score: 0.6 },
    ];

    const sorted = sortByRelevance(sources);

    expect(sorted[0].title).toBe("High");
    expect(sorted[1].title).toBe("Medium");
    expect(sorted[2].title).toBe("Low");
  });

  it("should place sources without relevance_score at the end", () => {
    const sources: SourceCitation[] = [
      { title: "No Score", url: "https://noscore.com" },
      { title: "Has Score", url: "https://hasscore.com", relevance_score: 0.5 },
    ];

    const sorted = sortByRelevance(sources);

    expect(sorted[0].title).toBe("Has Score");
    expect(sorted[1].title).toBe("No Score");
  });

  it("should treat null relevance_score as 0", () => {
    const sources: SourceCitation[] = [
      { title: "Null Score", url: "https://null.com", relevance_score: null },
      { title: "Has Score", url: "https://has.com", relevance_score: 0.8 },
    ];

    const sorted = sortByRelevance(sources);

    expect(sorted[0].title).toBe("Has Score");
    expect(sorted[1].title).toBe("Null Score");
  });

  it("should not mutate original array", () => {
    const sources: SourceCitation[] = [
      { title: "B", url: "https://b.com", relevance_score: 0.5 },
      { title: "A", url: "https://a.com", relevance_score: 0.9 },
    ];

    const sorted = sortByRelevance(sources);

    expect(sources[0].title).toBe("B"); // Original unchanged
    expect(sorted[0].title).toBe("A"); // Sorted copy
  });

  it("should maintain stable order for equal scores", () => {
    const sources: SourceCitation[] = [
      { title: "First", url: "https://first.com", relevance_score: 0.5 },
      { title: "Second", url: "https://second.com", relevance_score: 0.5 },
      { title: "Third", url: "https://third.com", relevance_score: 0.5 },
    ];

    const sorted = sortByRelevance(sources);

    // All have same score, order should be preserved
    expect(sorted[0].title).toBe("First");
    expect(sorted[1].title).toBe("Second");
    expect(sorted[2].title).toBe("Third");
  });
});

// =============================================================================
// isKBSource Tests
// =============================================================================

describe("isKBSource", () => {
  it("should return true for /kb/ URLs", () => {
    const source: SourceCitation = {
      title: "API Guide",
      url: "/kb/docs/api.md",
    };
    expect(isKBSource(source)).toBe(true);
  });

  it("should return true for kb:// protocol", () => {
    const source: SourceCitation = {
      title: "Config Reference",
      url: "kb://docs/config.md",
    };
    expect(isKBSource(source)).toBe(true);
  });

  it("should return false for web URLs", () => {
    const source: SourceCitation = {
      title: "Python Docs",
      url: "https://docs.python.org",
    };
    expect(isKBSource(source)).toBe(false);
  });

  it("should return false for empty URL", () => {
    const source: SourceCitation = {
      title: "No URL",
      url: "",
    };
    expect(isKBSource(source)).toBe(false);
  });

  it("should handle URLs with /kb in path but not at start", () => {
    const source: SourceCitation = {
      title: "External KB",
      url: "https://example.com/kb/docs",
    };
    // This is a web URL that happens to have /kb in path
    expect(isKBSource(source)).toBe(false);
  });
});

// =============================================================================
// groupSourcesByType Tests
// =============================================================================

describe("groupSourcesByType", () => {
  it("should return empty groups for empty input", () => {
    const result = groupSourcesByType([]);
    expect(result.web).toEqual([]);
    expect(result.kb).toEqual([]);
  });

  it("should group web sources correctly", () => {
    const sources: SourceCitation[] = [
      { title: "Python", url: "https://python.org" },
      { title: "Real Python", url: "https://realpython.com" },
    ];

    const result = groupSourcesByType(sources);

    expect(result.web).toHaveLength(2);
    expect(result.kb).toHaveLength(0);
  });

  it("should group KB sources correctly", () => {
    const sources: SourceCitation[] = [
      { title: "API Guide", url: "/kb/docs/api.md" },
      { title: "Config", url: "kb://config.md" },
    ];

    const result = groupSourcesByType(sources);

    expect(result.web).toHaveLength(0);
    expect(result.kb).toHaveLength(2);
  });

  it("should separate mixed sources", () => {
    const sources: SourceCitation[] = [
      { title: "Web Source", url: "https://example.com" },
      { title: "KB Source", url: "/kb/docs/guide.md" },
      { title: "Another Web", url: "https://other.com" },
    ];

    const result = groupSourcesByType(sources);

    expect(result.web).toHaveLength(2);
    expect(result.kb).toHaveLength(1);
    expect(result.web[0].title).toBe("Web Source");
    expect(result.kb[0].title).toBe("KB Source");
  });

  it("should preserve order within groups", () => {
    const sources: SourceCitation[] = [
      { title: "Web 1", url: "https://a.com" },
      { title: "KB 1", url: "/kb/a.md" },
      { title: "Web 2", url: "https://b.com" },
      { title: "KB 2", url: "/kb/b.md" },
    ];

    const result = groupSourcesByType(sources);

    expect(result.web.map((s) => s.title)).toEqual(["Web 1", "Web 2"]);
    expect(result.kb.map((s) => s.title)).toEqual(["KB 1", "KB 2"]);
  });
});
