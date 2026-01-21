/**
 * Tests for Button Semantics Codemod
 *
 * TDD: Write tests first, then implement the codemod
 *
 * This codemod adds semantic variants to Button components based on:
 * 1. Button text content (Delete -> danger, Cancel -> secondary)
 * 2. Icon type (Trash -> danger)
 * 3. Default fallback (primary for action buttons)
 */

import { describe, it, expect } from "vitest";
import jscodeshift, { type API } from "jscodeshift";
import transform from "../../scripts/codemods/fix-button-semantics.js";

const j = jscodeshift.withParser("tsx");

const api: API = {
  jscodeshift: j,
  j,
  stats: () => {},
  report: () => {},
};

function runTransform(source: string, path = "test.tsx"): string | null {
  return transform({ source, path }, api, {});
}

describe("fix-button-semantics codemod", () => {
  describe("danger variant detection", () => {
    it("should add variant='danger' to Delete buttons", () => {
      const input = `<Button onClick={handleDelete}>Delete</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to Remove buttons", () => {
      const input = `<Button onClick={handleRemove}>Remove</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to Clear buttons", () => {
      const input = `<Button>Clear All</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to Destroy buttons", () => {
      const input = `<Button>Destroy</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to Discard buttons", () => {
      const input = `<Button>Discard Changes</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to buttons with Trash icon", () => {
      const input = `<Button size="icon"><Trash2 className="w-4 h-4" /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should add variant='danger' to buttons with TrashIcon", () => {
      const input = `<Button><TrashIcon /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });
  });

  describe("secondary variant detection", () => {
    it("should add variant='secondary' to Cancel buttons", () => {
      const input = `<Button onClick={handleCancel}>Cancel</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });

    it("should add variant='secondary' to Close buttons", () => {
      const input = `<Button onClick={onClose}>Close</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });

    it("should add variant='secondary' to Back buttons", () => {
      const input = `<Button onClick={goBack}>Back</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });

    it("should add variant='secondary' to Dismiss buttons", () => {
      const input = `<Button>Dismiss</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });

    it("should add variant='secondary' to No buttons (exact match)", () => {
      const input = `<Button>No</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });

    it("should NOT add secondary to buttons starting with No (like 'Notes')", () => {
      const input = `<Button>Notes</Button>`;
      const result = runTransform(input);
      expect(result).not.toContain('variant="secondary"');
    });

    it("should add variant='secondary' to buttons with X/Close icon", () => {
      const input = `<Button size="icon"><X className="w-4 h-4" /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="secondary"');
    });
  });

  describe("primary variant detection", () => {
    it("should add variant='primary' to Submit buttons", () => {
      const input = `<Button type="submit">Submit</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Save buttons", () => {
      const input = `<Button onClick={handleSave}>Save</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Create buttons", () => {
      const input = `<Button>Create New</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Add buttons", () => {
      const input = `<Button>Add Item</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Confirm buttons", () => {
      const input = `<Button>Confirm</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Continue buttons", () => {
      const input = `<Button>Continue</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to Yes buttons", () => {
      const input = `<Button>Yes</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to buttons with Plus icon", () => {
      const input = `<Button><Plus /> Add</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });
  });

  describe("ghost variant detection", () => {
    it("should add variant='ghost' to icon-only buttons without semantics", () => {
      const input = `<Button size="icon"><Settings /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="ghost"');
    });

    it("should add variant='ghost' to buttons with ChevronLeft icon", () => {
      const input = `<Button size="icon"><ChevronLeft /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="ghost"');
    });

    it("should add variant='ghost' to buttons with Menu/Hamburger icon", () => {
      const input = `<Button size="icon"><Menu /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="ghost"');
    });

    it("should add variant='ghost' to buttons with MoreVertical icon", () => {
      const input = `<Button size="icon"><MoreVertical /></Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="ghost"');
    });
  });

  describe("preserves existing variants", () => {
    it("should not modify buttons that already have variant prop", () => {
      const input = `<Button variant="success" onClick={handleSave}>Delete</Button>`;
      const result = runTransform(input);
      // Should return null (no changes) since button already has variant
      expect(result).toBeNull();
    });

    it("should not modify buttons with dynamic variant", () => {
      const input = `<Button variant={buttonVariant}>Delete</Button>`;
      const result = runTransform(input);
      // Should return null (no changes) since button already has variant
      expect(result).toBeNull();
    });
  });

  describe("edge cases", () => {
    it("should handle buttons with mixed content (text + icon)", () => {
      const input = `<Button><Trash2 /> Delete Item</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should handle buttons with JSX expressions in children", () => {
      const input = `<Button>{isLoading ? 'Loading...' : 'Delete'}</Button>`;
      const result = runTransform(input);
      // Should detect 'Delete' in the expression
      expect(result).toContain('variant="danger"');
    });

    it("should handle self-closing Button with aria-label", () => {
      const input = `<Button size="icon" aria-label="Delete item" />`;
      const result = runTransform(input);
      expect(result).toContain('variant="danger"');
    });

    it("should skip test files", () => {
      const input = `<Button>Delete</Button>`;
      const result = runTransform(input, "Component.test.tsx");
      expect(result).toBeNull();
    });

    it("should skip story files", () => {
      const input = `<Button>Delete</Button>`;
      const result = runTransform(input, "Component.stories.tsx");
      expect(result).toBeNull();
    });

    it("should skip UI component definitions", () => {
      const input = `<Button>Delete</Button>`;
      const result = runTransform(input, "src/components/UI/SomeComponent.tsx");
      expect(result).toBeNull();
    });

    it("should return null if no changes needed", () => {
      const input = `const x = 1;`;
      const result = runTransform(input);
      expect(result).toBeNull();
    });

    it("should handle buttons with no content (empty)", () => {
      const input = `<Button size="icon"></Button>`;
      const result = runTransform(input);
      // Icon buttons without recognizable content should get ghost
      expect(result).toContain('variant="ghost"');
    });
  });

  describe("fallback behavior", () => {
    it("should add variant='primary' to generic action buttons", () => {
      const input = `<Button onClick={handleAction}>Apply Changes</Button>`;
      const result = runTransform(input);
      expect(result).toContain('variant="primary"');
    });

    it("should add variant='primary' to buttons with non-semantic text", () => {
      const input = `<Button>Process Data</Button>`;
      const result = runTransform(input);
      // Default to primary for action buttons
      expect(result).toContain('variant="primary"');
    });
  });
});
