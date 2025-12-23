/**
 * usePromptTemplates Tests
 *
 * TDD tests for prompt templates functionality.
 * Tests cover:
 * - Template library management
 * - Custom template creation
 * - Template variables
 * - Template application
 * - Template persistence
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { usePromptTemplates } from "./usePromptTemplates";

describe("usePromptTemplates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("initialization", () => {
    it("should initialize with default templates", () => {
      const { result } = renderHook(() => usePromptTemplates());

      expect(result.current.templates.length).toBeGreaterThan(0);
    });

    it("should have template categories", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const categories = result.current.getCategories();
      expect(categories.length).toBeGreaterThan(0);
    });

    it("should have default templates with required fields", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];
      expect(template.id).toBeDefined();
      expect(template.name).toBeDefined();
      expect(template.content).toBeDefined();
      expect(template.category).toBeDefined();
    });
  });

  describe("template retrieval", () => {
    it("should get template by ID", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];
      const retrieved = result.current.getTemplateById(template.id);

      expect(retrieved).toEqual(template);
    });

    it("should return undefined for non-existent ID", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const retrieved = result.current.getTemplateById("non-existent");
      expect(retrieved).toBeUndefined();
    });

    it("should filter templates by category", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const categories = result.current.getCategories();
      if (categories.length > 0) {
        const filtered = result.current.getTemplatesByCategory(categories[0]);
        filtered.forEach((template) => {
          expect(template.category).toBe(categories[0]);
        });
      }
    });

    it("should search templates by name", () => {
      const { result } = renderHook(() => usePromptTemplates());

      act(() => {
        result.current.createTemplate({
          name: "Code Review Template",
          content: "Review this code: {{code}}",
          category: "development",
        });
      });

      const searchResults = result.current.searchTemplates("code review");
      expect(searchResults.length).toBeGreaterThan(0);
      expect(searchResults[0].name.toLowerCase().includes("code review")).toBe(
        true,
      );
    });

    it("should search templates by content", () => {
      const { result } = renderHook(() => usePromptTemplates());

      act(() => {
        result.current.createTemplate({
          name: "Bug Fix",
          content: "Find and fix the bug in this function",
          category: "development",
        });
      });

      const searchResults = result.current.searchTemplates("bug");
      expect(searchResults.length).toBeGreaterThan(0);
    });
  });

  describe("custom template creation", () => {
    it("should create a custom template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const initialCount = result.current.templates.length;

      act(() => {
        result.current.createTemplate({
          name: "My Custom Template",
          content: "Hello, {{name}}!",
          category: "custom",
        });
      });

      expect(result.current.templates.length).toBe(initialCount + 1);
    });

    it("should assign unique ID to new template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let template1Id: string = "";
      let template2Id: string = "";

      act(() => {
        template1Id = result.current.createTemplate({
          name: "Template 1",
          content: "Content 1",
          category: "custom",
        });
      });

      act(() => {
        template2Id = result.current.createTemplate({
          name: "Template 2",
          content: "Content 2",
          category: "custom",
        });
      });

      expect(template1Id).not.toBe(template2Id);
    });

    it("should mark custom templates as not built-in", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let templateId: string = "";

      act(() => {
        templateId = result.current.createTemplate({
          name: "Custom Template",
          content: "Custom content",
          category: "custom",
        });
      });

      const template = result.current.getTemplateById(templateId);
      expect(template?.isBuiltIn).toBe(false);
    });

    it("should include description if provided", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let templateId: string = "";

      act(() => {
        templateId = result.current.createTemplate({
          name: "Described Template",
          content: "Content",
          category: "custom",
          description: "This is a helpful description",
        });
      });

      const template = result.current.getTemplateById(templateId);
      expect(template?.description).toBe("This is a helpful description");
    });
  });

  describe("template variables", () => {
    it("should extract variables from template content", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const variables = result.current.extractVariables(
        "Hello {{name}}, your order {{orderId}} is ready!",
      );

      expect(variables).toContain("name");
      expect(variables).toContain("orderId");
      expect(variables).toHaveLength(2);
    });

    it("should handle templates with no variables", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const variables = result.current.extractVariables(
        "This is a static template with no variables.",
      );

      expect(variables).toHaveLength(0);
    });

    it("should apply variable values to template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const applied = result.current.applyVariables(
        "Hello {{name}}, welcome to {{place}}!",
        { name: "Alice", place: "Wonderland" },
      );

      expect(applied).toBe("Hello Alice, welcome to Wonderland!");
    });

    it("should leave unmatched variables in place", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const applied = result.current.applyVariables(
        "Hello {{name}}, your age is {{age}}!",
        { name: "Bob" },
      );

      expect(applied).toBe("Hello Bob, your age is {{age}}!");
    });

    it("should handle multiple occurrences of same variable", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const applied = result.current.applyVariables(
        "{{name}} said hello to {{name}}",
        { name: "Charlie" },
      );

      expect(applied).toBe("Charlie said hello to Charlie");
    });
  });

  describe("template updates", () => {
    it("should update template name", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let templateId: string = "";

      act(() => {
        templateId = result.current.createTemplate({
          name: "Original Name",
          content: "Content",
          category: "custom",
        });
      });

      act(() => {
        result.current.updateTemplate(templateId, { name: "New Name" });
      });

      const template = result.current.getTemplateById(templateId);
      expect(template?.name).toBe("New Name");
    });

    it("should update template content", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let templateId: string = "";

      act(() => {
        templateId = result.current.createTemplate({
          name: "Template",
          content: "Original content",
          category: "custom",
        });
      });

      act(() => {
        result.current.updateTemplate(templateId, { content: "New content" });
      });

      const template = result.current.getTemplateById(templateId);
      expect(template?.content).toBe("New content");
    });

    it("should return false when updating non-existent template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let success: boolean = true;

      act(() => {
        success = result.current.updateTemplate("non-existent", {
          name: "New Name",
        });
      });

      expect(success).toBe(false);
    });

    it("should not allow updating built-in templates", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const builtInTemplate = result.current.templates.find((t) => t.isBuiltIn);
      if (builtInTemplate) {
        let success: boolean = true;

        act(() => {
          success = result.current.updateTemplate(builtInTemplate.id, {
            name: "Hacked Name",
          });
        });

        expect(success).toBe(false);
        expect(result.current.getTemplateById(builtInTemplate.id)?.name).toBe(
          builtInTemplate.name,
        );
      }
    });
  });

  describe("template deletion", () => {
    it("should delete custom template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let templateId: string = "";

      act(() => {
        templateId = result.current.createTemplate({
          name: "Deletable Template",
          content: "Content",
          category: "custom",
        });
      });

      const countBefore = result.current.templates.length;

      act(() => {
        result.current.deleteTemplate(templateId);
      });

      expect(result.current.templates.length).toBe(countBefore - 1);
      expect(result.current.getTemplateById(templateId)).toBeUndefined();
    });

    it("should not delete built-in templates", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const builtInTemplate = result.current.templates.find((t) => t.isBuiltIn);
      if (builtInTemplate) {
        let success: boolean = true;

        act(() => {
          success = result.current.deleteTemplate(builtInTemplate.id);
        });

        expect(success).toBe(false);
        expect(
          result.current.getTemplateById(builtInTemplate.id),
        ).toBeDefined();
      }
    });

    it("should return false when deleting non-existent template", () => {
      const { result } = renderHook(() => usePromptTemplates());

      let success: boolean = true;

      act(() => {
        success = result.current.deleteTemplate("non-existent");
      });

      expect(success).toBe(false);
    });
  });

  describe("favorites", () => {
    it("should add template to favorites", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];

      act(() => {
        result.current.addToFavorites(template.id);
      });

      expect(result.current.favorites).toContain(template.id);
    });

    it("should remove template from favorites", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];

      act(() => {
        result.current.addToFavorites(template.id);
      });

      act(() => {
        result.current.removeFromFavorites(template.id);
      });

      expect(result.current.favorites).not.toContain(template.id);
    });

    it("should check if template is favorite", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];

      expect(result.current.isFavorite(template.id)).toBe(false);

      act(() => {
        result.current.addToFavorites(template.id);
      });

      expect(result.current.isFavorite(template.id)).toBe(true);
    });

    it("should get favorite templates", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template1 = result.current.templates[0];
      const template2 = result.current.templates[1];

      act(() => {
        result.current.addToFavorites(template1.id);
        result.current.addToFavorites(template2.id);
      });

      const favTemplates = result.current.getFavoriteTemplates();
      expect(favTemplates).toHaveLength(2);
    });
  });

  describe("recent usage", () => {
    it("should track recent template usage", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template = result.current.templates[0];

      act(() => {
        result.current.markAsUsed(template.id);
      });

      expect(result.current.recentlyUsed).toContain(template.id);
    });

    it("should get recently used templates", () => {
      const { result } = renderHook(() => usePromptTemplates());

      const template1 = result.current.templates[0];
      const template2 = result.current.templates[1];

      act(() => {
        result.current.markAsUsed(template1.id);
        result.current.markAsUsed(template2.id);
      });

      const recent = result.current.getRecentlyUsedTemplates();
      expect(recent.length).toBeGreaterThan(0);
    });

    it("should limit recently used to 10 items", () => {
      const { result } = renderHook(() => usePromptTemplates());

      // Add more than 10 templates to recently used
      act(() => {
        for (let i = 0; i < 15; i++) {
          const id = result.current.createTemplate({
            name: `Template ${i}`,
            content: `Content ${i}`,
            category: "custom",
          });
          result.current.markAsUsed(id);
        }
      });

      expect(result.current.recentlyUsed.length).toBeLessThanOrEqual(10);
    });
  });
});
