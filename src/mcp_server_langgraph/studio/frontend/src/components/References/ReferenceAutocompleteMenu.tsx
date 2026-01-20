/**
 * ReferenceAutocompleteMenu Component
 *
 * Dropdown menu for [[type:qualifier:id]] reference autocomplete.
 * Shows suggestions based on user input and supports keyboard navigation.
 *
 * WCAG 2.2 AA compliant with proper listbox pattern.
 */

import { useCallback, useEffect, useRef } from 'react';
import { Wrench, Sparkles, FileCode, Brain, List, ChevronRight } from 'lucide-react';
import type { ReferenceSuggestion } from '@/hooks/useReferenceAutocomplete';
import { cn } from '@/utils/cn';

export interface ReferenceAutocompleteMenuProps {
  /** Whether the menu is open */
  isOpen: boolean;
  /** Available suggestions */
  suggestions: ReferenceSuggestion[];
  /** Currently selected index */
  selectedIndex: number;
  /** Callback when selection changes */
  onSelectedIndexChange: (index: number) => void;
  /** Callback when a suggestion is clicked */
  onSelect: (suggestion: ReferenceSuggestion) => void;
  /** Callback when menu should close */
  onClose: () => void;
  /** Additional CSS classes */
  className?: string;
}

// Icon mapping for reference types
const TYPE_ICONS: Record<string, typeof Wrench> = {
  tool: Wrench,
  skill: Sparkles,
  artifact: FileCode,
  memory: Brain,
  plan: List,
  type: ChevronRight, // For type suggestions
};

// Color mapping for reference types (Radix design tokens)
const TYPE_COLORS: Record<string, string> = {
  tool: 'text-primary-9',
  skill: 'text-success-9',
  artifact: 'text-neutral-9',
  memory: 'text-info-9',
  plan: 'text-warning-9',
  type: 'text-neutral-11',
};

/**
 * ReferenceAutocompleteMenu displays suggestions for reference autocomplete.
 */
export function ReferenceAutocompleteMenu({
  isOpen,
  suggestions,
  selectedIndex,
  onSelectedIndexChange,
  onSelect,
  onClose,
  className,
}: ReferenceAutocompleteMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLLIElement>(null);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedRef.current && menuRef.current && selectedRef.current.scrollIntoView) {
      selectedRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          onSelectedIndexChange(Math.min(selectedIndex + 1, suggestions.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          onSelectedIndexChange(Math.max(selectedIndex - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (suggestions[selectedIndex]) {
            onSelect(suggestions[selectedIndex]);
          }
          break;
        case 'Escape':
        case 'Tab':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [selectedIndex, suggestions, onSelectedIndexChange, onSelect, onClose]
  );

  // Handle suggestion click
  const handleSuggestionClick = useCallback(
    (suggestion: ReferenceSuggestion) => {
      onSelect(suggestion);
    },
    [onSelect]
  );

  if (!isOpen || suggestions.length === 0) {
    return null;
  }

  return (
    <div
      ref={menuRef}
      id="reference-autocomplete-listbox"
      role="listbox"
      aria-label="Reference suggestions"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className={cn(
        'absolute bottom-full left-0 mb-2 w-72',
        'bg-neutral-1 border border-neutral-6 rounded-lg shadow-lg',
        'max-h-64 overflow-y-auto z-dropdown',
        className
      )}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-neutral-6">
        <span className="text-xs font-medium text-neutral-11 uppercase tracking-wide">
          Insert Reference
        </span>
      </div>

      {/* Suggestions list */}
      <ul className="py-1">
        {suggestions.map((suggestion, index) => {
          const Icon = TYPE_ICONS[suggestion.type] || ChevronRight;
          const iconColor = TYPE_COLORS[suggestion.type] || 'text-neutral-9';
          const isSelected = index === selectedIndex;

          return (
            <li
              key={`${suggestion.type}-${suggestion.value}`}
              id={`ref-suggestion-${index}`}
              ref={isSelected ? selectedRef : undefined}
              role="option"
              aria-selected={isSelected}
              onClick={() => handleSuggestionClick(suggestion)}
              className={cn(
                'px-3 py-2 cursor-pointer flex items-center gap-3',
                isSelected
                  ? 'bg-primary-3 text-primary-12'
                  : 'hover:bg-neutral-2 text-neutral-12'
              )}
            >
              <Icon
                size={16}
                className={cn(iconColor, isSelected && 'text-primary-11')}
                aria-hidden
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">
                  {suggestion.label}
                </div>
                {suggestion.description && (
                  <div className="text-xs text-neutral-10 truncate">
                    {suggestion.description}
                  </div>
                )}
              </div>
              {suggestion.type === 'type' && (
                <ChevronRight
                  size={14}
                  className="text-neutral-9"
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ul>

      {/* Footer hint */}
      <div className="px-3 py-2 border-t border-neutral-6 bg-neutral-2">
        <span className="text-xs text-neutral-10">
          <kbd className="px-1 py-0.5 bg-neutral-3 rounded text-neutral-11">↑↓</kbd>
          {' '}navigate{' '}
          <kbd className="px-1 py-0.5 bg-neutral-3 rounded text-neutral-11">↵</kbd>
          {' '}select{' '}
          <kbd className="px-1 py-0.5 bg-neutral-3 rounded text-neutral-11">esc</kbd>
          {' '}close
        </span>
      </div>
    </div>
  );
}

export default ReferenceAutocompleteMenu;
