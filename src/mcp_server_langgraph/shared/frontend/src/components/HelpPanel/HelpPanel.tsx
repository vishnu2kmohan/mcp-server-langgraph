/**
 * HelpPanel Component
 *
 * Slide-out help panel with searchable articles and keyboard shortcuts.
 */

import React, { ReactElement, useState, useCallback, useMemo, useEffect } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface HelpSection {
  /** Unique identifier */
  id: string;
  /** Section title */
  title: string;
  /** Optional icon */
  icon?: string;
}

export interface HelpArticle {
  /** Unique identifier */
  id: string;
  /** Article title */
  title: string;
  /** Article content (markdown or plain text) */
  content: string;
  /** Category/section this belongs to */
  category: string;
  /** Keywords for search */
  keywords?: string[];
}

export interface KeyboardShortcut {
  /** Keys to press (e.g., ['Ctrl', 'S']) */
  keys: string[];
  /** Description of what it does */
  description: string;
}

export interface HelpPanelProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** Callback when panel is closed */
  onClose: () => void;
  /** Help articles */
  articles: HelpArticle[];
  /** Help sections/categories */
  sections: HelpSection[];
  /** Keyboard shortcuts to display */
  keyboardShortcuts?: KeyboardShortcut[];
  /** Custom title */
  title?: string;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// =============================================================================
// HelpPanel Component
// =============================================================================

export function HelpPanel({
  isOpen,
  onClose,
  articles,
  sections,
  keyboardShortcuts,
  title = 'Help Center',
  className,
}: HelpPanelProps): ReactElement | null {
  const [activeSection, setActiveSection] = useState(sections[0]?.id || '');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null);

  // Build sections list including keyboard shortcuts if provided
  const allSections = useMemo(() => {
    if (keyboardShortcuts && keyboardShortcuts.length > 0) {
      return [...sections, { id: 'keyboard-shortcuts', title: 'Keyboard', icon: '⌨️' }];
    }
    return sections;
  }, [sections, keyboardShortcuts]);

  // Filter articles based on search and section
  const filteredArticles = useMemo(() => {
    let filtered = articles;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = articles.filter(
        (article) =>
          article.title.toLowerCase().includes(query) ||
          article.content.toLowerCase().includes(query) ||
          article.keywords?.some((kw) => kw.toLowerCase().includes(query))
      );
    } else if (activeSection && activeSection !== 'keyboard-shortcuts') {
      filtered = articles.filter((article) => article.category === activeSection);
    }

    return filtered;
  }, [articles, searchQuery, activeSection]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  const handleSectionChange = useCallback((sectionId: string) => {
    setActiveSection(sectionId);
    setSelectedArticle(null);
    setSearchQuery('');
  }, []);

  const handleArticleClick = useCallback((article: HelpArticle) => {
    setSelectedArticle(article);
  }, []);

  const handleBack = useCallback(() => {
    setSelectedArticle(null);
  }, []);

  const handleClearSearch = useCallback(() => {
    setSearchQuery('');
  }, []);

  // Handle escape key at document level
  useEffect(() => {
    if (!isOpen) return;

    const handleDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleDocumentKeyDown);
    return () => document.removeEventListener('keydown', handleDocumentKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const isKeyboardShortcutsView = activeSection === 'keyboard-shortcuts' && !searchQuery;

  return (
    <aside
      role="complementary"
      aria-label="Help panel"
      onKeyDown={handleKeyDown}
      className={clsx(
        'fixed right-0 top-0 h-full w-80 z-50',
        'bg-white dark:bg-gray-800 shadow-xl',
        'border-l border-gray-200 dark:border-gray-700',
        'flex flex-col',
        'animate-in slide-in-from-right duration-200',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {title}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close help panel"
          className={clsx(
            'p-1 rounded-lg',
            'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300',
            'hover:bg-gray-100 dark:hover:bg-gray-700',
            'focus:outline-none focus:ring-2 focus:ring-blue-500'
          )}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <input
            type="text"
            placeholder="Search help articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={clsx(
              'w-full pl-10 pr-10 py-2 rounded-lg',
              'bg-gray-100 dark:bg-gray-700',
              'text-gray-900 dark:text-white',
              'placeholder-gray-500 dark:placeholder-gray-400',
              'border border-gray-200 dark:border-gray-600',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            )}
          />
          <svg
            className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          {searchQuery && (
            <button
              type="button"
              onClick={handleClearSearch}
              aria-label="Clear search"
              className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Section Tabs */}
      {!selectedArticle && !searchQuery && (
        <div
          role="tablist"
          className="flex gap-1 p-2 border-b border-gray-200 dark:border-gray-700 overflow-x-auto"
        >
          {allSections.map((section) => (
            <button
              key={section.id}
              role="tab"
              aria-selected={activeSection === section.id}
              onClick={() => handleSectionChange(section.id)}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap',
                'transition-colors',
                activeSection === section.id
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
            >
              {section.icon && <span className="mr-1">{section.icon}</span>}
              {section.title}
            </button>
          ))}
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {/* Article Detail View */}
        {selectedArticle && (
          <div className="p-4">
            <button
              type="button"
              onClick={handleBack}
              className={clsx(
                'flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400',
                'hover:underline mb-4'
              )}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {selectedArticle.title}
            </h3>
            <div className="text-gray-600 dark:text-gray-300 prose dark:prose-invert prose-sm">
              {selectedArticle.content}
            </div>
          </div>
        )}

        {/* Keyboard Shortcuts View */}
        {!selectedArticle && isKeyboardShortcutsView && keyboardShortcuts && (
          <div className="p-4 space-y-3">
            {keyboardShortcuts.map((shortcut, index) => (
              <div key={index} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {shortcut.description}
                </span>
                <div className="flex gap-1">
                  {shortcut.keys.map((key, keyIndex) => (
                    <kbd
                      key={keyIndex}
                      className={clsx(
                        'px-2 py-1 text-xs font-mono',
                        'bg-gray-100 dark:bg-gray-700',
                        'border border-gray-300 dark:border-gray-600',
                        'rounded text-gray-700 dark:text-gray-300'
                      )}
                    >
                      {key}
                    </kbd>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Articles List View */}
        {!selectedArticle && !isKeyboardShortcutsView && (
          <div className="p-4">
            {filteredArticles.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400">
                  No results found
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {filteredArticles.map((article) => (
                  <li key={article.id}>
                    <button
                      type="button"
                      onClick={() => handleArticleClick(article)}
                      className={clsx(
                        'w-full text-left p-3 rounded-lg',
                        'bg-gray-50 dark:bg-gray-700/50',
                        'hover:bg-gray-100 dark:hover:bg-gray-700',
                        'transition-colors'
                      )}
                    >
                      <span className="font-medium text-gray-900 dark:text-white">
                        {article.title}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default HelpPanel;
