/**
 * useSessionExport Hook
 *
 * Provides functionality for exporting and importing session history.
 * Supports JSON format with versioning for forward compatibility.
 */

import { useCallback } from 'react';

const CURRENT_VERSION = '1.0';
const SUPPORTED_VERSIONS = ['1.0'];

export interface SessionData {
  id: string;
  title: string;
  messages: unknown[];
  createdAt?: string;
  updatedAt?: string;
}

export interface SessionExportMetadata {
  source: string;
  userAgent?: string;
  exportCount?: number;
}

export interface SessionExportData {
  version: string;
  exportedAt: string;
  sessions: SessionData[];
  metadata?: SessionExportMetadata;
}

export interface ExportOptions {
  includeMetadata?: boolean;
}

export interface UseSessionExportResult {
  exportSessions: (sessions: SessionData[], options?: ExportOptions) => SessionExportData;
  validateImportData: (data: SessionExportData) => boolean;
  parseImportString: (jsonString: string) => Promise<SessionExportData | null>;
  createDownloadUrl: (sessions: SessionData[], options?: ExportOptions) => string;
  revokeDownloadUrl: (url: string) => void;
  generateFilename: (prefix?: string) => string;
  filterSessionsByDate: (sessions: SessionData[], startDate: Date, endDate: Date) => SessionData[];
}

export function useSessionExport(): UseSessionExportResult {
  /**
   * Export sessions to the standard format
   */
  const exportSessions = useCallback(
    (sessions: SessionData[], options?: ExportOptions): SessionExportData => {
      const exportData: SessionExportData = {
        version: CURRENT_VERSION,
        exportedAt: new Date().toISOString(),
        sessions,
      };

      if (options?.includeMetadata) {
        exportData.metadata = {
          source: 'playground',
          userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
        };
      }

      return exportData;
    },
    []
  );

  /**
   * Validate imported data structure and version
   */
  const validateImportData = useCallback((data: SessionExportData): boolean => {
    // Check basic structure
    if (!data || typeof data !== 'object') {
      return false;
    }

    if (!data.version || typeof data.version !== 'string') {
      return false;
    }

    if (!SUPPORTED_VERSIONS.includes(data.version)) {
      return false;
    }

    if (!data.exportedAt || typeof data.exportedAt !== 'string') {
      return false;
    }

    if (!Array.isArray(data.sessions)) {
      return false;
    }

    return true;
  }, []);

  /**
   * Parse JSON string and validate
   */
  const parseImportString = useCallback(
    async (jsonString: string): Promise<SessionExportData | null> => {
      try {
        const parsed = JSON.parse(jsonString) as SessionExportData;
        if (validateImportData(parsed)) {
          return parsed;
        }
        return null;
      } catch {
        return null;
      }
    },
    [validateImportData]
  );

  /**
   * Create a downloadable URL for export data
   */
  const createDownloadUrl = useCallback(
    (sessions: SessionData[], options?: ExportOptions): string => {
      const exportData = exportSessions(sessions, options);
      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      return URL.createObjectURL(blob);
    },
    [exportSessions]
  );

  /**
   * Revoke a download URL to free memory
   */
  const revokeDownloadUrl = useCallback((url: string): void => {
    URL.revokeObjectURL(url);
  }, []);

  /**
   * Generate a filename with timestamp
   */
  const generateFilename = useCallback((prefix = 'playground-sessions'): string => {
    const date = new Date().toISOString().split('T')[0];
    return `${prefix}-${date}.json`;
  }, []);

  /**
   * Filter sessions by date range
   */
  const filterSessionsByDate = useCallback(
    (sessions: SessionData[], startDate: Date, endDate: Date): SessionData[] => {
      return sessions.filter((session) => {
        if (!session.createdAt) return false;
        const sessionDate = new Date(session.createdAt);
        return sessionDate >= startDate && sessionDate <= endDate;
      });
    },
    []
  );

  return {
    exportSessions,
    validateImportData,
    parseImportString,
    createDownloadUrl,
    revokeDownloadUrl,
    generateFilename,
    filterSessionsByDate,
  };
}
