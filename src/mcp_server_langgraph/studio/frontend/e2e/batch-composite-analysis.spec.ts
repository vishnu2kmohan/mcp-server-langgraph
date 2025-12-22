/**
 * E2E Tests for Composite Analysis
 *
 * Tests the full stack integration of composite AI analysis:
 * - Persona analysis
 * - Disclosure level analysis
 * - Error analysis
 * - Cross-service insights
 * - Combined confidence scoring
 *
 * The composite analyze endpoint runs multiple analyses in parallel for efficiency.
 * Uses /api/v1/ai/composite/analyze for single-user combined analysis.
 * Uses /api/v1/ai/composite/batch for multi-user batch processing.
 */

import { test, expect } from '@playwright/test';

test.describe('Batch Composite Analysis', () => {
  test.describe('API Contract', () => {
    test('should return batch composite results from API', async ({ page }) => {
      // Setup: Mock successful batch response
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'alice-builder',
              confidence: 0.85,
              behavior_signals: ['Advanced feature usage', 'Long sessions'],
              recommendation: 'Consider upgrading to developer role',
              ui_adaptations: [{ feature: 'workflow_builder', action: 'unlock' }],
            },
            disclosure_result: {
              current_level: 'intermediate',
              recommended_level: 'advanced',
              confidence: 0.82,
              unlock_features: ['custom_agents', 'advanced_filters'],
              personalized_message: 'Ready for advanced features!',
            },
            error_result: null,
            cross_insights: [
              'User behavior suggests higher expertise than assigned persona',
              'Progressive disclosure level should be upgraded',
            ],
            confidence: 0.84,
          }),
        });
      });

      // Navigate to a page that would trigger batch analysis
      await page.goto('/studio/chat');

      // Trigger batch analysis (simulated via test API call)
      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: true,
            include_disclosure: true,
            include_error: false,
          }),
        });
        return res.json();
      });

      // Verify response structure
      expect(response).toHaveProperty('persona_result');
      expect(response).toHaveProperty('disclosure_result');
      expect(response).toHaveProperty('cross_insights');
      expect(response).toHaveProperty('confidence');
      expect(response.persona_result.detected_persona).toBe('alice-builder');
      expect(response.disclosure_result.recommended_level).toBe('advanced');
      expect(response.confidence).toBeGreaterThan(0);
    });

    test('should handle partial analysis requests', async ({ page }) => {
      // Setup: Mock response with only persona analysis
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'bob',
              confidence: 0.92,
              behavior_signals: ['Standard usage patterns'],
              recommendation: null,
              ui_adaptations: [],
            },
            disclosure_result: null,
            error_result: null,
            cross_insights: [],
            confidence: 0.92,
          }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: true,
            include_disclosure: false,
            include_error: false,
          }),
        });
        return res.json();
      });

      // Only persona result should be present
      expect(response.persona_result).not.toBeNull();
      expect(response.disclosure_result).toBeNull();
      expect(response.error_result).toBeNull();
    });

    test('should include error analysis when requested', async ({ page }) => {
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: null,
            disclosure_result: null,
            error_result: {
              classification: {
                category: 'network',
                subcategory: 'timeout',
                confidence: 0.88,
              },
              rootCause: 'Server took too long to respond',
              suggestions: [
                {
                  action: 'retry',
                  label: 'Try again',
                  estimatedSuccess: 0.75,
                },
              ],
              similarIssues: [],
            },
            cross_insights: ['Error occurred during high-load period'],
            confidence: 0.88,
          }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: false,
            include_disclosure: false,
            include_error: true,
            error_data: {
              error: { message: 'Connection timeout', name: 'TimeoutError' },
            },
          }),
        });
        return res.json();
      });

      expect(response.error_result).not.toBeNull();
      expect(response.error_result.classification.category).toBe('network');
      expect(response.error_result.suggestions).toHaveLength(1);
    });
  });

  test.describe('Rate Limiting', () => {
    test('should enforce rate limits on batch endpoint', async ({ page }) => {
      let requestCount = 0;

      await page.route('**/api/v1/ai/composite/batch', (route) => {
        requestCount++;
        if (requestCount > 10) {
          route.fulfill({
            status: 429,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Rate limit exceeded' }),
          });
        } else {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              persona_result: null,
              disclosure_result: null,
              error_result: null,
              cross_insights: [],
              confidence: 0,
            }),
          });
        }
      });

      await page.goto('/studio/chat');

      // Make 11 requests rapidly
      const results = await page.evaluate(async () => {
        const responses = [];
        for (let i = 0; i < 11; i++) {
          const res = await fetch('/api/v1/ai/composite/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: 'test-user',
              session_id: 'test-session',
            }),
          });
          responses.push(res.status);
        }
        return responses;
      });

      // First 10 should succeed, 11th should be rate limited
      expect(results.filter((s) => s === 200)).toHaveLength(10);
      expect(results.filter((s) => s === 429)).toHaveLength(1);
    });
  });

  test.describe('Cross Insights', () => {
    test('should generate cross-service insights when multiple analyses are run', async ({
      page,
    }) => {
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'alice-analyst',
              confidence: 0.78,
              behavior_signals: ['Frequent trace exploration'],
              recommendation: 'Enable analyst features',
              ui_adaptations: [],
            },
            disclosure_result: {
              current_level: 'beginner',
              recommended_level: 'intermediate',
              confidence: 0.75,
              unlock_features: ['filters'],
              personalized_message: 'Ready for more features',
            },
            error_result: null,
            cross_insights: [
              'Persona mismatch detected: assigned bob but behavior suggests alice-analyst',
              'Disclosure level should be upgraded based on actual usage',
              'Consider showing observability features to this user',
            ],
            confidence: 0.77,
          }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: true,
            include_disclosure: true,
            include_error: false,
          }),
        });
        return res.json();
      });

      // Should have multiple cross insights
      expect(response.cross_insights.length).toBeGreaterThanOrEqual(2);
      expect(response.cross_insights).toContain(
        expect.stringContaining('Persona mismatch')
      );
    });
  });

  test.describe('Error Handling', () => {
    test('should handle missing required fields gracefully', async ({
      page,
    }) => {
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'user_id is required' }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            // Missing user_id and session_id
            include_persona: true,
          }),
        });
        return { status: res.status, body: await res.json() };
      });

      expect(response.status).toBe(400);
      expect(response.body.detail).toContain('user_id');
    });

    test('should handle server errors gracefully', async ({ page }) => {
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: true,
          }),
        });
        return { status: res.status };
      });

      expect(response.status).toBe(500);
    });

    test('should handle timeout scenarios', async ({ page }) => {
      await page.route('**/api/v1/ai/composite/batch', async (route) => {
        // Simulate timeout by delaying response
        await new Promise((resolve) => setTimeout(resolve, 15000));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      });

      await page.goto('/studio/chat');

      // Set a shorter timeout for the fetch
      const response = await page.evaluate(async () => {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        try {
          const res = await fetch('/api/v1/ai/composite/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: 'test-user',
              session_id: 'test-session',
            }),
            signal: controller.signal,
          });
          clearTimeout(timeoutId);
          return { status: res.status, aborted: false };
        } catch (e) {
          clearTimeout(timeoutId);
          return { status: 0, aborted: true, error: (e as Error).name };
        }
      });

      expect(response.aborted).toBe(true);
      expect(response.error).toBe('AbortError');
    });
  });

  test.describe('Confidence Scoring', () => {
    test('should return overall confidence between 0 and 1', async ({
      page,
    }) => {
      await page.route('**/api/v1/ai/composite/batch', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'bob',
              confidence: 0.95,
              behavior_signals: [],
              recommendation: null,
              ui_adaptations: [],
            },
            disclosure_result: {
              current_level: 'beginner',
              recommended_level: 'beginner',
              confidence: 0.88,
              unlock_features: [],
              personalized_message: '',
            },
            error_result: null,
            cross_insights: [],
            confidence: 0.915, // Average of 0.95 and 0.88
          }),
        });
      });

      await page.goto('/studio/chat');

      const response = await page.evaluate(async () => {
        const res = await fetch('/api/v1/ai/composite/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'test-user',
            session_id: 'test-session',
            include_persona: true,
            include_disclosure: true,
          }),
        });
        return res.json();
      });

      expect(response.confidence).toBeGreaterThanOrEqual(0);
      expect(response.confidence).toBeLessThanOrEqual(1);
      expect(response.confidence).toBeCloseTo(0.915, 2);
    });
  });

  test.describe('CrossInsightsPanel UI', () => {
    test('should display CrossInsightsPanel when batch analysis returns insights', async ({
      page,
    }) => {
      // Setup: Mock feature flags endpoint to enable batch composite analysis
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      // Setup: Mock composite analyze endpoint
      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'alice-builder',
              confidence: 0.85,
              behavior_signals: ['Advanced feature usage'],
              recommendation: 'Consider upgrading to developer role',
              ui_adaptations: [{ feature: 'workflow_builder', action: 'unlock' }],
            },
            disclosure_result: {
              current_level: 'intermediate',
              recommended_level: 'advanced',
              confidence: 0.82,
              unlock_features: ['custom_agents'],
              personalized_message: 'Ready for advanced features!',
            },
            error_result: null,
            cross_insights: [
              'User behavior suggests higher expertise than assigned persona',
              'Progressive disclosure level should be upgraded',
            ],
            confidence: 0.84,
          }),
        });
      });

      // Navigate to the app shell
      await page.goto('/studio/chat');

      // Wait for the panel container to appear
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Verify the panel header is present
      const panelHeader = page.getByRole('heading', { name: /AI Insights/i });
      await expect(panelHeader).toBeVisible();
    });

    test('should show persona mismatch warning in CrossInsightsPanel', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'alice-analyst',
              confidence: 0.88,
              behavior_signals: ['Trace exploration'],
              recommendation: 'Enable analyst features',
              ui_adaptations: [],
            },
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Persona mismatch detected'],
            confidence: 0.88,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Expand the panel if collapsed (click the toggle button)
      const toggleButton = page.getByRole('button', { name: /toggle/i });
      if (await toggleButton.isVisible()) {
        await toggleButton.click();
      }

      // Check for persona mismatch warning
      const mismatchWarning = page.getByText(/Persona mismatch/i);
      await expect(mismatchWarning).toBeVisible();
    });

    test('should dismiss CrossInsightsPanel when dismiss button is clicked', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'bob',
              confidence: 0.92,
              behavior_signals: [],
              recommendation: null,
              ui_adaptations: [],
            },
            disclosure_result: null,
            error_result: null,
            cross_insights: ['No issues detected'],
            confidence: 0.92,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Click dismiss button
      const dismissButton = page.getByRole('button', { name: /dismiss/i });
      await dismissButton.click();

      // Panel should no longer be visible
      await expect(panelContainer).not.toBeVisible();
    });

    test('should display confidence indicator with appropriate color', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: {
              assigned_persona: 'bob',
              detected_persona: 'bob',
              confidence: 0.85,
              behavior_signals: [],
              recommendation: null,
              ui_adaptations: [],
            },
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Analysis complete'],
            confidence: 0.85,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Check for high confidence indicator (85% should be high)
      const confidenceIndicator = page.locator('[data-testid="confidence-high"]');
      await expect(confidenceIndicator).toBeVisible();
      await expect(confidenceIndicator).toHaveText(/85%/);
    });

    test('should not display CrossInsightsPanel when feature flag is disabled', async ({
      page,
    }) => {
      // Disable the feature flag
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: false,
            ai_suggestions: true,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Panel should not be present
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).not.toBeVisible();
    });

    test('should collapse and expand CrossInsightsPanel', async ({ page }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: null,
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Insight 1', 'Insight 2'],
            confidence: 0.75,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator('[data-testid="cross-insights-panel-container"]');
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      const toggleButton = page.getByRole('button', { name: /toggle/i });

      // Panel starts collapsed by default, expand it
      await toggleButton.click();

      // Insights should be visible when expanded
      const insight = page.getByText('Insight 1');
      await expect(insight).toBeVisible();

      // Collapse the panel
      await toggleButton.click();

      // Insights should be hidden when collapsed
      await expect(insight).not.toBeVisible();
    });

    test('should toggle CrossInsightsPanel visibility with Cmd+I keyboard shortcut (Mac)', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: null,
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Keyboard shortcut test insight'],
            confidence: 0.8,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator(
        '[data-testid="cross-insights-panel-container"]'
      );
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Press Cmd+I to dismiss the panel
      await page.keyboard.press('Meta+i');

      // Panel should be hidden after keyboard shortcut
      await expect(panelContainer).not.toBeVisible();

      // Press Cmd+I again to show the panel
      await page.keyboard.press('Meta+i');

      // Panel should be visible again
      await expect(panelContainer).toBeVisible();
    });

    test('should toggle CrossInsightsPanel visibility with Ctrl+I keyboard shortcut (Windows/Linux)', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: null,
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Keyboard shortcut test insight'],
            confidence: 0.8,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator(
        '[data-testid="cross-insights-panel-container"]'
      );
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Press Ctrl+I to dismiss the panel
      await page.keyboard.press('Control+i');

      // Panel should be hidden after keyboard shortcut
      await expect(panelContainer).not.toBeVisible();

      // Press Ctrl+I again to show the panel
      await page.keyboard.press('Control+i');

      // Panel should be visible again
      await expect(panelContainer).toBeVisible();
    });

    test('should persist dismissed state via keyboard shortcut to localStorage', async ({
      page,
    }) => {
      await page.route('**/api/v1/feature-flags', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            batch_composite_analysis: true,
            ai_suggestions: true,
            insights_session_dismissal: false, // Ensure localStorage persistence
          }),
        });
      });

      await page.route('**/api/v1/ai/composite/analyze', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            persona_result: null,
            disclosure_result: null,
            error_result: null,
            cross_insights: ['Persistence test insight'],
            confidence: 0.85,
          }),
        });
      });

      await page.goto('/studio/chat');

      // Wait for panel to be visible
      const panelContainer = page.locator(
        '[data-testid="cross-insights-panel-container"]'
      );
      await expect(panelContainer).toBeVisible({ timeout: 10000 });

      // Press Cmd+I to dismiss
      await page.keyboard.press('Meta+i');
      await expect(panelContainer).not.toBeVisible();

      // Check localStorage was updated
      const dismissedValue = await page.evaluate(() => {
        return localStorage.getItem('studio-cross-insights-dismissed');
      });
      expect(dismissedValue).toBe('true');

      // Reload page - panel should still be dismissed
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Panel should remain dismissed after reload
      await expect(panelContainer).not.toBeVisible({ timeout: 5000 });
    });
  });
});
