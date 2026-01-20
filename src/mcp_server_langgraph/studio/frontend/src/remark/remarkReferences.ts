/**
 * Remark plugin for parsing [[type:qualifier:id]] reference syntax.
 *
 * Transforms markdown references into link nodes with ref:// URLs.
 * These links are then rendered as ReferenceChip components by MarkdownContent.
 *
 * Syntax:
 * - [[tool:server:tool_name]] - MCP tool reference
 * - [[tool:server:tool_name|Custom Label]] - With custom label
 * - [[skill:skill-name]] - Skill reference
 * - [[artifact:artifact-id]] - Artifact reference
 *
 * Output:
 * - Link nodes with href="ref://type/qualifier:id" (for tools)
 * - Link nodes with href="ref://type/id" (for skills/artifacts)
 * - Title attribute contains custom label if provided
 */

import { visit } from 'unist-util-visit';
import type { Plugin } from 'unified';
import type { Text, Link, Root, Parent } from 'mdast';

/**
 * Regex to match [[type:qualifier:id]] or [[type:id]] patterns.
 *
 * Groups:
 * 1. type: tool, skill, artifact, memory, or plan
 * 2. id: The full identifier (may contain colons for tools, @version for skills)
 * 3. label: Optional custom label after |
 *
 * For tools: [[tool:server:name]] -> type=tool, id=server:name
 * For skills: [[skill:name]] -> type=skill, id=name
 * For skills: [[skill:name@1.2.0]] -> type=skill, id=name@1.2.0 (version-pinned)
 * For artifacts: [[artifact:id]] -> type=artifact, id=id
 * For memory: [[memory:id]] -> type=memory, id=id (Phase 4)
 * For plans: [[plan:id]] -> type=plan, id=id (Phase 4)
 */
const REFERENCE_REGEX =
  /\[\[(tool|skill|artifact|memory|plan):([a-zA-Z0-9_:/@.-]+)(?:\|([^\]]*))?\]\]/g;

/**
 * Validate that a reference has the correct format.
 * - Tools must have server:name format
 * - Skills/artifacts just need an id
 */
function isValidReference(type: string, id: string): boolean {
  if (type === 'tool') {
    // Tools require at least one colon (server:name)
    return id.includes(':') && !id.endsWith(':') && !id.startsWith(':');
  }
  // Skills and artifacts just need a non-empty id
  return id.length > 0;
}

/**
 * Build the ref:// URL for a reference.
 *
 * Format:
 * - Tools: ref://tool/server:name
 * - Skills: ref://skill/name
 * - Artifacts: ref://artifact/id
 */
function buildRefUrl(type: string, id: string): string {
  return `ref://${type}/${id}`;
}

/**
 * Extract display text from a reference.
 *
 * @param label - Custom label if provided
 * @param type - Reference type
 * @param id - Reference id
 * @returns Display text for the link
 */
function getDisplayText(
  label: string | undefined,
  type: string,
  id: string
): string {
  // Use custom label if provided and non-empty
  if (label && label.trim()) {
    return label.trim();
  }
  // For tools, extract just the tool name (after the last colon)
  if (type === 'tool' && id.includes(':')) {
    const parts = id.split(':');
    return parts[parts.length - 1];
  }
  // For version-pinned skills, strip the @version suffix for display
  if (type === 'skill' && id.includes('@')) {
    return id.split('@')[0];
  }
  // For skills/artifacts, use the id
  return id;
}

/**
 * Remark plugin to transform [[type:qualifier:id]] references to link nodes.
 *
 * The plugin:
 * 1. Visits all text nodes
 * 2. Skips code blocks and inline code (preserves raw text)
 * 3. Matches [[type:id]] patterns
 * 4. Replaces with link nodes having href="ref://type/id"
 */
export const remarkReferences: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, 'text', (node: Text, index: number | undefined, parent: Parent | undefined) => {
      // Safety checks
      if (!parent || index === undefined) return;

      // Skip code blocks (parent is 'code') and inline code (parent is 'inlineCode')
      // Also check grandparent for code context
      if (parent.type === 'code' || parent.type === 'inlineCode') {
        return;
      }

      const text = node.value;
      const matches = [...text.matchAll(REFERENCE_REGEX)];

      if (matches.length === 0) {
        return;
      }

      // Build new nodes to replace the text node
      const newNodes: (Text | Link)[] = [];
      let lastIndex = 0;

      for (const match of matches) {
        const [fullMatch, type, id, label] = match;
        const startIndex = match.index!;

        // Skip invalid references (leave as plain text)
        if (!isValidReference(type, id)) {
          continue;
        }

        // Add text before this match
        if (startIndex > lastIndex) {
          newNodes.push({
            type: 'text',
            value: text.slice(lastIndex, startIndex),
          });
        }

        // Create link node with ref:// URL
        const displayText = getDisplayText(label, type, id);
        const url = buildRefUrl(type, id);

        const linkNode: Link = {
          type: 'link',
          url,
          title: label?.trim() || null,
          children: [{ type: 'text', value: displayText }],
        };

        newNodes.push(linkNode);
        lastIndex = startIndex + fullMatch.length;
      }

      // If no valid matches were found, don't modify the node
      if (newNodes.length === 0) {
        return;
      }

      // Add remaining text after last match
      if (lastIndex < text.length) {
        newNodes.push({
          type: 'text',
          value: text.slice(lastIndex),
        });
      }

      // Replace the original text node with the new nodes
      parent.children.splice(index, 1, ...newNodes);

      // Return the index to skip processing of newly inserted nodes
      // This prevents infinite loops and double-processing
      return index + newNodes.length;
    });
  };
};
