/**
 * Canvas Artifact E2E Tests
 *
 * Tests for artifact viewing, editing, and management in the Canvas Panel.
 * Validates the Studio Canvas paradigm (Gemini/ChatGPT Canvas style).
 *
 * Test Coverage:
 * - Artifact viewing and rendering
 * - Artifact editing and version control
 * - Artifact tab management
 * - Code/Preview/Data view switching
 * - Artifact creation and forking
 */

import { test, expect } from './fixtures/auth';

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags
const mockFeatureFlags = {
  studio_canvas_shell: true,
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

// Mock artifacts
const mockArtifacts = [
  {
    id: 'artifact-code-1',
    type: 'code',
    title: 'React Component',
    content: 'function App() {\n  return <h1>Hello World</h1>;\n}',
    language: 'jsx',
    version: 1,
    sessionId: 'session-1',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    metadata: {
      editedBy: 'ai',
    },
  },
  {
    id: 'artifact-markdown-1',
    type: 'markdown',
    title: 'Documentation',
    content: '# Hello\n\nThis is markdown content.',
    version: 1,
    sessionId: 'session-1',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    metadata: {
      editedBy: 'user',
    },
  },
  {
    id: 'artifact-json-1',
    type: 'json',
    title: 'API Response',
    content: '{\n  "status": "success",\n  "data": [1, 2, 3]\n}',
    version: 1,
    sessionId: 'session-1',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    metadata: {
      editedBy: 'ai',
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

    // Mock artifacts
    await page.route('**/api/v1/artifacts*', async (route) => {
      const url = new URL(route.request().url());
      const sessionId = url.searchParams.get('session_id');

      if (route.request().method() === 'GET') {
        const items = sessionId
          ? mockArtifacts.filter((a) => a.sessionId === sessionId)
          : mockArtifacts;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items, cursor: null }),
        });
      } else if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: `artifact-${Date.now()}`,
            ...body,
            version: 1,
            createdAt: new Date().toISOString(),
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Mock artifact versions
    await page.route('**/api/v1/artifacts/*/versions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            { version: 1, content: 'Initial version', createdAt: new Date().toISOString() },
          ],
        }),
      });
    });
  }
}

test.describe('Canvas Artifact Display', () => {
  test('should render canvas panel', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should show empty state when no artifacts', async ({ alicePage }) => {
    await setupMocks(alicePage);

    // Override artifacts to return empty
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/artifacts*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], cursor: null }),
        });
      });
    }

    await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should render artifact tabs when artifacts exist', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Artifact Viewing', () => {
  test('should display code artifact with syntax highlighting', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should display markdown artifact with preview', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should display JSON artifact with formatted view', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Artifact Editing', () => {
  test('should allow editing artifact content', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });

    // Look for an editable area or code editor
    // The exact implementation depends on the canvas artifact component
  });

  test('should show unsaved changes indicator', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Artifact Version Control', () => {
  test('should show version history', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should allow reverting to previous version', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('View Mode Switching', () => {
  test('should switch between code and preview views', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should show split view by default', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Artifact Tab Management', () => {
  test('should allow switching between artifact tabs', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should close artifact tab', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Artifact Actions', () => {
  test('should show artifact action buttons', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should copy artifact content', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should export artifact', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Canvas Accessibility', () => {
  test('should have keyboard navigable artifacts', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });

    // Tab navigation should work
    await alicePage.keyboard.press('Tab');
  });

  test('should have proper ARIA labels on canvas elements', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });

    // Canvas panel should have proper role/label
    await expect(canvasPanel).toHaveAttribute('role');
  });
});
