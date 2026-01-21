/**
 * CanvasShortcutsMenu - Quick Actions for Canvas Artifacts
 *
 * @deprecated Phase 4 Canvas UX Improvements
 * This floating menu component is deprecated in favor of:
 * 1. AI actions integrated into ArtifactActions.tsx toolbar
 * 2. SuggestionsFooterBar.tsx for AI suggestions
 *
 * The component is still rendered when:
 * - Feature flag `canvas_ai_palette` is enabled
 * - AND feature flag `suggestions_footer_bar` is disabled
 *
 * Migration: Enable `suggestions_footer_bar` feature flag to use the new
 * non-intrusive AI controls. This component will be removed in a future version.
 *
 * Sprint 6: ChatGPT Canvas-inspired coding shortcuts menu.
 * Provides quick AI-powered actions for code artifacts.
 *
 * Actions:
 * - Review code (AI analysis)
 * - Add comments
 * - Add logging/debug statements
 * - Fix bugs
 * - Port to another language
 * - Generate tests
 * - Explain code
 *
 * Feature Flag: canvas_ai_palette (must be enabled)
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type CanvasShortcutAction =
  | "review"
  | "comments"
  | "logging"
  | "fix"
  | "port"
  | "tests"
  | "explain";

export interface CanvasShortcutItem {
  id: CanvasShortcutAction;
  label: string;
  description: string;
  icon: React.ReactNode;
  shortcut?: string;
}

export interface CanvasShortcutsMenuProps {
  /** Called when a shortcut action is selected */
  onAction: (action: CanvasShortcutAction) => void;
  /** Whether an action is currently loading */
  isLoading?: boolean;
  /** Additional class name */
  className?: string;
  /** Currently selected artifact's language (for port action) */
  language?: string;
}

// =============================================================================
// Shortcut Definitions
// =============================================================================

const SHORTCUTS: CanvasShortcutItem[] = [
  {
    id: "review",
    label: "Review Code",
    description: "AI analysis for improvements",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    shortcut: "⌘R",
  },
  {
    id: "comments",
    label: "Add Comments",
    description: "Document with inline comments",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
        />
      </svg>
    ),
  },
  {
    id: "logging",
    label: "Add Logging",
    description: "Insert debug statements",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 6h16M4 10h16M4 14h16M4 18h16"
        />
      </svg>
    ),
  },
  {
    id: "fix",
    label: "Fix Bugs",
    description: "Detect and fix issues",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    shortcut: "⌘F",
  },
  {
    id: "port",
    label: "Port Language",
    description: "Convert to another language",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
        />
      </svg>
    ),
  },
  {
    id: "tests",
    label: "Generate Tests",
    description: "Create unit test cases",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
    ),
    shortcut: "⌘T",
  },
  {
    id: "explain",
    label: "Explain Code",
    description: "Understand how it works",
    icon: (
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    shortcut: "⌘E",
  },
];

// =============================================================================
// Component
// =============================================================================

export function CanvasShortcutsMenu({
  onAction,
  isLoading = false,
  className,
  language,
}: CanvasShortcutsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      // Escape closes menu
      if (e.key === "Escape") {
        setIsOpen(false);
        return;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const handleActionClick = useCallback(
    (action: CanvasShortcutAction) => {
      if (isLoading) return;
      onAction(action);
      setIsOpen(false);
    },
    [onAction, isLoading],
  );

  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return (
    <div
      ref={menuRef}
      data-testid="canvas-shortcuts-menu"
      className={cn("relative", className)}
    >
      {/* Floating Action Button */}
      <Button
        variant="primary"
        data-testid="canvas-shortcuts-trigger"
        onClick={toggleMenu}
        disabled={isLoading}
        className={cn(
          "p-3 rounded-full shadow-lg transition-all duration-200",
          "bg-primary-10 hover:bg-primary-11 text-neutral-12",
          "focus:outline-none focus:ring-2 focus:ring-primary-7 focus:ring-offset-2",
          isLoading && "opacity-50 cursor-not-allowed",
          isOpen && "rotate-45",
        )}
        aria-label={isOpen ? "Close shortcuts menu" : "Open shortcuts menu"}
        aria-expanded={isOpen}>
        {isLoading ? (
          <span className="block w-5 h-5 animate-spin rounded-full border-2 border-neutral-1 border-t-transparent" />
        ) : (
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        )}
      </Button>
      {/* Menu Panel */}
      {isOpen && (
        <div
          data-testid="canvas-shortcuts-panel"
          className={cn(
            "absolute bottom-14 right-0 z-dropdown w-64",
            "bg-neutral-1 rounded-lg shadow-xl",
            "border border-neutral-5",
            "py-2 animate-in fade-in slide-in-from-bottom-2 duration-200",
          )}
          role="menu"
          aria-label="Canvas shortcuts"
        >
          {/* Header */}
          <div className="px-3 py-2 border-b border-neutral-5">
            <h3 className="text-sm font-semibold text-neutral-12">
              Quick Actions
            </h3>
            <p className="text-xs text-neutral-11">
              AI-powered code transformations
            </p>
          </div>

          {/* Actions List */}
          <div className="py-1">
            {SHORTCUTS.map((shortcut) => (
              <Button
                key={shortcut.id}
                variant="ghost"
                data-testid={`shortcut-${shortcut.id}`}
                onClick={() => handleActionClick(shortcut.id)}
                disabled={isLoading}
                className={cn(
                  "w-full flex items-start gap-3 px-3 py-2 rounded-none",
                  "text-left hover:bg-neutral-3",
                  "transition-colors duration-150",
                  "focus:outline-none focus:bg-neutral-3",
                  isLoading && "opacity-50 cursor-not-allowed",
                )}
                role="menuitem"
              >
                <span className="flex-shrink-0 text-primary-11 dark:text-primary-11 mt-0.5">
                  {shortcut.icon}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-neutral-12">
                      {shortcut.label}
                    </span>
                    {shortcut.shortcut && (
                      <span className="text-xs text-neutral-11 font-mono">
                        {shortcut.shortcut}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-neutral-11 truncate">
                    {shortcut.id === "port" && language
                      ? `Convert from ${language}`
                      : shortcut.description}
                  </p>
                </div>
              </Button>
            ))}
          </div>

          {/* Footer Tip */}
          <div className="px-3 py-2 border-t border-neutral-5">
            <p className="text-xs text-neutral-11">
              Actions apply to selected artifact
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default CanvasShortcutsMenu;
