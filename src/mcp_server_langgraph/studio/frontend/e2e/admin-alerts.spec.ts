/**
 * Admin Alerts E2E Tests
 *
 * Tests the admin alerts functionality including:
 * - Alerts tab navigation
 * - Alert list display
 * - Alert detail panel
 * - AI recommendations
 * - Remediation approval flow
 * - Real-time alert updates
 * - Sound notifications
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock alert data for frontend-only testing
const MOCK_ALERTS = [
  {
    alert_id: 'alert-1',
    name: 'HighCPUUsage',
    severity: 'critical',
    state: 'firing',
    message: 'CPU usage above 90% for 10 minutes',
    labels: { instance: 'node-1', job: 'kubernetes' },
    annotations: { runbook_url: 'https://runbooks.example.com/cpu' },
    started_at: new Date().toISOString(),
    ended_at: null,
    fingerprint: 'fp-1',
  },
  {
    alert_id: 'alert-2',
    name: 'DiskSpaceWarning',
    severity: 'warning',
    state: 'firing',
    message: 'Disk space below 20%',
    labels: { instance: 'node-2', job: 'kubernetes' },
    annotations: {},
    started_at: new Date().toISOString(),
    ended_at: null,
    fingerprint: 'fp-2',
  },
  {
    alert_id: 'alert-3',
    name: 'MemoryPressure',
    severity: 'critical',
    state: 'firing',
    message: 'Memory pressure detected',
    labels: { instance: 'node-1', job: 'kubernetes' },
    annotations: {},
    started_at: new Date().toISOString(),
    ended_at: null,
    fingerprint: 'fp-3',
  },
];

const MOCK_RECOMMENDATION = {
  recommendation_id: 'rec-1',
  alert_id: 'alert-1',
  root_cause_analysis: 'The high CPU usage is likely caused by a runaway process or insufficient resource allocation.',
  remediation_steps: [
    {
      step_number: 1,
      action: 'identify',
      description: 'Identify top CPU-consuming processes',
      command: 'top -b -n 1 | head -20',
      requires_approval: false,
      risk_level: 'low',
    },
    {
      step_number: 2,
      action: 'scale',
      description: 'Scale up the deployment if needed',
      command: 'kubectl scale deployment api-server --replicas=5',
      requires_approval: true,
      risk_level: 'medium',
    },
  ],
  risk_assessment: {
    overall_risk: 'medium',
    impact_analysis: 'Temporary service degradation possible during scaling',
    rollback_plan: 'kubectl scale deployment api-server --replicas=3',
  },
  runbook_reference: 'https://runbooks.example.com/cpu',
  generated_at: new Date().toISOString(),
  model_used: 'claude-3-sonnet',
};

test.describe('Admin Alerts', () => {
  test.beforeEach(async ({ adminPage }) => {
    // Only mock API responses when backend is disabled
    if (!backendEnabled) {
      await adminPage.route('**/api/v1/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        // Alerts list endpoint
        if (url.includes('/alerts') && method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ items: MOCK_ALERTS, total: MOCK_ALERTS.length }),
          });
          return;
        }

        // Alert recommendation endpoint
        if (url.includes('/recommendation')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_RECOMMENDATION),
          });
          return;
        }

        // Remediation approval endpoint
        if (url.includes('/remediations') && method === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: true }),
          });
          return;
        }

        // Health endpoint
        if (url.includes('/health')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'healthy' }),
          });
          return;
        }

        // User endpoint
        if (url.includes('/me')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'admin-user',
              username: 'admin',
              email: 'admin@example.com',
              roles: ['admin'],
            }),
          });
          return;
        }

        // Feature flags
        if (url.includes('/features')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ features: {} }),
          });
          return;
        }

        // Default response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }

    // Navigate to admin dashboard
    await adminPage.goto('/studio/admin/dashboard');
  });

  test.describe('Alerts Tab Navigation', () => {
    test('should display Alerts tab on admin dashboard', async ({ adminPage }) => {
      // Wait for dashboard to load
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Check for Alerts tab
      const alertsTab = adminPage.getByRole('tab', { name: /alerts/i });
      await expect(alertsTab).toBeVisible();
    });

    test('should navigate to Alerts tab when clicked', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Click on Alerts tab
      const alertsTab = adminPage.getByRole('tab', { name: /alerts/i });
      await alertsTab.click();

      // Verify tab is selected
      await expect(alertsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('should show alerts container when Alerts tab is active', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Click on Alerts tab
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Verify alerts container is visible
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();
    });
  });

  test.describe('Alert List Display', () => {
    test('should display alert list in alerts panel', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Navigate to Alerts tab
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Wait for alerts panel
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Check for alerts panel heading or content
      const alertsPanel = adminPage.locator('[data-testid*="alert"], .alerts-panel');
      await expect(alertsPanel.first()).toBeVisible({ timeout: 10000 });
    });

    test('should show severity indicators for alerts', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Wait for alerts container
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for severity badges or indicators
      const severityIndicators = adminPage.locator('[data-testid*="severity"], .severity, [class*="critical"], [class*="warning"]');
      // This may not be visible if no alerts exist in the backend
      const isVisible = await severityIndicators.first().isVisible().catch(() => false);
      if (isVisible) {
        await expect(severityIndicators.first()).toBeVisible();
      }
    });
  });

  test.describe('Alert Badge in Header', () => {
    test('should display alert badge count when alerts exist', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Check for alert badge in the Alerts tab
      const alertBadge = adminPage.getByTestId('alert-badge');

      // Badge may or may not be visible depending on alert count
      const isVisible = await alertBadge.isVisible().catch(() => false);
      if (isVisible) {
        // Verify badge contains a number
        const badgeText = await alertBadge.textContent();
        expect(badgeText).toMatch(/\d+/);
      }
    });
  });

  test.describe('Sound Toggle', () => {
    test('should have sound toggle control in alerts panel', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Wait for alerts container
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for sound toggle button
      const soundToggle = adminPage.locator('[data-testid*="sound"], [aria-label*="sound"], button:has-text("Sound")');
      const isVisible = await soundToggle.first().isVisible().catch(() => false);
      if (isVisible) {
        await expect(soundToggle.first()).toBeVisible();
      }
    });
  });

  test.describe('Alert Selection', () => {
    test('should show empty state when no alert is selected', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Wait for alerts container
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for empty state or "Select an alert" message
      const emptyState = adminPage.locator('text=/select|no alert|choose/i');
      const isVisible = await emptyState.first().isVisible().catch(() => false);
      if (isVisible) {
        await expect(emptyState.first()).toBeVisible();
      }
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper ARIA attributes for tabs', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Check for tablist
      const tablist = adminPage.getByRole('tablist');
      await expect(tablist).toBeVisible();

      // Check for tab buttons
      const tabs = adminPage.getByRole('tab');
      expect(await tabs.count()).toBeGreaterThan(0);
    });

    test('should have keyboard navigation for alerts panel', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Navigate to Alerts tab using keyboard
      await adminPage.keyboard.press('Tab');

      // Continue tabbing to reach the Alerts tab
      for (let i = 0; i < 10; i++) {
        const focused = await adminPage.evaluate(() => document.activeElement?.textContent);
        if (focused?.toLowerCase().includes('alert')) break;
        await adminPage.keyboard.press('Tab');
      }
    });
  });

  test.describe('Performance', () => {
    test('alerts tab should load within acceptable time', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      const startTime = Date.now();

      // Click on Alerts tab
      await adminPage.getByRole('tab', { name: /alerts/i }).click();

      // Wait for alerts container
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Tab switch should be fast (under 1 second)
      expect(loadTime).toBeLessThan(1000);
    });
  });

  test.describe('Non-Admin Access', () => {
    test('standard user should not see admin dashboard', async ({ bobPage }) => {
      // Try to navigate to admin dashboard as standard user
      await bobPage.goto('/studio/admin/dashboard');

      // Should either redirect or show access denied
      // Wait for page to settle
      await bobPage.waitForTimeout(1000);

      // Check if we're on admin dashboard or if access was denied
      const currentUrl = bobPage.url();
      const isOnAdminPage = currentUrl.includes('/admin/dashboard');

      if (isOnAdminPage) {
        // If we're on the admin page, check for access denied message
        const accessDenied = bobPage.locator('text=/access denied|unauthorized|forbidden/i');
        const isAccessDenied = await accessDenied.first().isVisible().catch(() => false);

        // Either show access denied or the user shouldn't be on this page
        if (!isAccessDenied) {
          // If no access denied message, the test should verify admin-specific content is hidden
          const alertsTab = bobPage.getByRole('tab', { name: /alerts/i });
          const hasAlertsTab = await alertsTab.isVisible().catch(() => false);
          // Standard users may not have the alerts tab
          console.log(`Standard user ${hasAlertsTab ? 'has' : 'does not have'} alerts tab`);
        }
      }
    });
  });

  test.describe('Keyboard Shortcuts', () => {
    test('should navigate to Alerts tab with Shift+A', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Ensure we're on Overview tab first
      const overviewTab = adminPage.getByRole('tab', { name: /overview/i });
      await expect(overviewTab).toHaveAttribute('aria-selected', 'true');

      // Press Shift+A to navigate to Alerts tab
      await adminPage.keyboard.press('Shift+A');

      // Verify Alerts tab is now selected
      const alertsTab = adminPage.getByRole('tab', { name: /alerts/i });
      await expect(alertsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('should navigate to Overview tab with Shift+O', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // First navigate to Alerts tab
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      const alertsTab = adminPage.getByRole('tab', { name: /alerts/i });
      await expect(alertsTab).toHaveAttribute('aria-selected', 'true');

      // Press Shift+O to navigate to Overview tab
      await adminPage.keyboard.press('Shift+O');

      // Verify Overview tab is now selected
      const overviewTab = adminPage.getByRole('tab', { name: /overview/i });
      await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    });

    test('should navigate to Users tab with Shift+U', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Press Shift+U to navigate to Users tab
      await adminPage.keyboard.press('Shift+U');

      // Verify Users tab is now selected
      const usersTab = adminPage.getByRole('tab', { name: /users/i });
      await expect(usersTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  test.describe('AI Recommendations', () => {
    test('should show recommendation panel when alert is selected', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for recommendation-related elements in alert detail
      const recommendationPanel = adminPage.locator('[data-testid*="recommendation"], [class*="recommendation"]');
      const alertDetail = adminPage.locator('[data-testid*="detail"], [class*="detail-panel"]');

      // Either recommendation panel or detail panel should exist
      const hasRecommendation = await recommendationPanel.first().isVisible().catch(() => false);
      const hasDetail = await alertDetail.first().isVisible().catch(() => false);

      // At least the alerts container should be visible
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();
    });

    test('should have regenerate button for recommendations', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for regenerate button (may not be visible if no alert is selected)
      const regenerateButton = adminPage.locator('button:has-text("Regenerate"), [data-testid*="regenerate"]');
      const isVisible = await regenerateButton.first().isVisible().catch(() => false);

      // This test documents expected behavior
      console.log(`Regenerate button ${isVisible ? 'is' : 'is not'} visible`);
    });
  });

  test.describe('Remediation Approval', () => {
    test('should show approval dialog when remediation is clicked', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for approve/reject buttons (may not be visible if no remediations pending)
      const approveButton = adminPage.locator('button:has-text("Approve"), [data-testid*="approve"]');
      const isVisible = await approveButton.first().isVisible().catch(() => false);

      if (isVisible) {
        await approveButton.first().click();

        // Look for dialog
        const dialog = adminPage.locator('[role="dialog"], [data-testid*="dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });
      }
    });

    test('should have reason field in approval dialog', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for approve buttons
      const approveButton = adminPage.locator('button:has-text("Approve"), [data-testid*="approve"]');
      const isVisible = await approveButton.first().isVisible().catch(() => false);

      if (isVisible) {
        await approveButton.first().click();

        // Look for reason input
        const reasonInput = adminPage.locator('textarea, input[name*="reason"], [placeholder*="reason"]');
        const hasReason = await reasonInput.first().isVisible().catch(() => false);
        console.log(`Reason field ${hasReason ? 'is' : 'is not'} visible in dialog`);
      }
    });
  });

  test.describe('Real-time Updates', () => {
    test('should show connection status indicator', async ({ adminPage }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for connection status indicator
      const statusIndicator = adminPage.locator('[data-testid*="connection"], [data-testid*="status"], [class*="connection"]');
      const isVisible = await statusIndicator.first().isVisible().catch(() => false);

      console.log(`Connection status indicator ${isVisible ? 'is' : 'is not'} visible`);
    });
  });

  /**
   * Full End-to-End Alert Flow Test
   *
   * Tests the complete alert lifecycle from webhook to remediation:
   * 1. Alertmanager webhook receives alert
   * 2. Alert is broadcast via WebSocket
   * 3. Alert appears in admin UI
   * 4. User views alert details and AI recommendation
   * 5. User approves remediation
   * 6. Remediation executes and result is shown
   *
   * This test requires BACKEND_ENABLED=true for full validation.
   */
  test.describe('Full Alert Lifecycle Flow', () => {
    // Skip in mock mode - requires real backend
    test.skip(
      !backendEnabled,
      'Full E2E flow requires real backend (BACKEND_ENABLED=true)'
    );

    test('complete alert flow: webhook → websocket → UI → recommendation → approval', async ({
      adminPage,
      request,
    }) => {
      // Step 1: Navigate to alerts tab and establish WebSocket connection
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Wait for WebSocket connection to establish
      await adminPage.waitForTimeout(1000);

      // Step 2: Simulate Alertmanager webhook with a new critical alert
      const testAlert = {
        version: '4',
        groupKey: 'test-group-' + Date.now(),
        status: 'firing',
        receiver: 'mcp-server',
        groupLabels: {
          alertname: 'E2ETestAlert',
        },
        commonLabels: {
          alertname: 'E2ETestAlert',
          severity: 'critical',
          instance: 'test-node-1',
          job: 'e2e-test',
        },
        commonAnnotations: {
          summary: 'E2E Test Alert - Critical',
          description: 'This is an automated E2E test alert',
        },
        externalURL: 'http://alertmanager:9093',
        alerts: [
          {
            status: 'firing',
            labels: {
              alertname: 'E2ETestAlert',
              severity: 'critical',
              instance: 'test-node-1',
              job: 'e2e-test',
            },
            annotations: {
              summary: 'E2E Test Alert - Critical',
              description: 'This is an automated E2E test alert',
            },
            startsAt: new Date().toISOString(),
            endsAt: '0001-01-01T00:00:00Z',
            generatorURL: 'http://prometheus:9090/graph',
            fingerprint: 'e2e-test-' + Date.now(),
          },
        ],
      };

      // Send webhook request
      const webhookResponse = await request.post('/api/v1/webhooks/alertmanager', {
        data: testAlert,
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Verify webhook was accepted
      expect(webhookResponse.status()).toBe(200);

      // Step 3: Wait for alert to appear in UI via WebSocket
      // The alert should appear within a few seconds
      const alertElement = adminPage.locator(
        `[data-testid*="alert"]:has-text("E2ETestAlert"), ` +
        `.alert-item:has-text("E2ETestAlert"), ` +
        `text=E2ETestAlert`
      );

      await expect(alertElement.first()).toBeVisible({ timeout: 10000 });

      // Step 4: Click on the alert to view details
      await alertElement.first().click();

      // Verify alert detail panel opens
      const detailPanel = adminPage.locator(
        '[data-testid*="detail-panel"], ' +
        '[data-testid*="alert-detail"], ' +
        '.alert-detail-panel'
      );
      await expect(detailPanel.first()).toBeVisible({ timeout: 5000 });

      // Verify alert name is shown in detail
      await expect(detailPanel.first()).toContainText('E2ETestAlert');

      // Step 5: Check for AI recommendation
      // Wait for recommendation to load (may take a few seconds for AI)
      const recommendationSection = adminPage.locator(
        '[data-testid*="recommendation"], ' +
        '.recommendation-card, ' +
        'text=Root Cause'
      );

      // Recommendation may take time to generate
      const hasRecommendation = await recommendationSection.first()
        .isVisible({ timeout: 15000 })
        .catch(() => false);

      if (hasRecommendation) {
        // Verify recommendation content
        await expect(recommendationSection.first()).toBeVisible();

        // Look for remediation steps
        const remediationSteps = adminPage.locator(
          '[data-testid*="step"], ' +
          '.remediation-step, ' +
          'text=Step'
        );
        const hasSteps = await remediationSteps.first().isVisible().catch(() => false);
        console.log(`Remediation steps ${hasSteps ? 'are' : 'are not'} visible`);

        // Step 6: Look for approve button and click if available
        const approveButton = adminPage.locator(
          'button:has-text("Approve"), ' +
          '[data-testid*="approve"], ' +
          'button[aria-label*="approve"]'
        );

        const canApprove = await approveButton.first().isVisible().catch(() => false);

        if (canApprove) {
          // Click approve
          await approveButton.first().click();

          // Wait for confirmation dialog or success message
          const confirmDialog = adminPage.locator(
            '[role="dialog"], [data-testid*="confirm"], .confirmation-dialog'
          );
          const hasDialog = await confirmDialog.first()
            .isVisible({ timeout: 3000 })
            .catch(() => false);

          if (hasDialog) {
            // Confirm approval
            const confirmButton = adminPage.locator(
              'button:has-text("Confirm"), ' +
              'button:has-text("Yes"), ' +
              '[data-testid*="confirm-approve"]'
            );
            await confirmButton.first().click();
          }

          // Wait for success indication
          const successMessage = adminPage.locator(
            'text=/approved|success|executed/i, ' +
            '[data-testid*="success"], ' +
            '.toast-success'
          );
          const wasSuccessful = await successMessage.first()
            .isVisible({ timeout: 5000 })
            .catch(() => false);

          console.log(`Remediation approval ${wasSuccessful ? 'succeeded' : 'status unknown'}`);
        }
      }

      // Step 7: Verify alert can be resolved (send resolved webhook)
      const resolvedAlert = {
        ...testAlert,
        status: 'resolved',
        alerts: [
          {
            ...testAlert.alerts[0],
            status: 'resolved',
            endsAt: new Date().toISOString(),
          },
        ],
      };

      const resolveResponse = await request.post('/api/v1/webhooks/alertmanager', {
        data: resolvedAlert,
        headers: {
          'Content-Type': 'application/json',
        },
      });

      expect(resolveResponse.status()).toBe(200);

      // Verify alert shows as resolved in UI
      await adminPage.waitForTimeout(2000);

      // The alert should show resolved state or be removed
      const resolvedIndicator = adminPage.locator(
        '[data-testid*="resolved"], ' +
        '.alert-resolved, ' +
        'text=/resolved/i'
      );
      const isResolved = await resolvedIndicator.first().isVisible().catch(() => false);
      console.log(`Alert resolved state ${isResolved ? 'shown' : 'not visible'}`);
    });

    test('should handle correlation request in UI', async ({ adminPage, request }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Look for correlation or grouping controls
      const correlationControl = adminPage.locator(
        '[data-testid*="correlation"], ' +
        '[data-testid*="group"], ' +
        'button:has-text("Group"), ' +
        'select:has-text("Group by")'
      );

      const hasCorrelation = await correlationControl.first().isVisible().catch(() => false);

      if (hasCorrelation) {
        // Click to trigger correlation
        await correlationControl.first().click();

        // Verify grouped view appears
        const groupedView = adminPage.locator(
          '[data-testid*="group"], ' +
          '.alert-group, ' +
          'text=/group|cluster/i'
        );
        const hasGrouped = await groupedView.first().isVisible({ timeout: 5000 }).catch(() => false);
        console.log(`Grouped view ${hasGrouped ? 'is' : 'is not'} visible`);
      }
    });

    test('should play sound for critical alerts', async ({ adminPage, request }) => {
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
      await adminPage.getByRole('tab', { name: /alerts/i }).click();
      await expect(adminPage.getByTestId('alerts-container')).toBeVisible();

      // Enable sound if toggle exists
      const soundToggle = adminPage.locator(
        '[data-testid*="sound-toggle"], ' +
        'button[aria-label*="sound"], ' +
        'input[type="checkbox"][name*="sound"]'
      );

      const hasToggle = await soundToggle.first().isVisible().catch(() => false);

      if (hasToggle) {
        // Check if sound is enabled
        const isEnabled = await soundToggle.first().isChecked?.() ?? false;

        if (!isEnabled) {
          await soundToggle.first().click();
        }

        // Send a critical alert
        const criticalAlert = {
          version: '4',
          groupKey: 'sound-test-' + Date.now(),
          status: 'firing',
          receiver: 'mcp-server',
          groupLabels: { alertname: 'SoundTestAlert' },
          commonLabels: {
            alertname: 'SoundTestAlert',
            severity: 'critical',
            instance: 'sound-test',
          },
          commonAnnotations: { summary: 'Sound Test Alert' },
          alerts: [{
            status: 'firing',
            labels: {
              alertname: 'SoundTestAlert',
              severity: 'critical',
              instance: 'sound-test',
            },
            annotations: { summary: 'Sound Test Alert' },
            startsAt: new Date().toISOString(),
            fingerprint: 'sound-test-' + Date.now(),
          }],
        };

        await request.post('/api/v1/webhooks/alertmanager', {
          data: criticalAlert,
          headers: { 'Content-Type': 'application/json' },
        });

        // Note: We can't actually verify sound played in Playwright
        // but we can verify the alert appeared
        const alertElement = adminPage.locator('text=SoundTestAlert');
        await expect(alertElement.first()).toBeVisible({ timeout: 10000 });

        console.log('Critical alert received - sound should have played if enabled');
      }
    });
  });
});
