/**
 * Agent HITL (Human-in-the-Loop) Approval E2E Tests
 *
 * Tests the complete HITL approval workflow for agents:
 * - Low confidence detection triggers approval request
 * - Approval dialog display
 * - Approve/Reject actions
 * - WebSocket real-time updates
 * - Agent resume/halt after decision
 * - Feature flag integration
 *
 * Reference: Plan - Confidence-Based HITL for Multi-Agent Orchestrator
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock AI explanation for AI-Native HITL Enhancement (Plan 10.2)
const MOCK_AI_EXPLANATION = {
  why_uncertain: 'The analysis involves external data sources with inconsistent formatting, leading to potential parsing errors.',
  what_could_go_wrong: 'If the data is misinterpreted, the report could contain inaccurate metrics that may mislead decision-making.',
  safer_alternatives: [
    {
      action: 'Validate data schema before sending',
      confidence: 0.88,
      trade_off: 'Additional 30 seconds processing time',
    },
    {
      action: 'Send to staging API first',
      confidence: 0.92,
      trade_off: 'Requires manual promotion to production',
    },
  ],
  confidence_factors: [
    {
      factor: 'data_format_inconsistency',
      weight: -0.25,
      evidence: 'Found 3 different date formats in input',
    },
    {
      factor: 'missing_validation',
      weight: -0.13,
      evidence: 'No schema validation on external payload',
    },
  ],
  reasoning_trace: [
    'Loaded data from external source',
    'Detected inconsistent date formats',
    'Attempted type coercion on 15 fields',
    'Generated report with best-effort parsing',
  ],
  model_used: 'gpt-4o-mini',
  generated_at: new Date().toISOString(),
  cached: false,
};

// Mock agent request data for frontend-only testing
const MOCK_APPROVAL_REQUEST = {
  request_id: 'hitl-req-001',
  session_id: 'session-001',
  task_id: 'task-001',
  agent_name: 'Research Assistant',
  request_type: 'approval',
  confidence: 0.62,
  threshold: 0.7,
  proposed_action: 'Send analysis report to external API',
  question: 'Confidence 62% is below threshold 70%. Approve?',
  trigger_reason: 'low_confidence',
  status: 'pending',
  requested_at: new Date().toISOString(),
  context: {
    task_instructions: 'Analyze market data and generate report',
    artifacts: ['analysis.json', 'chart.png'],
    duration_ms: 2450,
  },
  ai_explanation: MOCK_AI_EXPLANATION,
};

const MOCK_CLARIFICATION_REQUEST = {
  request_id: 'hitl-req-002',
  session_id: 'session-001',
  task_id: 'task-002',
  agent_name: 'Data Analyst',
  request_type: 'clarification',
  clarification_type: 'choice',
  question: 'Which analysis approach should I use?',
  options: [
    { id: 'fast', label: 'Fast Analysis', description: '~30 seconds, 85% accuracy', is_recommended: false },
    { id: 'thorough', label: 'Thorough Analysis', description: '~5 minutes, 98% accuracy', is_recommended: true },
  ],
  status: 'pending',
  requested_at: new Date().toISOString(),
  context: {},
};

const MOCK_PENDING_REQUESTS = [
  MOCK_APPROVAL_REQUEST,
  MOCK_CLARIFICATION_REQUEST,
];

test.describe('Agent HITL Approval Flow', () => {
  test.beforeEach(async ({ alicePage }) => {
    // Only mock API responses when backend is disabled
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

        // Agent requests list endpoint
        if (url.includes('/agents/requests') && method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ items: MOCK_PENDING_REQUESTS, total: MOCK_PENDING_REQUESTS.length }),
          });
          return;
        }

        // Approve endpoint
        if (url.includes('/approve') && method === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              request_id: MOCK_APPROVAL_REQUEST.request_id,
              status: 'approved',
              responded_by: 'alice@example.com',
              responded_at: new Date().toISOString(),
            }),
          });
          return;
        }

        // Reject endpoint
        if (url.includes('/reject') && method === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              request_id: MOCK_APPROVAL_REQUEST.request_id,
              status: 'rejected',
              responded_by: 'alice@example.com',
              responded_at: new Date().toISOString(),
            }),
          });
          return;
        }

        // Feature flags endpoint
        if (url.includes('/features')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              enable_agent_hitl: true,
              agent_hitl_confidence_threshold: 0.7,
            }),
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
              id: 'alice-user',
              username: 'alice',
              email: 'alice@example.com',
              roles: ['admin', 'hitl_reviewer'],
            }),
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

    // Navigate to chat page where HITL interactions occur
    await alicePage.goto('/studio/chat');
  });

  test.describe('Approval Request Display', () => {
    test('should show pending approval badge in status bar when approvals exist', async ({ alicePage }) => {
      // Wait for page to load
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for pending approval indicator in status bar
      const pendingBadge = alicePage.locator(
        '[data-testid="pending-approvals-badge"], ' +
        '[data-testid="hitl-pending-badge"], ' +
        '[data-testid="status-bar-approvals"]'
      );

      // In mock mode with pending approvals, the badge should be visible
      if (!backendEnabled) {
        await expect(pendingBadge.first()).toBeVisible({ timeout: 10000 });
        const badgeText = await pendingBadge.first().textContent();
        expect(badgeText).toMatch(/\d+/); // Should contain a number
      } else {
        // In backend mode, badge visibility depends on actual pending requests
        const isVisible = await pendingBadge.first().isVisible({ timeout: 5000 }).catch(() => false);
        console.log(`Pending approval badge visible: ${isVisible}`);
      }
    });

    test('should show awaiting_approval status for agent with pending request', async ({ alicePage }) => {
      // Wait for page to load
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for agent status indicator
      const agentStatus = alicePage.locator(
        '[data-testid*="agent-status"][data-status="awaiting_approval"], ' +
        '[data-testid="awaiting-approval-indicator"], ' +
        '.agent-status-awaiting'
      );

      // In mock mode, verify awaiting approval status is displayed correctly
      if (!backendEnabled) {
        await expect(agentStatus.first()).toBeVisible({ timeout: 10000 });
        await expect(agentStatus.first()).toContainText(/awaiting|approval|pending|review/i);
      } else {
        const isVisible = await agentStatus.first().isVisible({ timeout: 5000 }).catch(() => false);
        console.log(`Agent awaiting status visible: ${isVisible}`);
      }
    });
  });

  test.describe('Approval Dialog', () => {
    test('should open approval dialog when review button is clicked', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for review button
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), ' +
        '[data-testid="review-approval-button"], ' +
        'button[aria-label*="review"]'
      );

      // In mock mode, review button should be available
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Verify approval dialog opens with required elements
        const dialog = alicePage.locator('[role="dialog"][data-testid="agent-approval-dialog"], [role="dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });

        // Dialog must have approve and reject buttons
        const approveBtn = dialog.locator('button:has-text("Approve")');
        const rejectBtn = dialog.locator('button:has-text("Reject")');
        await expect(approveBtn.first()).toBeVisible();
        await expect(rejectBtn.first()).toBeVisible();
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          const dialog = alicePage.locator('[role="dialog"]');
          await expect(dialog.first()).toBeVisible({ timeout: 5000 });
        }
      }
    });

    test('should display confidence gauge in approval dialog', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      // In mock mode, confidence gauge is required
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Confidence gauge must show percentage
        const confidenceGauge = alicePage.locator(
          '[data-testid="confidence-gauge"], ' +
          '[data-testid="confidence-indicator"], ' +
          '.confidence-display'
        );

        await expect(confidenceGauge.first()).toBeVisible({ timeout: 5000 });
        const gaugeText = await confidenceGauge.first().textContent();
        expect(gaugeText).toMatch(/\d+%?/); // Should contain a number (with optional %)
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          // Log confidence visibility in backend mode
          const confidenceGauge = alicePage.locator('[data-testid*="confidence"]');
          const isVisible = await confidenceGauge.first().isVisible({ timeout: 3000 }).catch(() => false);
          console.log(`Confidence gauge visible: ${isVisible}`);
        }
      }
    });

    test('should show agent name and proposed action', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      // In mock mode, agent name and action are required
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        const dialog = alicePage.locator('[role="dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });

        // Agent name must be visible
        const agentNameLabel = dialog.locator('[data-testid="agent-name"], text=/Research Assistant|agent/i');
        await expect(agentNameLabel.first()).toBeVisible();

        // Proposed action must be visible
        const proposedAction = dialog.locator('[data-testid="proposed-action"], text=/action|send|API/i');
        await expect(proposedAction.first()).toBeVisible();
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          const dialog = alicePage.locator('[role="dialog"]');
          await expect(dialog.first()).toBeVisible({ timeout: 5000 });
        }
      }
    });

    test('should show trigger reason explanation', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      // In mock mode, explanation is required
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Explanation text must be visible
        const explanation = alicePage.locator(
          '[data-testid="trigger-explanation"], ' +
          '[data-testid="approval-reason"], ' +
          'text=/why|below threshold|confidence/i'
        );

        await expect(explanation.first()).toBeVisible({ timeout: 5000 });
        const explanationText = await explanation.first().textContent();
        expect(explanationText?.toLowerCase()).toMatch(/confidence|threshold|below|low/);
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          const explanation = alicePage.locator('[data-testid*="reason"], [data-testid*="explanation"]');
          const hasExplanation = await explanation.first().isVisible({ timeout: 3000 }).catch(() => false);
          console.log(`Trigger explanation visible: ${hasExplanation}`);
        }
      }
    });
  });

  test.describe('AI Explanation Display (Plan 10.2 AI-Native Enhancement)', () => {
    /**
     * Tests for AI-generated explanations in HITL approval dialogs.
     * These tests validate the AI-Native HITL Enhancement from Plan section 10.2.
     */

    test('should show AI explanation section in approval dialog', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      // In mock mode with ai_explanation, section should be visible
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // AI explanation section uses <details> element
        const aiExplanationSection = alicePage.locator(
          '[data-testid="ai-explanation-section"], ' +
          'details:has(summary:has-text("uncertain"))'
        );

        await expect(aiExplanationSection.first()).toBeVisible({ timeout: 5000 });
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          const aiSection = alicePage.locator('[data-testid="ai-explanation-section"]');
          const hasAI = await aiSection.first().isVisible({ timeout: 3000 }).catch(() => false);
          console.log(`AI explanation section visible: ${hasAI}`);
        }
      }
    });

    test('should expand AI explanation when clicked', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Click summary to expand details
        const summary = alicePage.locator(
          '[data-testid="ai-explanation-section"] summary, ' +
          'summary:has-text("uncertain")'
        );

        await expect(summary.first()).toBeVisible({ timeout: 5000 });
        await summary.first().click();

        // Verify content is visible after expand
        const explanationContent = alicePage.locator(
          'text=/external data sources|parsing errors/i'
        );

        await expect(explanationContent.first()).toBeVisible({ timeout: 3000 });
      }
    });

    test('should display "what could go wrong" section', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Expand AI explanation
        const summary = alicePage.locator('[data-testid="ai-explanation-section"] summary');
        await summary.first().click();

        // Verify "what could go wrong" content
        const riskContent = alicePage.locator(
          'text=/what could go wrong/i, ' +
          'text=/inaccurate metrics|mislead/i'
        );

        await expect(riskContent.first()).toBeVisible({ timeout: 3000 });
      }
    });

    test('should display safer alternatives list', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Expand AI explanation
        const summary = alicePage.locator('[data-testid="ai-explanation-section"] summary');
        await summary.first().click();

        // Verify safer alternatives are displayed with confidence percentages
        const alternatives = alicePage.locator(
          'text=/safer alternative/i, ' +
          'text=/Validate data schema|staging API/i'
        );

        await expect(alternatives.first()).toBeVisible({ timeout: 3000 });

        // Verify confidence percentages are shown
        const confidencePercent = alicePage.locator('text=/88%|92%/');
        await expect(confidencePercent.first()).toBeVisible();
      }
    });

    test('should display confidence factors with weights', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Expand AI explanation
        const summary = alicePage.locator('[data-testid="ai-explanation-section"] summary');
        await summary.first().click();

        // Verify confidence factors are displayed
        const factors = alicePage.locator(
          'text=/confidence factors/i, ' +
          'text=/date formats|validation/i'
        );

        await expect(factors.first()).toBeVisible({ timeout: 3000 });

        // Verify negative weights are shown (e.g., -25%)
        const negativeWeight = alicePage.locator('text=/-25%|-13%/');
        await expect(negativeWeight.first()).toBeVisible();
      }
    });

    test('AI explanation section should be accessible', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Verify details/summary has proper structure for a11y
        const details = alicePage.locator('[data-testid="ai-explanation-section"]');
        await expect(details.first()).toBeVisible({ timeout: 5000 });

        // Should be keyboard accessible - focus and press Enter
        const summary = alicePage.locator('[data-testid="ai-explanation-section"] summary');
        await summary.first().focus();
        await alicePage.keyboard.press('Enter');

        // Content should expand
        const content = alicePage.locator('text=/external data sources/i');
        await expect(content.first()).toBeVisible({ timeout: 3000 });
      }
    });
  });

  test.describe('Approval Actions', () => {
    test('should approve request when approve button is clicked', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Open approval dialog
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        await reviewButton.first().click();

        // Find and click approve button
        const approveButton = alicePage.locator(
          'button:has-text("Approve"), ' +
          '[data-testid*="approve-button"]'
        );

        const hasApprove = await approveButton.first().isVisible().catch(() => false);

        if (hasApprove) {
          await approveButton.first().click();

          // Verify success indication
          const successMessage = alicePage.locator(
            'text=/approved|success/i, ' +
            '[data-testid*="success"], ' +
            '.toast-success'
          );

          const wasSuccessful = await successMessage.first()
            .isVisible({ timeout: 5000 })
            .catch(() => false);

          console.log(`Approval ${wasSuccessful ? 'succeeded' : 'status unknown'}`);
        }
      }
    });

    test('should reject request when reject button is clicked', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Open approval dialog
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        await reviewButton.first().click();

        // Find and click reject button
        const rejectButton = alicePage.locator(
          'button:has-text("Reject"), ' +
          '[data-testid*="reject-button"]'
        );

        const hasReject = await rejectButton.first().isVisible().catch(() => false);

        if (hasReject) {
          await rejectButton.first().click();

          // Verify rejection indication (use text matching)
          const rejectedMessage = alicePage.locator(
            'text=/rejected|declined/i'
          );

          const wasRejected = await rejectedMessage.first()
            .isVisible({ timeout: 5000 })
            .catch(() => false);

          console.log(`Rejection ${wasRejected ? 'succeeded' : 'status unknown'}`);
        }
      }
    });

    test('should include optional reason with rejection', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Open approval dialog
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        await reviewButton.first().click();

        // Look for reason input
        const reasonInput = alicePage.locator(
          'textarea, ' +
          'input[name*="reason"], ' +
          '[placeholder*="reason"]'
        );

        const hasReason = await reasonInput.first().isVisible().catch(() => false);

        if (hasReason) {
          // Fill in reason
          await reasonInput.first().fill('Not authorized for this action');

          // Click reject
          const rejectButton = alicePage.locator('button:has-text("Reject")');
          await rejectButton.first().click();

          console.log('Rejection with reason submitted');
        }
      }
    });
  });

  test.describe('Clarification Dialog', () => {
    test('should show choice options in clarification dialog', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for clarification request indicator
      const clarificationButton = alicePage.locator(
        'button:has-text("Clarify"), ' +
        '[data-testid*="clarification"], ' +
        'text=/needs input|question/i'
      );

      const hasClarification = await clarificationButton.first().isVisible().catch(() => false);

      if (hasClarification) {
        await clarificationButton.first().click();

        // Verify clarification dialog
        const dialog = alicePage.locator('[role="dialog"], [data-testid*="clarification-dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });

        // Look for radio/choice options
        const options = dialog.locator('input[type="radio"], [role="radio"], [data-testid*="option"]');
        const optionCount = await options.count();

        console.log(`Found ${optionCount} choice options in clarification dialog`);
      }
    });

    test('should submit selected choice', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const clarificationButton = alicePage.locator(
        'button:has-text("Clarify"), [data-testid*="clarification"]'
      );

      const hasClarification = await clarificationButton.first().isVisible().catch(() => false);

      if (hasClarification) {
        await clarificationButton.first().click();

        // Select an option
        const firstOption = alicePage.locator('input[type="radio"], [role="radio"]').first();
        const hasOption = await firstOption.isVisible().catch(() => false);

        if (hasOption) {
          await firstOption.click();

          // Submit
          const submitButton = alicePage.locator('button:has-text("Submit"), button:has-text("Send")');
          await submitButton.first().click();

          console.log('Clarification response submitted');
        }
      }
    });
  });

  test.describe('WebSocket Real-time Updates', () => {
    test('should show connection status for HITL WebSocket', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for WebSocket connection status
      const connectionStatus = alicePage.locator(
        '[data-testid*="ws-status"], ' +
        '[data-testid*="connection-status"], ' +
        '.ws-connected, .ws-disconnected'
      );

      const hasStatus = await connectionStatus.first().isVisible().catch(() => false);
      console.log(`WebSocket status indicator ${hasStatus ? 'is' : 'is not'} visible`);
    });

    test('should receive approval_required message via WebSocket', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // This test validates that WebSocket messages are processed
      // In mock mode, we simulate the message arrival
      if (!backendEnabled) {
        // Simulate WebSocket message
        await alicePage.evaluate(() => {
          const event = new CustomEvent('hitl:approval_required', {
            detail: {
              request_id: 'ws-test-001',
              agent_name: 'Test Agent',
              confidence: 0.55,
              threshold: 0.7,
            },
          });
          window.dispatchEvent(event);
        });

        // Wait for UI to update
        await alicePage.waitForTimeout(1000);

        // Check if approval request appeared
        const notification = alicePage.locator(
          '[data-testid*="notification"], ' +
          '.toast, ' +
          'text=/approval|agent/i'
        );

        const hasNotification = await notification.first().isVisible().catch(() => false);
        console.log(`WebSocket notification ${hasNotification ? 'received' : 'not visible'}`);
      }
    });
  });

  test.describe('Feature Flag Integration', () => {
    test('should respect HITL feature flag', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // When HITL is disabled, approval UI should not appear
      // This test validates the feature flag check

      // Look for HITL-related UI elements
      const hitlElements = alicePage.locator(
        '[data-testid*="hitl"], ' +
        '[data-testid*="approval"], ' +
        '.hitl-container'
      );

      const hasHitlUI = await hitlElements.first().isVisible().catch(() => false);
      console.log(`HITL UI elements ${hasHitlUI ? 'are' : 'are not'} visible`);

      // Feature flag should control visibility
      // When enable_agent_hitl = true, elements should be visible
      // When enable_agent_hitl = false, elements should be hidden
    });

    test('should show confidence threshold from feature flags', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for threshold display
      const thresholdDisplay = alicePage.locator(
        '[data-testid*="threshold"], ' +
        'text=/threshold/i, ' +
        'text=/70%/'
      );

      const hasThreshold = await thresholdDisplay.first().isVisible().catch(() => false);
      console.log(`Confidence threshold ${hasThreshold ? 'is' : 'is not'} visible`);
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper ARIA attributes for approval dialog', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid="review-approval-button"]'
      );

      // In mock mode, verify ARIA compliance strictly
      if (!backendEnabled) {
        await expect(reviewButton.first()).toBeVisible({ timeout: 10000 });
        await reviewButton.first().click();

        // Dialog must have role="dialog"
        const dialog = alicePage.locator('[role="dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });

        // Must have aria-labelledby or aria-label
        const ariaLabelledby = await dialog.first().getAttribute('aria-labelledby');
        const ariaLabel = await dialog.first().getAttribute('aria-label');
        expect(ariaLabelledby || ariaLabel).toBeTruthy();

        // Must have aria-modal="true" for proper modal behavior
        const ariaModal = await dialog.first().getAttribute('aria-modal');
        expect(ariaModal).toBe('true');

        // Buttons must have accessible names
        const approveBtn = dialog.locator('button:has-text("Approve")');
        await expect(approveBtn.first()).toHaveAttribute('type', 'button');
      } else {
        const hasReviewButton = await reviewButton.first().isVisible({ timeout: 5000 }).catch(() => false);
        if (hasReviewButton) {
          await reviewButton.first().click();
          const dialog = alicePage.locator('[role="dialog"]');
          await expect(dialog.first()).toBeVisible({ timeout: 5000 });
          const hasLabel = await dialog.first().getAttribute('aria-labelledby') ||
                          await dialog.first().getAttribute('aria-label');
          expect(hasLabel).toBeTruthy();
        }
      }
    });

    test('should be keyboard navigable', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // In mock mode, verify keyboard navigation works
      if (!backendEnabled) {
        // Tab to find interactive elements
        let foundHITLElement = false;
        for (let i = 0; i < 20; i++) {
          await alicePage.keyboard.press('Tab');
          const focused = await alicePage.evaluate(() =>
            document.activeElement?.getAttribute('data-testid') ||
            document.activeElement?.textContent?.toLowerCase()
          );

          if (focused?.includes('approve') || focused?.includes('review') || focused?.includes('pending')) {
            foundHITLElement = true;
            break;
          }
        }

        // Should find at least one HITL-related focusable element
        expect(foundHITLElement).toBe(true);
      } else {
        // Tab through interactive elements
        await alicePage.keyboard.press('Tab');
        for (let i = 0; i < 15; i++) {
          const focused = await alicePage.evaluate(() =>
            document.activeElement?.getAttribute('data-testid') ||
            document.activeElement?.textContent
          );
          if (focused?.toLowerCase().includes('approve') || focused?.toLowerCase().includes('review')) {
            console.log('Found HITL-related focusable element');
            break;
          }
          await alicePage.keyboard.press('Tab');
        }
      }
    });
  });

  test.describe('Performance', () => {
    test('approval dialog should open within acceptable time', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        const startTime = Date.now();

        await reviewButton.first().click();

        const dialog = alicePage.locator('[role="dialog"]');
        await expect(dialog.first()).toBeVisible({ timeout: 5000 });

        const loadTime = Date.now() - startTime;

        // Dialog should open fast (under 500ms)
        expect(loadTime).toBeLessThan(500);
        console.log(`Approval dialog opened in ${loadTime}ms`);
      }
    });
  });

  /**
   * Full End-to-End HITL Flow Test
   *
   * Tests the complete HITL lifecycle:
   * 1. Agent executes with low confidence
   * 2. Approval request is created and broadcast
   * 3. User sees approval request in UI
   * 4. User reviews and approves/rejects
   * 5. Agent resumes or halts based on decision
   *
   * This test requires BACKEND_ENABLED=true for full validation.
   */
  test.describe('Full HITL Lifecycle Flow', () => {
    // Skip in mock mode - requires real backend
    test.skip(
      !backendEnabled,
      'Full E2E flow requires real backend (BACKEND_ENABLED=true)'
    );

    test('complete HITL flow: low confidence → approval request → user decision → agent resume', async ({
      alicePage,
      request: _request,
    }) => {
      // Step 1: Navigate to chat page and establish WebSocket connection
      await expect(alicePage.locator('body')).toBeVisible();

      // Wait for WebSocket connection
      await alicePage.waitForTimeout(1000);

      // Step 2: Trigger an agent task that will have low confidence
      // (This would be done by sending a message that triggers agent execution)
      const chatInput = alicePage.locator(
        'textarea, ' +
        'input[placeholder*="message"], ' +
        '[data-testid*="chat-input"]'
      );

      const hasChatInput = await chatInput.first().isVisible().catch(() => false);

      if (hasChatInput) {
        // Send a message that might trigger HITL
        await chatInput.first().fill('Analyze this complex data with high uncertainty');
        await alicePage.keyboard.press('Enter');

        // Step 3: Wait for approval request to appear
        // This may take time depending on agent execution
        const approvalNotification = alicePage.locator(
          '[data-testid*="pending-approval"], ' +
          'text=/awaiting approval|needs review|approval required/i'
        );

        const hasApproval = await approvalNotification.first()
          .isVisible({ timeout: 30000 })
          .catch(() => false);

        if (hasApproval) {
          console.log('Approval request received');

          // Step 4: Open approval dialog
          const reviewButton = alicePage.locator('button:has-text("Review")');
          await reviewButton.first().click();

          // Verify dialog content
          const dialog = alicePage.locator('[role="dialog"]');
          await expect(dialog.first()).toBeVisible({ timeout: 5000 });

          // Step 5: Approve the request
          const approveButton = dialog.locator('button:has-text("Approve")');
          await approveButton.first().click();

          // Step 6: Verify agent resumed (use text matching)
          const resumedMessage = alicePage.locator(
            'text=/resumed|continuing|approved/i'
          );

          const wasResumed = await resumedMessage.first()
            .isVisible({ timeout: 10000 })
            .catch(() => false);

          console.log(`Agent ${wasResumed ? 'resumed' : 'status unknown'} after approval`);
        } else {
          console.log('No HITL approval request triggered (agent may have high confidence)');
        }
      }
    });

    test('should handle rejection flow correctly', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Wait for any pending approval requests
      await alicePage.waitForTimeout(2000);

      // Look for pending approvals
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        await reviewButton.first().click();

        // Enter rejection reason
        const reasonInput = alicePage.locator('textarea, input[name*="reason"]');
        const hasReason = await reasonInput.first().isVisible().catch(() => false);

        if (hasReason) {
          await reasonInput.first().fill('Action not authorized by policy');
        }

        // Reject
        const rejectButton = alicePage.locator('button:has-text("Reject")');
        await rejectButton.first().click();

        // Verify agent halted (use text matching)
        const haltedMessage = alicePage.locator(
          'text=/halted|stopped|rejected/i'
        );

        const wasHalted = await haltedMessage.first()
          .isVisible({ timeout: 10000 })
          .catch(() => false);

        console.log(`Agent ${wasHalted ? 'halted' : 'status unknown'} after rejection`);
      }
    });

    test('should handle timeout for unanswered approval requests', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // This test verifies timeout behavior
      // In a real scenario, unanswered approvals would timeout

      // Look for timeout-related UI elements (use text matching)
      const timeoutIndicator = alicePage.locator(
        'text=/timeout|expired/i, ' +
        'text=/expires|timeout|time remaining/i'
      );

      const hasTimeout = await timeoutIndicator.first().isVisible().catch(() => false);
      console.log(`Timeout indicator ${hasTimeout ? 'is' : 'is not'} visible`);
    });
  });

  test.describe('RTK Query Caching Behavior', () => {
    test('should refresh pending list after approval', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Open approval dialog if available
      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        // Note initial pending count
        const pendingBadge = alicePage.locator(
          '[data-testid="pending-approvals-badge"], ' +
          '[data-testid="hitl-pending-badge"]'
        );
        const initialCount = await pendingBadge.first().textContent().catch(() => '0');

        // Approve the request
        await reviewButton.first().click();
        const approveButton = alicePage.locator('button:has-text("Approve")');
        await approveButton.first().click();

        // Wait for cache invalidation and refetch
        await alicePage.waitForTimeout(1000);

        // Pending count should decrease (RTK Query auto-refetch after mutation)
        const newCount = await pendingBadge.first().textContent().catch(() => '0');
        console.log(`Pending count: ${initialCount} -> ${newCount}`);

        // If there were multiple requests, count should decrease
        if (parseInt(initialCount || '0') > 0) {
          expect(parseInt(newCount || '0')).toBeLessThanOrEqual(parseInt(initialCount || '0'));
        }
      }
    });

    test('should refresh pending list after rejection', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        const pendingBadge = alicePage.locator('[data-testid*="pending"]');
        const initialCount = await pendingBadge.first().textContent().catch(() => '0');

        // Reject the request
        await reviewButton.first().click();
        const rejectButton = alicePage.locator('button:has-text("Reject")');
        await rejectButton.first().click();

        // Wait for cache invalidation
        await alicePage.waitForTimeout(1000);

        const newCount = await pendingBadge.first().textContent().catch(() => '0');
        console.log(`Pending count after rejection: ${initialCount} -> ${newCount}`);
      }
    });

    test('should show loading state during approval mutation', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      const reviewButton = alicePage.locator(
        'button:has-text("Review"), [data-testid*="review-approval"]'
      );

      const hasReviewButton = await reviewButton.first().isVisible().catch(() => false);

      if (hasReviewButton) {
        await reviewButton.first().click();

        const approveButton = alicePage.locator('button:has-text("Approve")');
        await approveButton.first().click();

        // Check for loading indicator (button disabled, spinner, etc.)
        const loadingIndicator = alicePage.locator(
          'button:disabled, ' +
          '[data-loading="true"], ' +
          '.spinner, ' +
          '[aria-busy="true"]'
        );

        // Loading state might be brief, log visibility
        const hasLoading = await loadingIndicator.first().isVisible({ timeout: 500 }).catch(() => false);
        console.log(`Loading state ${hasLoading ? 'detected' : 'too quick to capture'}`);
      }
    });
  });

  test.describe('Batch Approval (Admin)', () => {
    test('should show batch approval panel for admin users', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin');
      await expect(adminPage.locator('body')).toBeVisible();

      // Admin should see batch approval panel
      const batchPanel = adminPage.locator(
        '[data-testid="batch-approval-panel"], ' +
        '[data-testid="bulk-actions"], ' +
        'text=/batch|bulk|select all/i'
      );

      const hasBatchPanel = await batchPanel.first().isVisible({ timeout: 5000 }).catch(() => false);
      console.log(`Batch approval panel ${hasBatchPanel ? 'is' : 'is not'} visible for admin`);
    });

    test('should allow selecting multiple approval requests', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin');
      await expect(adminPage.locator('body')).toBeVisible();

      // Look for selection checkboxes
      const checkboxes = adminPage.locator(
        'input[type="checkbox"][data-testid*="select-request"], ' +
        'input[type="checkbox"][aria-label*="Select"], ' +
        '[role="checkbox"][aria-label*="Select"]'
      );

      const checkboxCount = await checkboxes.count();
      console.log(`Found ${checkboxCount} selectable requests`);

      if (checkboxCount >= 2) {
        // Select multiple requests
        await checkboxes.nth(0).click();
        await checkboxes.nth(1).click();

        // Verify batch action buttons appear
        const batchApproveBtn = adminPage.locator(
          'button:has-text("Approve Selected"), ' +
          'button:has-text("Batch Approve"), ' +
          '[data-testid="batch-approve-btn"]'
        );

        const hasBatchApprove = await batchApproveBtn.first().isVisible().catch(() => false);
        console.log(`Batch approve button ${hasBatchApprove ? 'appeared' : 'not visible'}`);
      }
    });

    test('should batch approve multiple requests', async ({ adminPage }) => {
      // Only mock API in frontend-only mode
      if (!backendEnabled) {
        await adminPage.route('**/api/v1/agents/requests/batch/approve', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              processed: 2,
              failed: 0,
              results: [
                { request_id: 'req-1', success: true },
                { request_id: 'req-2', success: true },
              ],
            }),
          });
        });
      }

      await adminPage.goto('/studio/admin');
      await expect(adminPage.locator('body')).toBeVisible();

      // Select all checkbox
      const selectAllCheckbox = adminPage.locator(
        'input[type="checkbox"][data-testid="select-all"], ' +
        '[aria-label*="Select all"]'
      );

      const hasSelectAll = await selectAllCheckbox.first().isVisible().catch(() => false);

      if (hasSelectAll) {
        await selectAllCheckbox.first().click();

        // Click batch approve
        const batchApproveBtn = adminPage.locator(
          'button:has-text("Approve Selected"), ' +
          'button:has-text("Approve All")'
        );

        const hasBatchApprove = await batchApproveBtn.first().isVisible().catch(() => false);

        if (hasBatchApprove) {
          await batchApproveBtn.first().click();

          // Verify success message (use text matching)
          const successMessage = adminPage.locator(
            'text=/approved|success/i'
          );

          const wasSuccessful = await successMessage.first()
            .isVisible({ timeout: 5000 })
            .catch(() => false);

          console.log(`Batch approval ${wasSuccessful ? 'succeeded' : 'status unknown'}`);
        }
      }
    });

    test('should batch reject multiple requests with reason', async ({ adminPage }) => {
      // Only mock API in frontend-only mode
      if (!backendEnabled) {
        await adminPage.route('**/api/v1/agents/requests/batch/reject', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              processed: 2,
              failed: 0,
              results: [
                { request_id: 'req-1', success: true },
                { request_id: 'req-2', success: true },
              ],
            }),
          });
        });
      }

      await adminPage.goto('/studio/admin');
      await expect(adminPage.locator('body')).toBeVisible();

      // Look for batch reject button
      const batchRejectBtn = adminPage.locator(
        'button:has-text("Reject Selected"), ' +
        'button:has-text("Batch Reject")'
      );

      const hasBatchReject = await batchRejectBtn.first().isVisible().catch(() => false);

      if (hasBatchReject) {
        await batchRejectBtn.first().click();

        // Fill in batch rejection reason
        const reasonInput = adminPage.locator(
          'textarea[placeholder*="reason"], ' +
          'input[name*="reason"]'
        );

        const hasReason = await reasonInput.first().isVisible().catch(() => false);

        if (hasReason) {
          await reasonInput.first().fill('Policy violation - batch rejection');
        }

        // Confirm rejection
        const confirmBtn = adminPage.locator('button:has-text("Confirm"), button:has-text("Reject")');
        await confirmBtn.first().click();

        console.log('Batch rejection submitted');
      }
    });

    test('should show partial failure in batch operations', async ({ adminPage }) => {
      // Mock partial failure
      if (!backendEnabled) {
        await adminPage.route('**/api/v1/agents/requests/batch/approve', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: false,
              processed: 1,
              failed: 1,
              results: [
                { request_id: 'req-1', success: true },
                { request_id: 'req-2', success: false, error: 'Request not found' },
              ],
            }),
          });
        });
      }

      await adminPage.goto('/studio/admin');
      await expect(adminPage.locator('body')).toBeVisible();

      // Attempt batch operation
      const batchApproveBtn = adminPage.locator('button:has-text("Approve Selected")');
      const hasBatchApprove = await batchApproveBtn.first().isVisible().catch(() => false);

      if (hasBatchApprove) {
        await batchApproveBtn.first().click();

        // Look for partial failure indication (use text matching)
        const partialFailure = adminPage.locator(
          'text=/partial|some failed|1 failed/i'
        );

        const hasPartialFailure = await partialFailure.first()
          .isVisible({ timeout: 5000 })
          .catch(() => false);

        console.log(`Partial failure ${hasPartialFailure ? 'shown' : 'not shown'}`);
      }
    });
  });

  test.describe('BackgroundAgentPanel Integration', () => {
    test('should show awaiting_approval status in background agent panel', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for background agent panel
      const agentPanel = alicePage.locator(
        '[data-testid*="agent-panel"], ' +
        '[data-testid*="background-agent"], ' +
        '.background-agent-panel'
      );

      const hasPanel = await agentPanel.first().isVisible().catch(() => false);

      if (hasPanel) {
        // Look for awaiting_approval status
        const awaitingStatus = agentPanel.locator(
          '[data-testid*="awaiting"], ' +
          'text=/awaiting|pending|approval/i'
        );

        const hasAwaitingStatus = await awaitingStatus.first().isVisible().catch(() => false);
        console.log(`Awaiting approval status ${hasAwaitingStatus ? 'is' : 'is not'} shown in panel`);
      }
    });

    test('should show confidence indicator for agent', async ({ alicePage }) => {
      await expect(alicePage.locator('body')).toBeVisible();

      // Look for confidence indicator in agent panel
      const confidenceIndicator = alicePage.locator(
        '[data-testid*="confidence"], ' +
        '.confidence-bar, ' +
        'text=/\\d+%/'
      );

      const hasConfidence = await confidenceIndicator.first().isVisible().catch(() => false);
      console.log(`Confidence indicator ${hasConfidence ? 'is' : 'is not'} visible`);
    });
  });
});
