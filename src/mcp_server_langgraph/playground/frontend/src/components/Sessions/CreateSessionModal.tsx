/**
 * CreateSessionModal Component
 *
 * Modal dialog for creating a new session.
 */

import React, { useState, useEffect } from 'react';
import type { SessionConfig } from '../../api/types';

export interface CreateSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, config?: Partial<SessionConfig>) => void;
}

export function CreateSessionModal({
  isOpen,
  onClose,
  onCreate,
}: CreateSessionModalProps): React.ReactElement | null {
  const [name, setName] = useState('');

  // Clear form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setName('');
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), undefined);
      onClose();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-dark-surface rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2
          id="modal-title"
          className="text-lg font-semibold text-gray-900 dark:text-dark-text mb-4"
        >
          Create New Session
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label
              htmlFor="session-name"
              className="block text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-1"
            >
              Session Name
            </label>
            <input
              id="session-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="Enter session name..."
              autoFocus
            />
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!name.trim()}
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
