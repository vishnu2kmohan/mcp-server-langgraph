/**
 * useSessionExport Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionExport, type SessionExportData } from './useSessionExport';

describe('useSessionExport', () => {
  // Mock URL.createObjectURL and URL.revokeObjectURL
  const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
  const mockRevokeObjectURL = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should_export_sessions_as_json', () => {
    const { result } = renderHook(() => useSessionExport());

    const sessions = [
      {
        id: 'session-1',
        title: 'Test Session',
        messages: [{ role: 'user', content: 'Hello' }],
        createdAt: '2024-01-01T00:00:00Z',
      },
    ];

    let exportData: SessionExportData | null = null;
    act(() => {
      exportData = result.current.exportSessions(sessions);
    });

    expect(exportData).not.toBeNull();
    expect(exportData!.version).toBe('1.0');
    expect(exportData!.sessions).toEqual(sessions);
    expect(exportData!.exportedAt).toBeDefined();
  });

  it('should_include_metadata_in_export', () => {
    const { result } = renderHook(() => useSessionExport());

    const sessions = [{ id: 'session-1', title: 'Test', messages: [] }];

    let exportData: SessionExportData | null = null;
    act(() => {
      exportData = result.current.exportSessions(sessions, { includeMetadata: true });
    });

    expect(exportData!.metadata).toBeDefined();
    expect(exportData!.metadata?.source).toBe('playground');
  });

  it('should_validate_import_data_format', () => {
    const { result } = renderHook(() => useSessionExport());

    const validData: SessionExportData = {
      version: '1.0',
      exportedAt: '2024-01-01T00:00:00Z',
      sessions: [{ id: 'session-1', title: 'Test', messages: [] }],
    };

    let validationResult: boolean = false;
    act(() => {
      validationResult = result.current.validateImportData(validData);
    });

    expect(validationResult).toBe(true);
  });

  it('should_reject_invalid_import_data', () => {
    const { result } = renderHook(() => useSessionExport());

    const invalidData = { notValid: true };

    let validationResult: boolean = true;
    act(() => {
      validationResult = result.current.validateImportData(invalidData as unknown as SessionExportData);
    });

    expect(validationResult).toBe(false);
  });

  it('should_reject_unsupported_version', () => {
    const { result } = renderHook(() => useSessionExport());

    const unsupportedVersionData: SessionExportData = {
      version: '99.0',
      exportedAt: '2024-01-01T00:00:00Z',
      sessions: [],
    };

    let validationResult: boolean = true;
    act(() => {
      validationResult = result.current.validateImportData(unsupportedVersionData);
    });

    expect(validationResult).toBe(false);
  });

  it('should_parse_json_from_string', async () => {
    const { result } = renderHook(() => useSessionExport());

    const jsonString = JSON.stringify({
      version: '1.0',
      exportedAt: '2024-01-01T00:00:00Z',
      sessions: [{ id: 'session-1', title: 'Imported', messages: [] }],
    });

    let importedData: SessionExportData | null = null;
    await act(async () => {
      importedData = await result.current.parseImportString(jsonString);
    });

    expect(importedData).not.toBeNull();
    expect(importedData!.sessions).toHaveLength(1);
    expect(importedData!.sessions[0].title).toBe('Imported');
  });

  it('should_return_null_for_invalid_json', async () => {
    const { result } = renderHook(() => useSessionExport());

    let importedData: SessionExportData | null = { version: '1.0', exportedAt: '', sessions: [] };
    await act(async () => {
      importedData = await result.current.parseImportString('not valid json {{{');
    });

    expect(importedData).toBeNull();
  });

  it('should_generate_download_link', () => {
    const { result } = renderHook(() => useSessionExport());

    const sessions = [{ id: 'session-1', title: 'Test', messages: [] }];

    let downloadUrl: string = '';
    act(() => {
      downloadUrl = result.current.createDownloadUrl(sessions);
    });

    expect(downloadUrl).toBe('blob:mock-url');
    expect(mockCreateObjectURL).toHaveBeenCalled();
  });

  it('should_cleanup_download_url', () => {
    const { result } = renderHook(() => useSessionExport());

    act(() => {
      result.current.revokeDownloadUrl('blob:mock-url');
    });

    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should_generate_filename_with_timestamp', () => {
    const { result } = renderHook(() => useSessionExport());

    let filename: string = '';
    act(() => {
      filename = result.current.generateFilename();
    });

    expect(filename).toMatch(/^playground-sessions-\d{4}-\d{2}-\d{2}\.json$/);
  });

  it('should_filter_sessions_by_date_range', () => {
    const { result } = renderHook(() => useSessionExport());

    const sessions = [
      { id: '1', title: 'Old', messages: [], createdAt: '2023-01-01T00:00:00Z' },
      { id: '2', title: 'Recent', messages: [], createdAt: '2024-06-15T00:00:00Z' },
      { id: '3', title: 'New', messages: [], createdAt: '2024-12-01T00:00:00Z' },
    ];

    let filtered: unknown[] = [];
    act(() => {
      filtered = result.current.filterSessionsByDate(
        sessions,
        new Date('2024-01-01'),
        new Date('2024-07-01')
      );
    });

    expect(filtered).toHaveLength(1);
    expect((filtered[0] as { title: string }).title).toBe('Recent');
  });
});
