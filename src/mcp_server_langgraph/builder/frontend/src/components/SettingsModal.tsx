/**
 * SettingsModal Component
 *
 * Application settings modal including privacy controls.
 */

import React, { useId } from 'react';
import { X } from 'lucide-react';
import { PrivacySettings, type PrivacyState } from '../../../../shared/frontend/src/components';

// ==============================================================================
// Types
// ==============================================================================

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPrivacyChange?: (settings: PrivacyState) => void;
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Component
// ==============================================================================

export function SettingsModal({
  isOpen,
  onClose,
  onPrivacyChange,
}: SettingsModalProps): React.ReactElement | null {
  const headerId = useId();

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
  };

  const handleDialogClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      data-testid="settings-overlay"
      onClick={handleOverlayClick}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={headerId}
        className={clsx(
          'relative z-10 w-full max-w-lg mx-4',
          'bg-white dark:bg-gray-800 rounded-lg shadow-xl',
          'max-h-[90vh] overflow-y-auto'
        )}
        onClick={handleDialogClick}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2
            id={headerId}
            className="text-xl font-semibold text-gray-900 dark:text-white"
          >
            Settings
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className={clsx(
              'p-2 rounded-lg',
              'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
              'hover:bg-gray-100 dark:hover:bg-gray-700',
              'focus:outline-none focus:ring-2 focus:ring-blue-500'
            )}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <PrivacySettings onSettingsChange={onPrivacyChange} />
        </div>
      </div>
    </div>
  );
}

export default SettingsModal;
