/**
 * BulkReferenceInserter Component
 *
 * Dialog for searching and selecting multiple references to insert.
 * Supports filtering by type, search, and bulk selection.
 *
 * WCAG 2.2 AA compliant with proper dialog and listbox patterns.
 */

import { useState, useCallback, useMemo, useEffect, useRef, useId } from 'react';
import { Search, Wrench, Sparkles, FileCode, X } from 'lucide-react';
import { Button, Checkbox } from '@/components/UI';
import { cn } from '@/utils/cn';

export type ReferenceType = 'tool' | 'skill' | 'artifact';

export interface ReferenceItem {
  /** Type of reference */
  type: ReferenceType;
  /** Unique identifier */
  id: string;
  /** Display name */
  name: string;
  /** Optional qualifier (server for tools) */
  qualifier?: string;
  /** Optional description */
  description?: string;
}

export interface BulkReferenceInserterProps {
  /** Whether dialog is open */
  isOpen: boolean;
  /** Available items to select from */
  items: ReferenceItem[];
  /** Callback when references are inserted */
  onInsert: (items: ReferenceItem[]) => void;
  /** Callback when dialog closes */
  onClose: () => void;
}

type TabType = 'all' | ReferenceType;

const TYPE_ICONS: Record<ReferenceType, typeof Wrench> = {
  tool: Wrench,
  skill: Sparkles,
  artifact: FileCode,
};

const TYPE_COLORS: Record<ReferenceType, string> = {
  tool: 'text-primary-9',
  skill: 'text-success-9',
  artifact: 'text-neutral-9',
};

/**
 * Generate markdown reference syntax for an item.
 */
function toMarkdown(item: ReferenceItem): string {
  if (item.type === 'tool' && item.qualifier) {
    return `[[tool:${item.qualifier}:${item.name}]]`;
  }
  return `[[${item.type}:${item.id}]]`;
}

/**
 * BulkReferenceInserter allows selecting multiple references at once.
 */
export function BulkReferenceInserter({
  isOpen,
  items,
  onInsert,
  onClose,
}: BulkReferenceInserterProps) {
  const titleId = useId();
  const searchRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [focusedIndex, setFocusedIndex] = useState(-1);

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setActiveTab('all');
      setSelectedIds(new Set());
      setFocusedIndex(-1);
      // Focus search after mount
      setTimeout(() => searchRef.current?.focus(), 0);
    }
  }, [isOpen]);

  // Filter items based on search and tab
  const filteredItems = useMemo(() => {
    let result = items;

    // Filter by type
    if (activeTab !== 'all') {
      result = result.filter((item) => item.type === activeTab);
    }

    // Filter by search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (item) =>
          item.name.toLowerCase().includes(query) ||
          item.description?.toLowerCase().includes(query) ||
          item.qualifier?.toLowerCase().includes(query) ||
          item.id.toLowerCase().includes(query)
      );
    }

    return result;
  }, [items, activeTab, searchQuery]);

  // Selected items (for preview and insertion)
  const selectedItems = useMemo(() => {
    return items.filter((item) => selectedIds.has(item.id));
  }, [items, selectedIds]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Arrow navigation in list
      if (e.key === 'ArrowDown' && focusedIndex < filteredItems.length - 1) {
        e.preventDefault();
        setFocusedIndex((prev) => prev + 1);
      } else if (e.key === 'ArrowUp' && focusedIndex > 0) {
        e.preventDefault();
        setFocusedIndex((prev) => prev - 1);
      }
    },
    [filteredItems.length, focusedIndex, onClose]
  );

  const handleToggleItem = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    const allIds = filteredItems.map((item) => item.id);
    setSelectedIds((prev) => new Set([...prev, ...allIds]));
  }, [filteredItems]);

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleInsert = useCallback(() => {
    onInsert(selectedItems);
    onClose();
  }, [selectedItems, onInsert, onClose]);

  if (!isOpen) {
    return null;
  }

  const tabs: { value: TabType; label: string; count: number }[] = [
    { value: 'all', label: 'All', count: items.length },
    { value: 'tool', label: 'Tools', count: items.filter((i) => i.type === 'tool').length },
    { value: 'skill', label: 'Skills', count: items.filter((i) => i.type === 'skill').length },
    { value: 'artifact', label: 'Artifacts', count: items.filter((i) => i.type === 'artifact').length },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-modal flex items-center justify-center bg-neutral-1/80 backdrop-blur-sm"
      onKeyDown={handleKeyDown}
    >
      <div className="w-full max-w-lg bg-neutral-1 border border-neutral-6 rounded-lg shadow-xl flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="px-4 py-3 border-b border-neutral-6 flex items-center justify-between">
          <h2 id={titleId} className="text-base font-semibold text-neutral-12">
            Insert References
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="p-1"
            aria-label="Close"
          >
            <X size={18} />
          </Button>
        </div>

        {/* Search */}
        <div className="px-4 py-2 border-b border-neutral-6">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-9"
              aria-hidden
            />
{/* eslint-disable-next-line react/forbid-elements -- Custom search with ref for focus management, SearchInput doesn't support refs */}
            <input
              ref={searchRef}
              type="search"
              role="searchbox"
              placeholder="Search references..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                'w-full pl-9 pr-3 py-2 rounded-lg',
                'bg-neutral-2 border border-neutral-6',
                'text-sm text-neutral-12 placeholder:text-neutral-9',
                'focus:outline-none focus:ring-2 focus:ring-primary-7'
              )}
            />
          </div>
        </div>

        {/* Type tabs */}
        <div className="px-4 py-2 border-b border-neutral-6">
          <div role="tablist" className="flex gap-1">
            {tabs.map((tab) => (
              // eslint-disable-next-line react/forbid-elements -- Custom tab with role="tab" and aria-selected
              <button
                key={tab.value}
                role="tab"
                aria-selected={activeTab === tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  activeTab === tab.value
                    ? 'bg-primary-3 text-primary-11'
                    : 'text-neutral-11 hover:bg-neutral-2'
                )}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </div>

        {/* Selection controls */}
        <div className="px-4 py-2 border-b border-neutral-6 flex items-center justify-between">
          <span className="text-sm text-neutral-10">
            {filteredItems.length} items
          </span>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleSelectAll}>
              Select all
            </Button>
            {selectedIds.size > 0 && (
              <Button variant="ghost" size="sm" onClick={handleClearSelection}>
                Clear selection
              </Button>
            )}
          </div>
        </div>

        {/* Items list */}
        <div
          role="listbox"
          aria-multiselectable="true"
          className="flex-1 overflow-y-auto px-2 py-2"
        >
          {filteredItems.length === 0 ? (
            <div className="text-center py-8 text-neutral-10">
              No matching references found
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = TYPE_ICONS[item.type];
              const isSelected = selectedIds.has(item.id);
              const isFocused = index === focusedIndex;

              return (
                <div
                  key={item.id}
                  role="option"
                  aria-selected={isFocused}
                  className={cn(
                    'flex items-center gap-3 px-2 py-2 rounded-lg cursor-pointer',
                    'hover:bg-neutral-2',
                    isFocused && 'bg-neutral-2 ring-2 ring-primary-7'
                  )}
                  onClick={() => handleToggleItem(item.id)}
                >
                  <div onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isSelected}
                      onChange={() => handleToggleItem(item.id)}
                      aria-label={`Select ${item.name}`}
                    />
                  </div>
                  <Icon
                    size={16}
                    className={TYPE_COLORS[item.type]}
                    aria-hidden
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-neutral-12 truncate">
                      {item.name}
                    </div>
                    {item.description && (
                      <div className="text-xs text-neutral-10 truncate">
                        {item.description}
                      </div>
                    )}
                  </div>
                  {item.qualifier && (
                    <span className="text-xs text-neutral-9 px-1.5 py-0.5 bg-neutral-3 rounded">
                      {item.qualifier}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Selection status (live region) */}
        <div role="status" aria-live="polite" className="sr-only">
          {selectedIds.size} selected
        </div>

        {/* Preview */}
        {selectedItems.length > 0 && (
          <div className="px-4 py-2 border-t border-neutral-6 bg-neutral-2">
            <div className="text-xs text-neutral-10 mb-1">Preview:</div>
            <div className="text-xs text-neutral-11 font-mono bg-neutral-3 rounded px-2 py-1 overflow-x-auto">
              {selectedItems.map((item) => toMarkdown(item)).join(' ')}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 border-t border-neutral-6 flex items-center justify-between">
          <span className="text-sm text-neutral-11" role="status">
            {selectedIds.size > 0 && `${selectedIds.size} selected`}
          </span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleInsert}
              disabled={selectedIds.size === 0}
            >
              Insert ({selectedIds.size})
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BulkReferenceInserter;
