/**
 * Keyboard Shortcuts Modal Component
 *
 * Displays available keyboard shortcuts for the Visual Workflow Builder.
 * Helps users discover and learn keyboard navigation for improved efficiency.
 *
 * WCAG 2.1 AA Compliant:
 * - Focus trap within modal
 * - Escape key closes modal
 * - Proper ARIA labels
 */

import { useEffect, useRef } from 'react';
import { X, Keyboard } from 'lucide-react';
import { useFocusTrap } from '../hooks/useAccessibility';

// ==============================================================================
// Types
// ==============================================================================

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ShortcutCategory {
  name: string;
  shortcuts: Shortcut[];
}

interface Shortcut {
  keys: string[];
  description: string;
}

// ==============================================================================
// Shortcut Data
// ==============================================================================

const shortcutCategories: ShortcutCategory[] = [
  {
    name: 'General',
    shortcuts: [
      { keys: ['Ctrl', 'S'], description: 'Save workflow' },
      { keys: ['Ctrl', 'G'], description: 'Generate code' },
      { keys: ['Ctrl', 'Shift', 'T'], description: 'Toggle dark mode' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
      { keys: ['Escape'], description: 'Close menu/modal' },
    ],
  },
  {
    name: 'Editing',
    shortcuts: [
      { keys: ['Ctrl', 'Z'], description: 'Undo' },
      { keys: ['Ctrl', 'Y'], description: 'Redo' },
      { keys: ['Ctrl', 'Shift', 'Z'], description: 'Redo (alternative)' },
      { keys: ['Delete'], description: 'Delete selected nodes' },
      { keys: ['Backspace'], description: 'Delete selected nodes' },
    ],
  },
];

// ==============================================================================
// Key Badge Component
// ==============================================================================

function KeyBadge({ keyName }: { keyName: string }) {
  return (
    <kbd className="inline-flex items-center justify-center px-2 py-1 min-w-[28px] text-xs font-mono font-medium bg-gray-100 border border-gray-300 rounded shadow-sm">
      {keyName}
    </kbd>
  );
}

// ==============================================================================
// Main Component
// ==============================================================================

export function KeyboardShortcutsModal({
  isOpen,
  onClose,
}: KeyboardShortcutsModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus trap for accessibility
  useFocusTrap(modalRef, isOpen);

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="modal-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Keyboard size={20} className="text-gray-600" />
            <h2
              id="shortcuts-modal-title"
              className="text-lg font-semibold text-gray-900"
            >
              Keyboard Shortcuts
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-6">
          {shortcutCategories.map((category) => (
            <div key={category.name}>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                {category.name}
              </h3>
              <div className="space-y-2">
                {category.shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <span className="text-gray-700">{shortcut.description}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <span key={keyIndex} className="flex items-center gap-1">
                          <KeyBadge keyName={key} />
                          {keyIndex < shortcut.keys.length - 1 && (
                            <span className="text-gray-400 text-xs">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 bg-gray-50 border-t border-gray-200 text-center text-sm text-gray-500">
          Press <KeyBadge keyName="?" /> to toggle this modal
        </div>
      </div>
    </div>
  );
}

export default KeyboardShortcutsModal;
