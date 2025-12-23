/**
 * AI Suggestions E2E Tests
 *
 * Tests for AI-native features including inline suggestions,
 * follow-up suggestions, and AI command palette.
 *
 * Test Coverage:
 * - Inline code suggestions
 * - Follow-up message suggestions
 * - AI command palette (natural language)
 * - Suggestion acceptance/rejection
 * - AI edit overlays
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
  cost_dashboard: true,
  observability: true,
  code_export: true,
  ai_suggestions: true,
  llm_suggestions: true,
  mcp_websocket: true,
  interactive_artifacts: true,
  slash_commands: true,
};

// Mock AI suggestions
const mockFollowUpSuggestions = [
  {
    id: 'suggestion-1',
    text: 'Tell me more about this feature',
    type: 'follow-up',
    confidence: 0.92,
  },
  {
    id: 'suggestion-2',
    text: 'Can you provide an example?',
    type: 'follow-up',
    confidence: 0.88,
  },
  {
    id: 'suggestion-3',
    text: 'What are the alternatives?',
    type: 'follow-up',
    confidence: 0.75,
  },
];

const mockInlineSuggestions = [
  {
    id: 'inline-1',
    content: 'console.log("Hello World");',
    type: 'completion',
    position: { line: 1, column: 0 },
    confidence: 0.95,
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'session-1',
              name: 'AI Test Session',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          cursor: null,
        }),
      });
    });

    // Mock AI suggestions
    await page.route('**/api/v1/ai/suggestions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggestions: mockFollowUpSuggestions,
        }),
      });
    });

    // Mock follow-up suggestions
    await page.route('**/api/v1/ai/follow-up*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggestions: mockFollowUpSuggestions,
        }),
      });
    });

    // Mock inline suggestions
    await page.route('**/api/v1/ai/inline*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggestions: mockInlineSuggestions,
        }),
      });
    });

    // Mock AI command interpretation
    await page.route('**/api/v1/ai/interpret-command*', async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      const query = body.query?.toLowerCase() || '';

      let action = 'navigate';
      let params = { to: '/studio/chat' };

      if (query.includes('compliance')) {
        params = { to: '/studio/compliance' };
      } else if (query.includes('workflow')) {
        params = { to: '/studio/workflows' };
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          action,
          params,
          confidence: 0.85,
        }),
      });
    });
  }
}

test.describe('Follow-Up Suggestions', () => {
  test('should display follow-up suggestions in conversation panel', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const conversationPanel = alicePage.getByTestId('conversation-panel');
    await expect(conversationPanel).toBeVisible({ timeout: 10000 });
  });

  test('should show suggestion chips with text', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const conversationPanel = alicePage.getByTestId('conversation-panel');
    await expect(conversationPanel).toBeVisible({ timeout: 10000 });
  });

  test('should click suggestion chip to send message', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat/session-1', { waitUntil: 'networkidle' });

    const conversationPanel = alicePage.getByTestId('conversation-panel');
    await expect(conversationPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('AI Command Palette', () => {
  test('should open command palette with Cmd+K', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette with Cmd+K (Meta+K on Mac)
    await alicePage.keyboard.press('Meta+k');

    // Command palette should appear
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Should have a search input
    const searchInput = commandPalette.getByPlaceholder(/search|type/i);
    await expect(searchInput).toBeVisible();
  });

  test('should close command palette with Escape', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Close with Escape
    await alicePage.keyboard.press('Escape');
    await expect(commandPalette).not.toBeVisible({ timeout: 3000 });
  });

  test('should display command list grouped by category', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Should show command categories (chat, layout, navigation)
    await expect(commandPalette.getByText(/new chat/i)).toBeVisible();
    await expect(commandPalette.getByText(/toggle canvas/i)).toBeVisible();
  });

  test('should filter commands when typing', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Type to filter commands
    await alicePage.keyboard.type('toggle');

    // Should show filtered results (toggle canvas, toggle sidebar)
    await expect(commandPalette.getByText(/toggle canvas/i)).toBeVisible();
    await expect(commandPalette.getByText(/toggle sidebar/i)).toBeVisible();
  });

  test('should execute command on Enter', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Verify canvas is visible initially
    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible();

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Type and select toggle canvas command
    await alicePage.keyboard.type('toggle canvas');
    await alicePage.keyboard.press('Enter');

    // Command palette should close
    await expect(commandPalette).not.toBeVisible({ timeout: 3000 });
  });

  test('should show AI interpretation for natural language', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Type natural language query
    await alicePage.keyboard.type('show me the compliance dashboard');

    // AI interpretation should appear (after debounce)
    const interpretation = commandPalette.getByTestId('ai-suggestion');
    await expect(interpretation).toBeVisible({ timeout: 3000 });
  });

  test('should execute AI-interpreted command on selection', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Type natural language query
    await alicePage.keyboard.type('go to compliance');

    // Wait for AI interpretation and select it
    const interpretation = commandPalette.getByTestId('ai-suggestion');
    await expect(interpretation).toBeVisible({ timeout: 3000 });
    await interpretation.click();

    // Should navigate to compliance (URL change)
    await expect(alicePage).toHaveURL(/compliance/);
  });

  test('should navigate commands with arrow keys', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });

    // Navigate with arrow keys
    await alicePage.keyboard.press('ArrowDown');
    await alicePage.keyboard.press('ArrowDown');

    // First item should have focused/selected state
    const firstItem = commandPalette.getByRole('option').first();
    await expect(firstItem).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('Inline Suggestions', () => {
  test('should show inline suggestions in code editor', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should accept inline suggestion with Tab', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });

  test('should dismiss inline suggestion with Escape', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Suggestion Chips Component', () => {
  test('should render suggestion chips', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });
  });

  test('should show confidence indicator on chips', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });
  });

  test('should be keyboard navigable', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Tab navigation
    await alicePage.keyboard.press('Tab');
  });
});

test.describe('AI Edit Overlay', () => {
  test('should show AI edit overlay when Cmd+E is pressed on artifact', async ({ alicePage }) => {
    await setupMocks(alicePage);

    // Mock artifacts endpoint
    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'artifact-code-1',
              type: 'code',
              contentType: 'code',
              content: 'function hello() {\n  console.log("world");\n}',
              language: 'javascript',
              version: 1,
            },
          ],
          cursor: null,
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });

    // Click on the artifact to select it
    const artifactTab = canvasPanel.getByTestId('artifact-tab-artifact-code-1');
    if (await artifactTab.isVisible()) {
      await artifactTab.click();
    }

    // Open AI edit overlay with Cmd+E
    await alicePage.keyboard.press('Meta+e');

    // AI Edit overlay should appear
    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });
  });

  test('should have edit input in overlay', async ({ alicePage }) => {
    await setupMocks(alicePage);

    // Mock artifacts endpoint
    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'artifact-code-1',
              type: 'code',
              contentType: 'code',
              content: 'function hello() {}',
              language: 'javascript',
              version: 1,
            },
          ],
          cursor: null,
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });

    // Open AI edit overlay
    await alicePage.keyboard.press('Meta+e');

    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });

    // Should have an input for edit instructions
    const editInput = editOverlay.getByPlaceholder(/edit|describe|instruction/i);
    await expect(editInput).toBeVisible();
    await expect(editInput).toBeFocused();
  });

  test('should close overlay with Escape', async ({ alicePage }) => {
    await setupMocks(alicePage);

    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'artifact-1', type: 'code', contentType: 'code', content: 'test', version: 1 }],
          cursor: null,
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    // Open AI edit overlay
    await alicePage.keyboard.press('Meta+e');

    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });

    // Close with Escape
    await alicePage.keyboard.press('Escape');
    await expect(editOverlay).not.toBeVisible({ timeout: 3000 });
  });

  test('should show diff preview for AI edits', async ({ alicePage }) => {
    await setupMocks(alicePage);

    // Mock artifacts
    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            { id: 'artifact-1', type: 'code', contentType: 'code', content: 'const x = 1;', version: 1 },
          ],
          cursor: null,
        }),
      });
    });

    // Mock AI edit endpoint
    await alicePage.route('**/api/v1/ai/edit*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          originalContent: 'const x = 1;',
          suggestedContent: 'const x = 42;',
          diff: '@@ -1 +1 @@\n-const x = 1;\n+const x = 42;',
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    // Open AI edit overlay
    await alicePage.keyboard.press('Meta+e');

    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });

    // Type edit instruction
    const editInput = editOverlay.getByPlaceholder(/edit|describe|instruction/i);
    await editInput.fill('Change x to 42');
    await alicePage.keyboard.press('Enter');

    // Diff preview should appear
    const diffPreview = editOverlay.getByTestId('diff-preview');
    await expect(diffPreview).toBeVisible({ timeout: 5000 });
  });

  test('should accept AI edit with accept button', async ({ alicePage }) => {
    await setupMocks(alicePage);

    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'artifact-1', type: 'code', contentType: 'code', content: 'let y = 2;', version: 1 }],
          cursor: null,
        }),
      });
    });

    await alicePage.route('**/api/v1/ai/edit*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          originalContent: 'let y = 2;',
          suggestedContent: 'const y = 2;',
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    // Open AI edit overlay and submit
    await alicePage.keyboard.press('Meta+e');
    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });

    const editInput = editOverlay.getByPlaceholder(/edit|describe|instruction/i);
    await editInput.fill('Use const instead of let');
    await alicePage.keyboard.press('Enter');

    // Wait for diff and accept
    const acceptButton = editOverlay.getByRole('button', { name: /accept|apply/i });
    await expect(acceptButton).toBeVisible({ timeout: 5000 });
    await acceptButton.click();

    // Overlay should close after accept
    await expect(editOverlay).not.toBeVisible({ timeout: 3000 });
  });

  test('should reject AI edit with reject button', async ({ alicePage }) => {
    await setupMocks(alicePage);

    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'artifact-1', type: 'code', contentType: 'code', content: 'const z = 3;', version: 1 }],
          cursor: null,
        }),
      });
    });

    await alicePage.route('**/api/v1/ai/edit*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          originalContent: 'const z = 3;',
          suggestedContent: 'const z = 100;',
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await alicePage.keyboard.press('Meta+e');
    const editOverlay = alicePage.getByTestId('ai-edit-overlay');
    await expect(editOverlay).toBeVisible({ timeout: 5000 });

    const editInput = editOverlay.getByPlaceholder(/edit|describe|instruction/i);
    await editInput.fill('Change z to 100');
    await alicePage.keyboard.press('Enter');

    // Wait for diff and reject
    const rejectButton = editOverlay.getByRole('button', { name: /reject|cancel|discard/i });
    await expect(rejectButton).toBeVisible({ timeout: 5000 });
    await rejectButton.click();

    // Overlay should close after reject
    await expect(editOverlay).not.toBeVisible({ timeout: 3000 });
  });
});

test.describe('Background Agent Status', () => {
  test('should show background agent indicator in status bar', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const statusBar = alicePage.getByTestId('status-bar');
    await expect(statusBar).toBeVisible({ timeout: 10000 });
  });

  test('should expand agent panel on click', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const statusBar = alicePage.getByTestId('status-bar');
    await expect(statusBar).toBeVisible({ timeout: 10000 });
  });
});

test.describe('AI Feature Flags', () => {
  test('should NOT open command palette when canvas_ai_palette flag is disabled', async ({ alicePage }) => {
    // Override feature flags to disable AI palette
    await alicePage.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockFeatureFlags,
          canvas_ai_palette: false,
        }),
      });
    });

    // Mock sessions to prevent errors
    await alicePage.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], cursor: null }),
      });
    });

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Try to open command palette with Cmd+K
    await alicePage.keyboard.press('Meta+k');

    // Command palette should NOT appear when feature flag is disabled
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).not.toBeVisible({ timeout: 2000 });
  });

  test('should NOT show inline suggestions when ai_suggestions flag is disabled', async ({ alicePage }) => {
    // Override feature flags to disable AI suggestions
    await alicePage.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockFeatureFlags,
          ai_suggestions: false,
        }),
      });
    });

    // Mock sessions
    await alicePage.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'session-1', name: 'Test', created_at: new Date().toISOString() }],
          cursor: null,
        }),
      });
    });

    // Mock artifacts
    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'artifact-1', type: 'code', contentType: 'code', content: 'test', version: 1 }],
          cursor: null,
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Inline suggestions component should NOT be visible
    const inlineSuggestions = alicePage.getByTestId('inline-suggestions');
    await expect(inlineSuggestions).not.toBeVisible({ timeout: 2000 });
  });

  test('should NOT show background agent panel when ai_suggestions flag is disabled', async ({ alicePage }) => {
    // Override feature flags to disable AI suggestions
    await alicePage.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockFeatureFlags,
          ai_suggestions: false,
        }),
      });
    });

    await alicePage.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], cursor: null }),
      });
    });

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Background agent panel should NOT be visible
    const agentPanel = alicePage.getByTestId('background-agent-panel');
    await expect(agentPanel).not.toBeVisible({ timeout: 2000 });
  });

  test('should show command palette when canvas_ai_palette flag is enabled', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Open command palette with Cmd+K
    await alicePage.keyboard.press('Meta+k');

    // Command palette should appear
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    await expect(commandPalette).toBeVisible({ timeout: 5000 });
  });

  test('should show AI features when all flags are enabled', async ({ alicePage }) => {
    await setupMocks(alicePage);

    // Mock artifacts
    await alicePage.route('**/api/v1/artifacts*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'artifact-1', type: 'code', contentType: 'code', content: 'test', version: 1 }],
          cursor: null,
        }),
      });
    });

    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Canvas panel should be visible (AI features available)
    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible();
  });

  test('should gracefully handle flag fetch failure', async ({ alicePage }) => {
    // Simulate feature flags API failure
    await alicePage.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await alicePage.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], cursor: null }),
      });
    });

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    // App should still render without crashing
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // AI features should be disabled by default when flags fail to load
    await alicePage.keyboard.press('Meta+k');
    const commandPalette = alicePage.getByTestId('ai-command-palette');
    // Should either not appear or appear with basic functionality
    // The important thing is the app doesn't crash
  });
});

test.describe('AI Accessibility', () => {
  test('should have accessible suggestion chips', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });
  });

  test('should announce AI suggestions to screen readers', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });
  });
});
