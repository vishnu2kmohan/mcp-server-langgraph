/**
 * Execution History E2E Tests
 *
 * Tests for the WorkflowsPage execution history panel functionality:
 * - Viewing execution history
 * - Pagination through executions
 * - Execution status display
 * - Execution details viewing
 * - Re-running executions
 */

import { test, expect } from './fixtures/auth';

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags
const mockFeatureFlags = {
  canvas_studio_shell: true,
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

// Mock workflow
const mockWorkflow = {
  id: 'wf-test-1',
  name: 'Test Workflow',
  description: 'A workflow for testing execution history',
  nodes: [
    {
      id: 'node-1',
      type: 'default',
      position: { x: 100, y: 100 },
      data: {
        label: 'Start Node',
        nodeType: 'input',
        config: {},
      },
    },
  ],
  edges: [],
  version: 1,
  createdAt: '2025-01-01T10:00:00Z',
  updatedAt: '2025-01-02T11:00:00Z',
};

// Generate mock executions with pagination support
function generateMockExecutions(page: number, pageSize: number = 10) {
  const executions = [];
  const totalExecutions = 35; // Total for pagination testing
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalExecutions);

  for (let i = startIndex; i < endIndex; i++) {
    const status = ['completed', 'failed', 'running', 'pending'][i % 4];
    const baseTime = new Date('2025-01-15T10:00:00Z').getTime();
    const startedAt = new Date(baseTime - i * 3600000).toISOString();
    const completedAt = status === 'completed' || status === 'failed'
      ? new Date(baseTime - i * 3600000 + 300000).toISOString()
      : null;

    executions.push({
      id: `exec-${i + 1}`,
      workflow_id: 'wf-test-1',
      status,
      started_at: startedAt,
      completed_at: completedAt,
      input_data: { query: `Test query ${i + 1}` },
      output_data: status === 'completed' ? { result: `Result ${i + 1}` } : null,
      error: status === 'failed' ? `Error in execution ${i + 1}` : null,
      duration_ms: status !== 'pending' && status !== 'running' ? 300000 : null,
    });
  }

  const hasNextPage = endIndex < totalExecutions;

  return {
    items: executions,
    total: totalExecutions,
    page,
    page_size: pageSize,
    next_cursor: hasNextPage ? `cursor-page-${page + 1}` : null,
  };
}

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

    // Mock workflow
    await page.route('**/api/v1/workflows/wf-test-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockWorkflow),
      });
    });

    // Mock workflow list
    await page.route('**/api/v1/workflows', async (route) => {
      if (!route.request().url().includes('/wf-test-1')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [mockWorkflow],
            cursor: null,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Mock execution history with pagination
    await page.route('**/api/v1/workflows/*/executions*', async (route) => {
      const url = new URL(route.request().url());
      const cursor = url.searchParams.get('cursor');
      const pageNum = cursor ? parseInt(cursor.split('-').pop() || '1', 10) : 1;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(generateMockExecutions(pageNum)),
      });
    });

    // Mock single execution details
    await page.route('**/api/v1/executions/*', async (route) => {
      const execId = route.request().url().split('/').pop();
      const execNum = parseInt(execId?.split('-').pop() || '1', 10);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: execId,
          workflow_id: 'wf-test-1',
          status: 'completed',
          started_at: '2025-01-15T10:00:00Z',
          completed_at: '2025-01-15T10:05:00Z',
          input_data: { query: `Test query ${execNum}` },
          output_data: { result: `Result ${execNum}` },
          logs: [
            { timestamp: '2025-01-15T10:00:00Z', level: 'info', message: 'Starting execution' },
            { timestamp: '2025-01-15T10:01:00Z', level: 'info', message: 'Processing input' },
            { timestamp: '2025-01-15T10:05:00Z', level: 'info', message: 'Execution complete' },
          ],
        }),
      });
    });

    // Mock sessions (required for layout)
    await page.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], cursor: null }),
      });
    });
  }
}

test.describe('Execution History Panel - Opening/Closing', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should have History button in workflow toolbar', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByRole('button', { name: /history/i })).toBeVisible({ timeout: 10000 });
  });

  test('should open execution history panel when History button is clicked', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });

    // Click History button
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Execution history panel should appear
    await expect(alicePage.getByText('Execution History')).toBeVisible({ timeout: 5000 });
  });

  test('should close execution history panel when toggled', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });

    // Open history panel
    await alicePage.getByRole('button', { name: /history/i }).click();
    await expect(alicePage.getByText('Execution History')).toBeVisible({ timeout: 5000 });

    // Click History button again to close
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Panel should be hidden
    await expect(alicePage.getByText('Execution History')).not.toBeVisible();
  });
});

test.describe('Execution History Panel - Execution List', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should display total execution count', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Should show total count
    await expect(alicePage.getByText(/35 executions/i)).toBeVisible({ timeout: 5000 });
  });

  test('should display execution list items', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Should show execution items
    await expect(alicePage.getByTestId('execution-item-exec-1')).toBeVisible({ timeout: 5000 });
  });

  test('should show execution status with color coding', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // First execution should be completed (green)
    const firstExecution = alicePage.getByTestId('execution-item-exec-1');
    await expect(firstExecution.getByText(/completed/i)).toBeVisible({ timeout: 5000 });
  });

  test('should show execution timestamp', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Should show timestamps
    const firstExecution = alicePage.getByTestId('execution-item-exec-1');
    await expect(firstExecution).toContainText(/Jan 15/); // From our mock data
  });
});

test.describe('Execution History Panel - Pagination', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should show load more button when more pages exist', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Wait for list to load
    await expect(alicePage.getByTestId('execution-item-exec-1')).toBeVisible({ timeout: 5000 });

    // Should show load more button
    await expect(alicePage.getByRole('button', { name: /load more/i })).toBeVisible();
  });

  test('should load next page when clicking load more', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Wait for initial list
    await expect(alicePage.getByTestId('execution-item-exec-1')).toBeVisible({ timeout: 5000 });

    // Click load more
    await alicePage.getByRole('button', { name: /load more/i }).click();

    // Should now show executions from page 2 (exec-11 to exec-20)
    await expect(alicePage.getByTestId('execution-item-exec-11')).toBeVisible({ timeout: 5000 });
  });

  test('should show cumulative count of loaded executions', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Wait for initial list
    await expect(alicePage.getByTestId('execution-item-exec-1')).toBeVisible({ timeout: 5000 });

    // Should show "Showing 10 of 35" or similar
    await expect(alicePage.getByText(/showing.*10.*of.*35/i)).toBeVisible();

    // Load more
    await alicePage.getByRole('button', { name: /load more/i }).click();

    // Should now show "Showing 20 of 35"
    await expect(alicePage.getByText(/showing.*20.*of.*35/i)).toBeVisible({ timeout: 5000 });
  });

  test('should hide load more button on last page', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Load all pages (35 items = 4 pages)
    await expect(alicePage.getByTestId('execution-item-exec-1')).toBeVisible({ timeout: 5000 });

    await alicePage.getByRole('button', { name: /load more/i }).click();
    await expect(alicePage.getByTestId('execution-item-exec-11')).toBeVisible({ timeout: 5000 });

    await alicePage.getByRole('button', { name: /load more/i }).click();
    await expect(alicePage.getByTestId('execution-item-exec-21')).toBeVisible({ timeout: 5000 });

    await alicePage.getByRole('button', { name: /load more/i }).click();
    await expect(alicePage.getByTestId('execution-item-exec-31')).toBeVisible({ timeout: 5000 });

    // Load more button should be hidden (no more pages)
    await expect(alicePage.getByRole('button', { name: /load more/i })).not.toBeVisible();
  });
});

test.describe('Execution History Panel - Execution Details', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should show execution details when clicking an execution', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Click on first execution
    await alicePage.getByTestId('execution-item-exec-1').click();

    // Details panel should appear
    await expect(alicePage.getByTestId('execution-details')).toBeVisible({ timeout: 5000 });
  });

  test('should show input data in execution details', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();
    await alicePage.getByTestId('execution-item-exec-1').click();

    // Should show input data
    await expect(alicePage.getByText(/input/i)).toBeVisible({ timeout: 5000 });
    await expect(alicePage.getByText(/test query/i)).toBeVisible();
  });

  test('should show output data in execution details', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();
    await alicePage.getByTestId('execution-item-exec-1').click();

    // Should show output data
    await expect(alicePage.getByText(/output/i)).toBeVisible({ timeout: 5000 });
    await expect(alicePage.getByText(/result/i)).toBeVisible();
  });

  test('should show execution logs', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();
    await alicePage.getByTestId('execution-item-exec-1').click();

    // Should show logs
    await expect(alicePage.getByText(/logs/i)).toBeVisible({ timeout: 5000 });
    await expect(alicePage.getByText(/starting execution/i)).toBeVisible();
    await expect(alicePage.getByText(/execution complete/i)).toBeVisible();
  });
});

test.describe('Execution History Panel - Re-run Execution', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should have re-run button in execution details', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();
    await alicePage.getByTestId('execution-item-exec-1').click();

    // Should have re-run button
    await expect(alicePage.getByRole('button', { name: /re-run/i })).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Execution History Panel - Status Filtering', () => {
  test.beforeEach(async ({ alicePage }) => {
    await setupMocks(alicePage);
  });

  test('should have status filter dropdown', async ({ alicePage }) => {
    await alicePage.goto('/studio/v2/workflows?id=wf-test-1', { waitUntil: 'networkidle' });
    await alicePage.getByRole('button', { name: /history/i }).click();

    // Should have filter options
    await expect(alicePage.getByTestId('status-filter')).toBeVisible({ timeout: 5000 });
  });
});
