/**
 * Tests for remarkReferences plugin
 *
 * TDD: Tests written first per project guidelines.
 */

import { describe, it, expect } from 'vitest';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkStringify from 'remark-stringify';
import { remarkReferences } from './remarkReferences';

/**
 * Helper to process markdown through the remarkReferences plugin.
 */
async function processMarkdown(markdown: string): Promise<string> {
  const result = await unified()
    .use(remarkParse)
    .use(remarkReferences)
    .use(remarkStringify)
    .process(markdown);
  return String(result);
}

describe('remarkReferences', () => {
  describe('tool references', () => {
    it('should transform [[tool:server:name]] to link node', async () => {
      const input = 'Use [[tool:filesystem:read_file]] to read files.';
      const output = await processMarkdown(input);
      // Note: remark-stringify may escape underscores, so check for the URL
      expect(output).toContain('ref://tool/filesystem:read_file');
      expect(output).toContain('read_file'); // label (may be escaped as read\_file)
    });

    it('should handle custom label [[tool:server:name|Label]]', async () => {
      const input = 'Use [[tool:filesystem:read_file|Read File Tool]] for reading.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Read File Tool](ref://tool/filesystem:read_file');
    });

    it('should handle underscores in tool names', async () => {
      const input = 'Check [[tool:code_sandbox:execute_python]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/code_sandbox:execute_python');
    });

    it('should handle hyphens in server names', async () => {
      const input = 'Use [[tool:my-server:my-tool]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/my-server:my-tool');
    });
  });

  describe('skill references', () => {
    it('should transform [[skill:name]] to link node', async () => {
      const input = 'Apply [[skill:code-review]] to check code.';
      const output = await processMarkdown(input);
      expect(output).toContain('[code-review](ref://skill/code-review)');
    });

    it('should handle skill with custom label', async () => {
      const input = 'Use [[skill:summarize|Summary Skill]] for brevity.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Summary Skill](ref://skill/summarize');
    });

    it('should handle skill names with underscores', async () => {
      const input = 'Run [[skill:data_analysis]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://skill/data_analysis');
    });
  });

  describe('artifact references', () => {
    it('should transform [[artifact:id]] to link node', async () => {
      const input = 'See [[artifact:abc-123-def]] for the chart.';
      const output = await processMarkdown(input);
      expect(output).toContain('[abc-123-def](ref://artifact/abc-123-def)');
    });

    it('should handle artifact with custom label', async () => {
      const input = 'View [[artifact:chart-001|Sales Chart]] in canvas.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Sales Chart](ref://artifact/chart-001');
    });

    it('should handle UUID-style artifact IDs', async () => {
      const input = 'Check [[artifact:550e8400-e29b-41d4-a716-446655440000]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://artifact/550e8400-e29b-41d4-a716-446655440000');
    });
  });

  describe('memory references (Phase 4)', () => {
    it('should transform [[memory:id]] to link node', async () => {
      const input = 'See [[memory:note-abc-123]] for context.';
      const output = await processMarkdown(input);
      expect(output).toContain('[note-abc-123](ref://memory/note-abc-123)');
    });

    it('should handle memory with custom label', async () => {
      const input = 'Refer to [[memory:note-1|Meeting Notes]] for details.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Meeting Notes](ref://memory/note-1');
    });

    it('should handle UUID-style memory IDs', async () => {
      const input = 'Check [[memory:550e8400-e29b-41d4-a716-446655440000]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://memory/550e8400-e29b-41d4-a716-446655440000');
    });
  });

  describe('plan references (Phase 4)', () => {
    it('should transform [[plan:id]] to link node', async () => {
      const input = 'Follow [[plan:plan-xyz-789]] for implementation.';
      const output = await processMarkdown(input);
      expect(output).toContain('[plan-xyz-789](ref://plan/plan-xyz-789)');
    });

    it('should handle plan with custom label', async () => {
      const input = 'Execute [[plan:plan-1|Refactoring Plan]] next.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Refactoring Plan](ref://plan/plan-1');
    });

    it('should handle complex plan IDs', async () => {
      const input = 'See [[plan:exec-plan-2025-01]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://plan/exec-plan-2025-01');
    });
  });

  describe('multiple references', () => {
    it('should transform multiple references in one paragraph', async () => {
      const input = 'Use [[tool:fs:read]] and [[skill:analyze]] together.';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/fs:read');
      expect(output).toContain('ref://skill/analyze');
    });

    it('should transform references across multiple lines', async () => {
      const input = `First use [[tool:a:b]].

Then apply [[skill:c]].

Finally see [[artifact:d]].`;
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/a:b');
      expect(output).toContain('ref://skill/c');
      expect(output).toContain('ref://artifact/d');
    });
  });

  describe('code block exclusion', () => {
    it('should NOT transform references in fenced code blocks', async () => {
      const input = `Here is code:

\`\`\`javascript
const ref = "[[tool:fs:read]]";
\`\`\`

That was code.`;
      const output = await processMarkdown(input);
      // The reference inside code block should remain as-is
      expect(output).toContain('[[tool:fs:read]]');
      expect(output).not.toContain('ref://tool/fs:read');
    });

    it('should NOT transform references in inline code', async () => {
      const input = 'Use `[[tool:fs:read]]` for reading files.';
      const output = await processMarkdown(input);
      // Inline code preserves the raw text
      expect(output).toContain('`[[tool:fs:read]]`');
    });
  });

  describe('edge cases', () => {
    it('should handle reference at start of text', async () => {
      const input = '[[tool:a:b]] is a tool.';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/a:b');
    });

    it('should handle reference at end of text', async () => {
      const input = 'Use this: [[tool:a:b]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/a:b');
    });

    it('should handle adjacent references', async () => {
      const input = '[[tool:a:b]][[skill:c]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/a:b');
      expect(output).toContain('ref://skill/c');
    });

    it('should not transform invalid reference types', async () => {
      const input = 'This [[unknown:foo]] is not valid.';
      const output = await processMarkdown(input);
      // Should NOT be transformed to a link (no ref:// URL)
      expect(output).not.toContain('ref://');
      // Text remains (brackets may be escaped by remark-stringify)
      expect(output).toContain('unknown:foo');
    });

    it('should not transform malformed references', async () => {
      const input = 'This [[tool:]] is incomplete.';
      const output = await processMarkdown(input);
      // Should NOT be transformed to a link (no ref:// URL)
      expect(output).not.toContain('ref://');
      // Text remains (brackets may be escaped by remark-stringify)
      expect(output).toContain('tool:');
    });

    it('should handle empty label gracefully', async () => {
      const input = 'Use [[tool:fs:read|]] for reading.';
      const output = await processMarkdown(input);
      // Empty label should use the id as label
      expect(output).toContain('ref://tool/fs:read');
    });

    it('should handle special characters in labels', async () => {
      const input = 'Use [[skill:analyze|Data & Stats Analysis]] for insights.';
      const output = await processMarkdown(input);
      expect(output).toContain('Data & Stats Analysis');
    });
  });

  describe('mixed content', () => {
    it('should work with other markdown elements', async () => {
      const input = `# Heading

Use **bold** and [[tool:fs:read]] together.

- List item with [[skill:analyze]]
- Another item

> Quote with [[artifact:chart-1]]`;
      const output = await processMarkdown(input);
      expect(output).toContain('ref://tool/fs:read');
      expect(output).toContain('ref://skill/analyze');
      expect(output).toContain('ref://artifact/chart-1');
    });

    it('should not interfere with existing links', async () => {
      const input = 'Visit [Google](https://google.com) and use [[tool:fs:read]].';
      const output = await processMarkdown(input);
      expect(output).toContain('[Google](https://google.com)');
      expect(output).toContain('ref://tool/fs:read');
    });
  });

  describe('version-pinned skill references (Deferred)', () => {
    it('should transform [[skill:name@version]] to link node', async () => {
      const input = 'Use [[skill:code-review@1.2.0]] for this PR.';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://skill/code-review@1.2.0');
    });

    it('should handle version-pinned skill with custom label', async () => {
      const input = 'Apply [[skill:summarize@2.0.0|Summary v2]] for the report.';
      const output = await processMarkdown(input);
      expect(output).toContain('[Summary v2](ref://skill/summarize@2.0.0');
    });

    it('should handle semver versions with major.minor.patch', async () => {
      const input = 'Use [[skill:analyzer@10.20.30]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://skill/analyzer@10.20.30');
    });

    it('should handle version with prerelease suffix', async () => {
      const input = 'Try [[skill:beta-feature@1.0.0-beta.1]]';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://skill/beta-feature@1.0.0-beta.1');
    });

    it('should extract just skill name for display when no label', async () => {
      const input = 'Use [[skill:code-review@1.2.0]]';
      const output = await processMarkdown(input);
      // Display text should be skill name without version
      expect(output).toContain('[code-review](ref://skill/code-review@1.2.0)');
    });

    it('should work alongside non-versioned skill refs', async () => {
      const input = 'Compare [[skill:analyze]] with [[skill:analyze@2.0.0]].';
      const output = await processMarkdown(input);
      expect(output).toContain('ref://skill/analyze)');
      expect(output).toContain('ref://skill/analyze@2.0.0)');
    });
  });
});
