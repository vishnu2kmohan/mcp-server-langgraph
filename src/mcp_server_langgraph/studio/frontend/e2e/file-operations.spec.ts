/**
 * File Operations E2E Tests
 *
 * Tests for the FilesPage file browser functionality including:
 * - File listing and search
 * - File preview modal
 * - File download
 * - File deletion
 * - View mode switching (grid/list)
 */

import { test, expect } from './fixtures/auth';

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags
const mockFeatureFlags = {
  canvas_hybrid_shell: true,
  canvas_editable: true,
  canvas_agents: true,
  canvas_ai_palette: true,
  canvas_compliance: true,
  canvas_help: true,
  workflows: true,
  sessions: true,
  cost_export: true,
  observability: true,
  code_export: true,
  ai_suggestions: true,
  llm_suggestions: true,
  mcp_websocket: true,
  interactive_artifacts: true,
  slash_commands: true,
};

// Mock files (artifacts)
const mockFiles = [
  {
    id: 'file-py-1',
    type: 'code',
    title: 'main.py',
    contentType: 'code',
    content: 'print("Hello, World!")\n\ndef greet(name):\n    return f"Hello, {name}!"',
    version: 1,
    sessionId: 'session-1',
    createdAt: '2025-01-01T10:00:00Z',
    updatedAt: '2025-01-01T11:00:00Z',
    editMetadata: {
      editedBy: 'ai',
      language: 'python',
    },
  },
  {
    id: 'file-md-1',
    type: 'markdown',
    title: 'README.md',
    contentType: 'document',
    content: '# Project README\n\nThis is a sample project.\n\n## Installation\n\n```bash\nnpm install\n```',
    version: 1,
    sessionId: 'session-1',
    createdAt: '2025-01-01T09:00:00Z',
    updatedAt: '2025-01-01T12:00:00Z',
    editMetadata: {
      editedBy: 'user',
    },
  },
  {
    id: 'file-json-1',
    type: 'json',
    title: 'config.json',
    contentType: 'data',
    content: '{\n  "name": "app",\n  "version": "1.0.0",\n  "debug": true\n}',
    version: 2,
    sessionId: 'session-1',
    createdAt: '2025-01-01T08:00:00Z',
    updatedAt: '2025-01-02T09:00:00Z',
    editMetadata: {
      editedBy: 'ai',
    },
  },
  {
    id: 'file-ts-1',
    type: 'code',
    title: 'utils.ts',
    contentType: 'code',
    content: 'export function formatDate(date: Date): string {\n  return date.toISOString();\n}',
    version: 1,
    sessionId: 'session-1',
    createdAt: '2025-01-02T10:00:00Z',
    updatedAt: '2025-01-02T10:00:00Z',
    editMetadata: {
      editedBy: 'user',
      language: 'typescript',
    },
  },
];

async function setupMocks(page: import('@playwright/test').Page) {
  if (!backendEnabled) {
    // Mock feature flags
    await page.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockFeatureFlags),
      });
    });

    // Mock sessions
    await page.route('**/api/v1/sessions*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'session-1',
                name: 'Test Session',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
            cursor: null,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Mock files (artifacts)
    await page.route('**/api/v1/artifacts*', async (route) => {
      const url = new URL(route.request().url());
      const artifactId = url.pathname.match(/\/artifacts\/([^/]+)/)?.[1];

      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: mockFiles, cursor: null }),
        });
      } else if (route.request().method() === 'DELETE' && artifactId) {
        await route.fulfill({
          status: 204,
        });
      } else {
        await route.continue();
      }
    });
  }
}

test.describe('FilesPage - File Browser', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should render files page with header', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('files-page')).toBeVisible({ timeout: 10000 });
    await expect(alicePage.getByText('Files')).toBeVisible();
  });

  test('should display file count in header', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Should show count of files
    await expect(alicePage.getByText(/4 files/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display files in grid view by default', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Should show file cards
    await expect(alicePage.getByTestId('file-card-file-py-1')).toBeVisible({ timeout: 10000 });
    await expect(alicePage.getByTestId('file-card-file-md-1')).toBeVisible();
    await expect(alicePage.getByTestId('file-card-file-json-1')).toBeVisible();
    await expect(alicePage.getByTestId('file-card-file-ts-1')).toBeVisible();
  });

  test('should show file names with extensions', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await expect(alicePage.getByText('main.py')).toBeVisible({ timeout: 10000 });
    await expect(alicePage.getByText('README.md')).toBeVisible();
    await expect(alicePage.getByText('config.json')).toBeVisible();
    await expect(alicePage.getByText('utils.ts')).toBeVisible();
  });
});

test.describe('FilesPage - View Mode Switching', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should switch to list view', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Click list view button
    await alicePage.getByTestId('view-list').click();

    // Should now show table/list format
    await expect(alicePage.getByRole('table')).toBeVisible({ timeout: 5000 });
  });

  test('should switch back to grid view', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Switch to list then back to grid
    await alicePage.getByTestId('view-list').click();
    await alicePage.getByTestId('view-grid').click();

    // Should show grid (cards)
    await expect(alicePage.getByTestId('file-card-file-py-1')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('FilesPage - Search', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should filter files by search query', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Search for "main"
    await alicePage.getByTestId('file-search').fill('main');

    // Should only show main.py
    await expect(alicePage.getByText('main.py')).toBeVisible({ timeout: 5000 });
    await expect(alicePage.getByText('README.md')).not.toBeVisible();
    await expect(alicePage.getByText('config.json')).not.toBeVisible();
  });

  test('should show no results message when search has no matches', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Search for non-existent file
    await alicePage.getByTestId('file-search').fill('nonexistent');

    // Should show no files match message
    await expect(alicePage.getByText(/no files match/i)).toBeVisible({ timeout: 5000 });
  });

  test('should update file count based on search results', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Search for ".json"
    await alicePage.getByTestId('file-search').fill('.json');

    // Should show 1 file count
    await expect(alicePage.getByText(/1 file/i)).toBeVisible({ timeout: 5000 });
  });
});

test.describe('FilesPage - Preview Modal', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should open preview modal when clicking file card', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Click on main.py card
    await alicePage.getByTestId('file-card-file-py-1').click();

    // Preview modal should appear
    await expect(alicePage.getByTestId('preview-modal')).toBeVisible({ timeout: 5000 });
  });

  test('should show file name in preview modal header', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await alicePage.getByTestId('file-card-file-py-1').click();

    const modal = alicePage.getByTestId('preview-modal');
    await expect(modal.getByText('main.py')).toBeVisible({ timeout: 5000 });
  });

  test('should show file content in preview modal', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await alicePage.getByTestId('file-card-file-py-1').click();

    const modal = alicePage.getByTestId('preview-modal');
    await expect(modal.getByText(/print\("Hello, World!"\)/)).toBeVisible({ timeout: 5000 });
  });

  test('should close preview modal when clicking X button', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await alicePage.getByTestId('file-card-file-py-1').click();
    await expect(alicePage.getByTestId('preview-modal')).toBeVisible({ timeout: 5000 });

    // Click close button
    await alicePage.getByLabel('Close preview').click();

    // Modal should be hidden
    await expect(alicePage.getByTestId('preview-modal')).not.toBeVisible();
  });

  test('should close preview modal when clicking backdrop', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    await alicePage.getByTestId('file-card-file-py-1').click();
    await expect(alicePage.getByTestId('preview-modal')).toBeVisible({ timeout: 5000 });

    // Click the backdrop (the modal overlay)
    await alicePage.getByTestId('preview-modal').click({ position: { x: 10, y: 10 } });

    // Modal should be hidden
    await expect(alicePage.getByTestId('preview-modal')).not.toBeVisible();
  });
});

test.describe('FilesPage - Download', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should trigger download when clicking download button', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Listen for download
    const downloadPromise = alicePage.waitForEvent('download');

    // Click download button on first file card
    const fileCard = alicePage.getByTestId('file-card-file-py-1');
    await fileCard.getByLabel('Download').click();

    // Verify download started
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('main.py');
  });

  test('should allow download from preview modal', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Open preview modal
    await alicePage.getByTestId('file-card-file-py-1').click();
    await expect(alicePage.getByTestId('preview-modal')).toBeVisible({ timeout: 5000 });

    // Listen for download
    const downloadPromise = alicePage.waitForEvent('download');

    // Click download button in modal
    const modal = alicePage.getByTestId('preview-modal');
    await modal.getByRole('button', { name: /download/i }).click();

    // Verify download started
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('main.py');
  });
});

test.describe('FilesPage - Delete', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should show delete confirmation modal when clicking delete button', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Click delete button on first file card
    const fileCard = alicePage.getByTestId('file-card-file-py-1');
    await fileCard.getByLabel('Delete').click();

    // Confirmation modal should appear
    await expect(alicePage.getByTestId('delete-confirm-modal')).toBeVisible({ timeout: 5000 });
    await expect(alicePage.getByText('Delete File')).toBeVisible();
  });

  test('should show file name in delete confirmation', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    const fileCard = alicePage.getByTestId('file-card-file-py-1');
    await fileCard.getByLabel('Delete').click();

    // Should show the file name being deleted
    await expect(alicePage.getByText('main.py')).toBeVisible({ timeout: 5000 });
  });

  test('should close confirmation modal when clicking Cancel', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    const fileCard = alicePage.getByTestId('file-card-file-py-1');
    await fileCard.getByLabel('Delete').click();

    await expect(alicePage.getByTestId('delete-confirm-modal')).toBeVisible({ timeout: 5000 });

    // Click Cancel
    await alicePage.getByRole('button', { name: /cancel/i }).click();

    // Modal should be hidden
    await expect(alicePage.getByTestId('delete-confirm-modal')).not.toBeVisible();
  });

  test('should delete file when confirming', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    const fileCard = alicePage.getByTestId('file-card-file-py-1');
    await fileCard.getByLabel('Delete').click();

    await expect(alicePage.getByTestId('delete-confirm-modal')).toBeVisible({ timeout: 5000 });

    // Intercept the DELETE request
    const deleteRequest = alicePage.waitForRequest((request) =>
      request.method() === 'DELETE' && request.url().includes('/artifacts/')
    );

    // Click delete button in modal
    await alicePage.getByRole('button', { name: /delete$/i }).click();

    // Should have sent DELETE request
    const request = await deleteRequest;
    expect(request.url()).toContain('/artifacts/file-py-1');

    // Modal should close
    await expect(alicePage.getByTestId('delete-confirm-modal')).not.toBeVisible();
  });
});

test.describe('FilesPage - List View Actions', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should show action buttons in list view', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Switch to list view
    await alicePage.getByTestId('view-list').click();

    // Should have action buttons in the table
    const table = alicePage.getByRole('table');
    await expect(table.getByLabel('Preview')).toBeVisible({ timeout: 5000 });
    await expect(table.getByLabel('Download').first()).toBeVisible();
    await expect(table.getByLabel('Delete').first()).toBeVisible();
  });

  test('should open preview from list view', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/files', { waitUntil: 'networkidle' });

    // Switch to list view
    await alicePage.getByTestId('view-list').click();

    // Click preview button in first row
    const table = alicePage.getByRole('table');
    await table.getByLabel('Preview').first().click();

    // Preview modal should appear
    await expect(alicePage.getByTestId('preview-modal')).toBeVisible({ timeout: 5000 });
  });
});
