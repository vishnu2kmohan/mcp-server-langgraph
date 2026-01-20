/**
 * useReferenceAutocomplete Hook
 *
 * Provides autocomplete functionality for [[type:qualifier:id]] markdown references.
 * Triggers when user types [[ and provides suggestions for types, then qualifiers/ids.
 *
 * Features:
 * - Detects [[ trigger in input
 * - Parses partial reference syntax
 * - Provides contextual suggestions
 * - Keyboard navigation support
 * - WCAG 2.2 AA accessible aria attributes
 */

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

export type ReferenceType = 'tool' | 'skill' | 'artifact' | 'memory' | 'plan';

export interface ReferenceSuggestion {
  /** Value to insert */
  value: string;
  /** Display label */
  label: string;
  /** Optional description */
  description?: string;
  /** Type of suggestion */
  type: 'type' | ReferenceType;
  /** Whether this completes the reference (adds ]]) */
  isComplete?: boolean;
  /** Icon name for display */
  icon?: string;
  /** Semantic search relevance score (0-1) */
  score?: number;
}

export interface AvailableTool {
  server: string;
  name: string;
  description?: string;
}

export interface AvailableSkill {
  name: string;
  description?: string;
  tags?: string[];
}

export interface AvailableArtifact {
  id: string;
  name?: string;
  description?: string;
}

export interface ParsedQuery {
  type: ReferenceType | undefined;
  qualifier: string | undefined;
  id: string | undefined;
}

export interface SelectionResult {
  newText: string;
  newCursorPosition: number;
  suggestion: ReferenceSuggestion;
}

export interface UseReferenceAutocompleteOptions {
  /** Current input value */
  inputValue: string;
  /** Current cursor position */
  cursorPosition: number;
  /** Whether autocomplete is enabled */
  enabled: boolean;
  /** Callback when a suggestion is selected */
  onSelect?: (result: SelectionResult) => void;
  /** Available tools for suggestions */
  availableTools?: AvailableTool[];
  /** Available skills for suggestions */
  availableSkills?: AvailableSkill[];
  /** Available artifacts for suggestions */
  availableArtifacts?: AvailableArtifact[];
  /** Enable semantic search via API (requires feature flag) */
  enableSemanticSearch?: boolean;
}

/** Result from semantic search API */
export interface SemanticSearchResult {
  tool_id?: string;
  skill_id?: string;
  name: string;
  description: string;
  score: number;
  tags?: string[];
  category?: string;
}

export interface UseReferenceAutocompleteResult {
  /** Whether autocomplete is currently active */
  isActive: boolean;
  /** Start position of the [[ trigger */
  triggerStart: number | null;
  /** Current query string after [[ */
  query: string;
  /** Parsed query components */
  parsedQuery: ParsedQuery;
  /** Available suggestions */
  suggestions: ReferenceSuggestion[];
  /** Currently selected suggestion index */
  selectedIndex: number;
  /** Set selected index */
  setSelectedIndex: (index: number) => void;
  /** Select a suggestion */
  selectSuggestion: (suggestion: ReferenceSuggestion) => void;
  /** Dismiss autocomplete */
  dismiss: () => void;
  /** ARIA attributes for accessibility */
  ariaProps: Record<string, string | boolean>;
}

// =============================================================================
// Constants
// =============================================================================

const REFERENCE_TYPES: ReferenceSuggestion[] = [
  {
    value: 'tool',
    label: 'Tool',
    description: 'Reference an MCP tool',
    type: 'type',
    icon: 'wrench',
  },
  {
    value: 'skill',
    label: 'Skill',
    description: 'Reference a skill',
    type: 'type',
    icon: 'sparkles',
  },
  {
    value: 'artifact',
    label: 'Artifact',
    description: 'Reference an artifact',
    type: 'type',
    icon: 'file',
  },
];

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Find the [[ trigger position before the cursor.
 */
function findTriggerPosition(text: string, cursorPos: number): number | null {
  // Look backwards from cursor for [[
  const textBeforeCursor = text.slice(0, cursorPos);
  const lastOpenBrackets = textBeforeCursor.lastIndexOf('[[');

  if (lastOpenBrackets === -1) {
    return null;
  }

  // Check if there's a ]] between [[ and cursor (reference already closed)
  const textBetween = text.slice(lastOpenBrackets, cursorPos);
  if (textBetween.includes(']]')) {
    return null;
  }

  return lastOpenBrackets;
}

/**
 * Parse the query string after [[ into components.
 */
function parseQuery(query: string): ParsedQuery {
  if (!query) {
    return { type: undefined, qualifier: undefined, id: undefined };
  }

  const parts = query.split(':');
  const typePart = parts[0]?.toLowerCase();

  // Check if type is valid
  const validTypes: ReferenceType[] = ['tool', 'skill', 'artifact', 'memory', 'plan'];
  const type = validTypes.includes(typePart as ReferenceType)
    ? (typePart as ReferenceType)
    : undefined;

  if (!type) {
    // Still typing the type
    return { type: undefined, qualifier: undefined, id: undefined };
  }

  // For tools: [[tool:server:tool_name]]
  if (type === 'tool') {
    return {
      type,
      qualifier: parts[1],
      id: parts[2],
    };
  }

  // For skills/artifacts: [[skill:name]] or [[artifact:id]]
  return {
    type,
    qualifier: parts[1],
    id: parts[1], // qualifier and id are the same for non-tools
  };
}

// =============================================================================
// Hook
// =============================================================================

// Debounce delay for semantic search API calls (ms)
const SEMANTIC_SEARCH_DEBOUNCE_MS = 300;

export function useReferenceAutocomplete({
  inputValue,
  cursorPosition,
  enabled,
  onSelect,
  availableTools = [],
  availableSkills = [],
  availableArtifacts = [],
  enableSemanticSearch = false,
}: UseReferenceAutocompleteOptions): UseReferenceAutocompleteResult {
  const [isDismissed, setIsDismissed] = useState(false);
  const [selectedIndex, setSelectedIndexRaw] = useState(0);
  const [lastTriggerPos, setLastTriggerPos] = useState<number | null>(null);
  const [semanticResults, setSemanticResults] = useState<ReferenceSuggestion[]>([]);
  const [_isLoadingSemanticSearch, setIsLoadingSemanticSearch] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Find trigger position
  const triggerStart = useMemo(() => {
    if (!enabled || isDismissed) return null;
    return findTriggerPosition(inputValue, cursorPosition);
  }, [inputValue, cursorPosition, enabled, isDismissed]);

  // Reset dismissed state when a new trigger is detected
  useEffect(() => {
    const currentTrigger = findTriggerPosition(inputValue, cursorPosition);
    if (currentTrigger !== null && currentTrigger !== lastTriggerPos) {
      setIsDismissed(false);
      setLastTriggerPos(currentTrigger);
    }
  }, [inputValue, cursorPosition, lastTriggerPos]);

  // Extract query string after [[
  const query = useMemo(() => {
    if (triggerStart === null) return '';
    return inputValue.slice(triggerStart + 2, cursorPosition);
  }, [inputValue, cursorPosition, triggerStart]);

  // Parse query into components
  const parsedQuery = useMemo(() => parseQuery(query), [query]);

  // Semantic search effect - debounced API call when enabled
  useEffect(() => {
    // Only run semantic search when:
    // 1. enableSemanticSearch is true
    // 2. We have a type (tool or skill - artifacts don't support semantic search yet)
    // 3. We have a qualifier string to search with
    if (!enableSemanticSearch || !parsedQuery.type || !parsedQuery.qualifier) {
      setSemanticResults([]);
      return;
    }

    // Only tools and skills support semantic search
    if (parsedQuery.type !== 'tool' && parsedQuery.type !== 'skill') {
      setSemanticResults([]);
      return;
    }

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Debounced API call
    debounceTimerRef.current = setTimeout(async () => {
      const searchQuery = parsedQuery.qualifier;
      const searchType = parsedQuery.type;

      // Determine API endpoint based on type
      const endpoint = searchType === 'tool'
        ? '/api/v1/tools/semantic-search'
        : '/api/v1/admin/skills/semantic-search';

      setIsLoadingSemanticSearch(true);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: searchQuery,
            limit: 10,
            min_score: 0.0,
          }),
        });

        if (!response.ok) {
          // On error, clear semantic results (will fall back to substring matching)
          setSemanticResults([]);
          return;
        }

        const data = await response.json();
        const results: SemanticSearchResult[] = data.results || [];

        // Transform API results to ReferenceSuggestion format
        const suggestions: ReferenceSuggestion[] = results
          .sort((a, b) => b.score - a.score) // Sort by score descending
          .map((result) => ({
            value: result.name,
            label: result.name,
            description: result.description,
            type: searchType as ReferenceType,
            isComplete: true,
            icon: searchType === 'tool' ? 'wrench' : 'sparkles',
            score: result.score,
          }));

        setSemanticResults(suggestions);
      } catch {
        // On error, clear semantic results (will fall back to substring matching)
        setSemanticResults([]);
      } finally {
        setIsLoadingSemanticSearch(false);
      }
    }, SEMANTIC_SEARCH_DEBOUNCE_MS);

    // Cleanup on unmount or deps change
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [enableSemanticSearch, parsedQuery.type, parsedQuery.qualifier]);

  // Generate suggestions based on current query state
  const suggestions = useMemo((): ReferenceSuggestion[] => {
    if (triggerStart === null) return [];

    // No type yet - show type suggestions
    if (!parsedQuery.type) {
      const lowerQuery = query.toLowerCase();
      return REFERENCE_TYPES.filter((t) =>
        t.value.toLowerCase().startsWith(lowerQuery)
      );
    }

    // Use semantic results if available (for tools and skills with semantic search enabled)
    if (
      enableSemanticSearch &&
      (parsedQuery.type === 'tool' || parsedQuery.type === 'skill') &&
      semanticResults.length > 0
    ) {
      return semanticResults;
    }

    // Type is complete, need qualifier/id - fallback to substring matching
    const lowerQualifier = (parsedQuery.qualifier || '').toLowerCase();

    if (parsedQuery.type === 'tool') {
      // Filter tools based on qualifier input
      return availableTools
        .filter((tool) => {
          const fullName = `${tool.server}:${tool.name}`;
          return fullName.toLowerCase().includes(lowerQualifier);
        })
        .map((tool) => ({
          value: `${tool.server}:${tool.name}`,
          label: tool.name,
          description: tool.description,
          type: 'tool' as const,
          isComplete: true,
          icon: 'wrench',
        }));
    }

    if (parsedQuery.type === 'skill') {
      return availableSkills
        .filter((skill) =>
          skill.name.toLowerCase().includes(lowerQualifier)
        )
        .map((skill) => ({
          value: skill.name,
          label: skill.name,
          description: skill.description,
          type: 'skill' as const,
          isComplete: true,
          icon: 'sparkles',
        }));
    }

    if (parsedQuery.type === 'artifact') {
      return availableArtifacts
        .filter((artifact) => {
          const searchText = (artifact.name || artifact.id).toLowerCase();
          return searchText.includes(lowerQualifier);
        })
        .map((artifact) => ({
          value: artifact.id,
          label: artifact.name || artifact.id,
          description: artifact.description,
          type: 'artifact' as const,
          isComplete: true,
          icon: 'file',
        }));
    }

    return [];
  }, [
    triggerStart,
    query,
    parsedQuery,
    availableTools,
    availableSkills,
    enableSemanticSearch,
    semanticResults,
    availableArtifacts,
  ]);

  // Reset selected index when suggestions change
  useEffect(() => {
    setSelectedIndexRaw(0);
  }, [suggestions.length, query]);

  // Bound selected index
  const setSelectedIndex = useCallback(
    (index: number) => {
      const maxIndex = Math.max(0, suggestions.length - 1);
      setSelectedIndexRaw(Math.min(Math.max(0, index), maxIndex));
    },
    [suggestions.length]
  );

  // Select a suggestion
  const selectSuggestion = useCallback(
    (suggestion: ReferenceSuggestion) => {
      if (triggerStart === null || !onSelect) return;

      let newText: string;
      let newCursorPos: number;

      const beforeTrigger = inputValue.slice(0, triggerStart);
      const afterCursor = inputValue.slice(cursorPosition);

      if (suggestion.type === 'type') {
        // Insert type and continue (add colon)
        newText = `${beforeTrigger}[[${suggestion.value}:${afterCursor}`;
        newCursorPos = triggerStart + 2 + suggestion.value.length + 1;
      } else if (suggestion.isComplete) {
        // Complete the reference with ]]
        const parts = query.split(':');
        const existingType = parts[0] || parsedQuery.type;

        if (parsedQuery.type === 'tool') {
          // For tools, check if we have a partial qualifier already typed
          // If suggestion.value contains server:name, use it directly
          // Otherwise, preserve what the user typed as qualifier
          if (suggestion.value.includes(':')) {
            // Suggestion is server:name format - use as-is
            newText = `${beforeTrigger}[[${existingType}:${suggestion.value}]]${afterCursor}`;
          } else {
            // Suggestion is just the tool name, preserve existing qualifier
            const existingQualifier = parts[1] || '';
            if (existingQualifier) {
              newText = `${beforeTrigger}[[${existingType}:${existingQualifier}:${suggestion.value}]]${afterCursor}`;
            } else {
              newText = `${beforeTrigger}[[${existingType}:${suggestion.value}]]${afterCursor}`;
            }
          }
        } else {
          // Skill/artifact with just name
          newText = `${beforeTrigger}[[${existingType}:${suggestion.value}]]${afterCursor}`;
        }
        newCursorPos = newText.length - afterCursor.length;
      } else {
        // Partial - add colon and continue
        newText = `${beforeTrigger}[[${query}${suggestion.value}:${afterCursor}`;
        newCursorPos = triggerStart + 2 + query.length + suggestion.value.length + 1;
      }

      onSelect({
        newText,
        newCursorPosition: newCursorPos,
        suggestion,
      });
    },
    [inputValue, cursorPosition, triggerStart, query, parsedQuery, onSelect]
  );

  // Dismiss autocomplete
  const dismiss = useCallback(() => {
    setIsDismissed(true);
  }, []);

  // ARIA attributes for accessibility
  const ariaProps = useMemo(() => {
    const isActive = triggerStart !== null && suggestions.length > 0;
    const activeId = isActive ? `ref-suggestion-${selectedIndex}` : undefined;

    return {
      role: 'combobox',
      'aria-expanded': isActive,
      'aria-haspopup': 'listbox' as const,
      'aria-controls': 'reference-autocomplete-listbox',
      'aria-activedescendant': activeId || '',
    };
  }, [triggerStart, suggestions.length, selectedIndex]);

  // Active when trigger is found (even if no suggestions yet)
  const isActive = triggerStart !== null && !isDismissed;

  return {
    isActive,
    triggerStart,
    query,
    parsedQuery,
    suggestions,
    selectedIndex,
    setSelectedIndex,
    selectSuggestion,
    dismiss,
    ariaProps,
  };
}

export default useReferenceAutocomplete;
