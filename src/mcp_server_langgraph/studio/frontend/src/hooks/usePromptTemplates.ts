/**
 * usePromptTemplates Hook
 *
 * Manages prompt templates for quick access to common prompts.
 * Features:
 * - Built-in template library
 * - Custom template creation
 * - Template variables with substitution
 * - Category and search filtering
 * - Favorites and recent usage tracking
 * - Persistence to localStorage
 */

import { useState, useCallback, useMemo } from "react";
import { storage, STORAGE_KEYS } from "../utils/storage";

// ==============================================================================
// Types
// ==============================================================================

export interface PromptTemplate {
  /** Unique template identifier */
  id: string;
  /** Display name */
  name: string;
  /** Template content with optional {{variables}} */
  content: string;
  /** Category for grouping */
  category: string;
  /** Optional description */
  description?: string;
  /** Whether this is a built-in template */
  isBuiltIn: boolean;
  /** Creation timestamp */
  createdAt: number;
}

export interface TemplateInput {
  name: string;
  content: string;
  category: string;
  description?: string;
}

export interface PromptTemplatesState {
  /** All available templates */
  templates: PromptTemplate[];
  /** Favorite template IDs */
  favorites: string[];
  /** Recently used template IDs */
  recentlyUsed: string[];
  /** Get all unique categories */
  getCategories: () => string[];
  /** Get template by ID */
  getTemplateById: (id: string) => PromptTemplate | undefined;
  /** Get templates by category */
  getTemplatesByCategory: (category: string) => PromptTemplate[];
  /** Search templates by name or content */
  searchTemplates: (query: string) => PromptTemplate[];
  /** Create a new custom template */
  createTemplate: (input: TemplateInput) => string;
  /** Update an existing template */
  updateTemplate: (id: string, updates: Partial<TemplateInput>) => boolean;
  /** Delete a template */
  deleteTemplate: (id: string) => boolean;
  /** Extract variables from template content */
  extractVariables: (content: string) => string[];
  /** Apply variable values to template */
  applyVariables: (
    content: string,
    variables: Record<string, string>,
  ) => string;
  /** Add template to favorites */
  addToFavorites: (id: string) => void;
  /** Remove template from favorites */
  removeFromFavorites: (id: string) => void;
  /** Check if template is favorite */
  isFavorite: (id: string) => boolean;
  /** Get favorite templates */
  getFavoriteTemplates: () => PromptTemplate[];
  /** Mark template as used */
  markAsUsed: (id: string) => void;
  /** Get recently used templates */
  getRecentlyUsedTemplates: () => PromptTemplate[];
}

// ==============================================================================
// Constants
// ==============================================================================

// Use centralized storage key for templates, with custom keys for sub-categories
const STORAGE_KEY_TEMPLATES = STORAGE_KEYS.PROMPT_TEMPLATES;
const STORAGE_KEY_FAVORITES = "studio-prompt-templates-favorites";
const STORAGE_KEY_RECENT = "studio-prompt-templates-recent";
const MAX_RECENT = 10;

// Built-in templates
const BUILT_IN_TEMPLATES: PromptTemplate[] = [
  {
    id: "builtin-explain-code",
    name: "Explain Code",
    content:
      "Please explain the following code in detail:\n\n```\n{{code}}\n```\n\nExplain what it does, how it works, and any potential issues.",
    category: "development",
    description: "Get a detailed explanation of any code snippet",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-fix-bug",
    name: "Fix Bug",
    content:
      "I have a bug in my code:\n\n```\n{{code}}\n```\n\nThe error is: {{error}}\n\nPlease help me fix this bug.",
    category: "development",
    description: "Get help fixing a bug in your code",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-write-tests",
    name: "Write Tests",
    content:
      "Please write comprehensive unit tests for the following code:\n\n```\n{{code}}\n```\n\nInclude edge cases and error scenarios.",
    category: "development",
    description: "Generate unit tests for your code",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-refactor",
    name: "Refactor Code",
    content:
      "Please refactor the following code to improve readability and maintainability:\n\n```\n{{code}}\n```\n\nExplain your changes.",
    category: "development",
    description: "Improve code quality through refactoring",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-summarize",
    name: "Summarize Text",
    content:
      "Please summarize the following text in {{length}} sentences:\n\n{{text}}",
    category: "writing",
    description: "Get a concise summary of any text",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-translate",
    name: "Translate",
    content: "Please translate the following text to {{language}}:\n\n{{text}}",
    category: "writing",
    description: "Translate text to another language",
    isBuiltIn: true,
    createdAt: 0,
  },
  {
    id: "builtin-brainstorm",
    name: "Brainstorm Ideas",
    content:
      "Please brainstorm {{count}} creative ideas for: {{topic}}\n\nProvide a brief description for each idea.",
    category: "creative",
    description: "Generate creative ideas for any topic",
    isBuiltIn: true,
    createdAt: 0,
  },
];

// ==============================================================================
// Helper Functions
// ==============================================================================

function generateTemplateId(): string {
  return `template-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function loadFromStorage<T>(key: string, defaultValue: T): T {
  return storage.get<T>(key) ?? defaultValue;
}

function saveToStorage<T>(key: string, value: T): void {
  storage.set(key, value);
}

// ==============================================================================
// Hook
// ==============================================================================

export function usePromptTemplates(): PromptTemplatesState {
  // Load custom templates from storage
  const [customTemplates, setCustomTemplates] = useState<PromptTemplate[]>(() =>
    loadFromStorage<PromptTemplate[]>(STORAGE_KEY_TEMPLATES, []),
  );

  // Load favorites from storage
  const [favorites, setFavorites] = useState<string[]>(() =>
    loadFromStorage<string[]>(STORAGE_KEY_FAVORITES, []),
  );

  // Load recently used from storage
  const [recentlyUsed, setRecentlyUsed] = useState<string[]>(() =>
    loadFromStorage<string[]>(STORAGE_KEY_RECENT, []),
  );

  // Combine built-in and custom templates
  const templates = useMemo(
    () => [...BUILT_IN_TEMPLATES, ...customTemplates],
    [customTemplates],
  );

  // Get all unique categories
  const getCategories = useCallback((): string[] => {
    const categorySet = new Set<string>();
    templates.forEach((t) => categorySet.add(t.category));
    return Array.from(categorySet).sort();
  }, [templates]);

  // Get template by ID
  const getTemplateById = useCallback(
    (id: string): PromptTemplate | undefined => {
      return templates.find((t) => t.id === id);
    },
    [templates],
  );

  // Get templates by category
  const getTemplatesByCategory = useCallback(
    (category: string): PromptTemplate[] => {
      return templates.filter((t) => t.category === category);
    },
    [templates],
  );

  // Search templates
  const searchTemplates = useCallback(
    (query: string): PromptTemplate[] => {
      const lowerQuery = query.toLowerCase();
      return templates.filter(
        (t) =>
          t.name.toLowerCase().includes(lowerQuery) ||
          t.content.toLowerCase().includes(lowerQuery) ||
          t.description?.toLowerCase().includes(lowerQuery),
      );
    },
    [templates],
  );

  // Create a new template
  const createTemplate = useCallback((input: TemplateInput): string => {
    const id = generateTemplateId();
    const newTemplate: PromptTemplate = {
      id,
      name: input.name,
      content: input.content,
      category: input.category,
      description: input.description,
      isBuiltIn: false,
      createdAt: Date.now(),
    };

    setCustomTemplates((prev) => {
      const updated = [...prev, newTemplate];
      saveToStorage(STORAGE_KEY_TEMPLATES, updated);
      return updated;
    });

    return id;
  }, []);

  // Update an existing template
  const updateTemplate = useCallback(
    (id: string, updates: Partial<TemplateInput>): boolean => {
      // Check if template exists and is not built-in
      const template = templates.find((t) => t.id === id);
      if (!template || template.isBuiltIn) return false;

      setCustomTemplates((prev) => {
        const updated = prev.map((t) =>
          t.id === id
            ? {
                ...t,
                ...(updates.name !== undefined && { name: updates.name }),
                ...(updates.content !== undefined && {
                  content: updates.content,
                }),
                ...(updates.category !== undefined && {
                  category: updates.category,
                }),
                ...(updates.description !== undefined && {
                  description: updates.description,
                }),
              }
            : t,
        );
        saveToStorage(STORAGE_KEY_TEMPLATES, updated);
        return updated;
      });

      return true;
    },
    [templates],
  );

  // Delete a template
  const deleteTemplate = useCallback(
    (id: string): boolean => {
      const template = templates.find((t) => t.id === id);
      if (!template || template.isBuiltIn) return false;

      setCustomTemplates((prev) => {
        const updated = prev.filter((t) => t.id !== id);
        saveToStorage(STORAGE_KEY_TEMPLATES, updated);
        return updated;
      });

      return true;
    },
    [templates],
  );

  // Extract variables from content
  const extractVariables = useCallback((content: string): string[] => {
    const regex = /\{\{(\w+)\}\}/g;
    const variables: string[] = [];
    let match;

    while ((match = regex.exec(content)) !== null) {
      if (!variables.includes(match[1])) {
        variables.push(match[1]);
      }
    }

    return variables;
  }, []);

  // Apply variable values
  const applyVariables = useCallback(
    (content: string, variables: Record<string, string>): string => {
      let result = content;

      for (const [key, value] of Object.entries(variables)) {
        const regex = new RegExp(`\\{\\{${key}\\}\\}`, "g");
        result = result.replace(regex, value);
      }

      return result;
    },
    [],
  );

  // Add to favorites
  const addToFavorites = useCallback((id: string): void => {
    setFavorites((prev) => {
      if (prev.includes(id)) return prev;
      const updated = [...prev, id];
      saveToStorage(STORAGE_KEY_FAVORITES, updated);
      return updated;
    });
  }, []);

  // Remove from favorites
  const removeFromFavorites = useCallback((id: string): void => {
    setFavorites((prev) => {
      const updated = prev.filter((fid) => fid !== id);
      saveToStorage(STORAGE_KEY_FAVORITES, updated);
      return updated;
    });
  }, []);

  // Check if favorite
  const isFavorite = useCallback(
    (id: string): boolean => {
      return favorites.includes(id);
    },
    [favorites],
  );

  // Get favorite templates
  const getFavoriteTemplates = useCallback((): PromptTemplate[] => {
    return templates.filter((t) => favorites.includes(t.id));
  }, [templates, favorites]);

  // Mark as used
  const markAsUsed = useCallback((id: string): void => {
    setRecentlyUsed((prev) => {
      // Remove if already in list
      const filtered = prev.filter((rid) => rid !== id);
      // Add to front
      const updated = [id, ...filtered].slice(0, MAX_RECENT);
      saveToStorage(STORAGE_KEY_RECENT, updated);
      return updated;
    });
  }, []);

  // Get recently used templates
  const getRecentlyUsedTemplates = useCallback((): PromptTemplate[] => {
    return recentlyUsed
      .map((id) => templates.find((t) => t.id === id))
      .filter((t): t is PromptTemplate => t !== undefined);
  }, [templates, recentlyUsed]);

  return {
    templates,
    favorites,
    recentlyUsed,
    getCategories,
    getTemplateById,
    getTemplatesByCategory,
    searchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    extractVariables,
    applyVariables,
    addToFavorites,
    removeFromFavorites,
    isFavorite,
    getFavoriteTemplates,
    markAsUsed,
    getRecentlyUsedTemplates,
  };
}

export default usePromptTemplates;
