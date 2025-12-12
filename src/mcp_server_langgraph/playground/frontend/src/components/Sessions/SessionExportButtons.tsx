/**
 * SessionExportButtons Component
 *
 * Provides export and import functionality for session history.
 */

import React, { useRef, useCallback } from 'react';
import clsx from 'clsx';
import { useSessionExport, type SessionData } from '../../hooks/useSessionExport';

export interface SessionExportButtonsProps {
  sessions: SessionData[];
  onImport: (sessions: SessionData[]) => void;
  variant?: 'default' | 'compact';
  className?: string;
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
      />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

export function SessionExportButtons({
  sessions,
  onImport,
  variant = 'default',
  className,
}: SessionExportButtonsProps): React.ReactElement {
  const { createDownloadUrl, revokeDownloadUrl, generateFilename, parseImportString, validateImportData } =
    useSessionExport();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = useCallback(() => {
    if (sessions.length === 0) return;

    const url = createDownloadUrl(sessions, { includeMetadata: true });
    const filename = generateFilename();

    // Create temporary link and trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up the blob URL
    setTimeout(() => revokeDownloadUrl(url), 100);
  }, [sessions, createDownloadUrl, generateFilename, revokeDownloadUrl]);

  const handleImportClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = await parseImportString(text);

        if (data && validateImportData(data)) {
          onImport(data.sessions);
        } else {
          console.error('Invalid import file format');
        }
      } catch (error) {
        console.error('Failed to import sessions:', error);
      }

      // Reset input so the same file can be selected again
      event.target.value = '';
    },
    [parseImportString, validateImportData, onImport]
  );

  const isCompact = variant === 'compact';
  const hasNoSessions = sessions.length === 0;

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      {/* Session count */}
      {!isCompact && (
        <span className="text-xs text-gray-500 dark:text-dark-textMuted">
          {sessions.length} session{sessions.length !== 1 ? 's' : ''}
        </span>
      )}

      {/* Export button */}
      <button
        onClick={handleExport}
        disabled={hasNoSessions}
        className={clsx(
          'btn btn-ghost p-1.5',
          hasNoSessions && 'opacity-50 cursor-not-allowed'
        )}
        aria-label="Export sessions"
        title={hasNoSessions ? 'No sessions to export' : 'Export sessions as JSON'}
      >
        <DownloadIcon className="w-4 h-4" />
      </button>

      {/* Import button */}
      <button
        onClick={handleImportClick}
        className="btn btn-ghost p-1.5"
        aria-label="Import sessions"
        title="Import sessions from JSON"
      >
        <UploadIcon className="w-4 h-4" />
      </button>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        onChange={handleFileChange}
        className="hidden"
        aria-hidden="true"
      />
    </div>
  );
}
