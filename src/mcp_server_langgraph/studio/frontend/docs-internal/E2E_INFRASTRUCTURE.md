# E2E Test Infrastructure Requirements

## Overview

The Agent Studio frontend has 27 E2E test specifications covering persona journeys, canvas interactions, and compliance flows. These tests are designed to run against a real backend to validate the complete integration.

## Infrastructure Components

### Required Services

| Service | Default URL | Port | Purpose |
|---------|-------------|------|---------|
| **Frontend** | `http://localhost:5175` | 5175 | Vite dev server |
| **API Server** | `http://localhost:8000` | 8000 | LangGraph MCP backend |
| **Keycloak** | `http://localhost:9082` | 9082 | SSO authentication |
| **Qdrant** | `http://localhost:9333` | 9333 | Vector database |

### Test Users (Keycloak)

| User | Password | Persona | Access Level |
|------|----------|---------|--------------|
| admin | admin123 | admin | Full access |
| alice | alice123 | developer | Power user |
| bob | bob123 | user | Standard user |

These users are provisioned in the Keycloak realm configuration (`default-realm.json`).

## Quick Start

### Prerequisites

1. **Docker** - For running backend services
2. **Node.js 20+** - For frontend and Playwright
3. **Make** - For infrastructure commands

### Running E2E Tests

```bash
# 1. Start all backend infrastructure
make test-infra-up-build

# 2. Wait for services to be healthy (~30-60 seconds)

# 3. Run all E2E tests
npm run test:e2e

# OR run specific browser only (faster for local dev)
npm run test:e2e:chromium
```

### Running Without Backend (Mock Mode)

For UI-only validation during development:

```bash
# Frontend-only tests with mock auth
BACKEND_ENABLED=false npm run test:e2e
```

**Note:** Mock mode only validates UI rendering, not API integration.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_URL` | `http://localhost:5175` | Frontend dev server URL |
| `API_URL` | `http://localhost:8000` | Backend API URL |
| `KEYCLOAK_URL` | `http://localhost:9082` | Keycloak SSO URL |
| `KEYCLOAK_REALM` | `default` | Keycloak realm name |
| `QDRANT_URL` | `http://localhost:9333` | Vector database URL |
| `BACKEND_ENABLED` | `true` | Enable backend integration |
| `PW_WORKERS` | Auto-calculated | Playwright worker count |
| `PW_BROWSERS` | All | Limit browser projects |

## Authentication Flow

E2E tests use OAuth2 Authorization Code + PKCE flow per RFC 9700:

1. Navigate to `/api/v1/auth/login` (initiates PKCE)
2. Redirect to Keycloak login page
3. Fill in test user credentials
4. Token exchange at `/api/v1/auth/callback`
5. Redirect to `/auth/callback#access_token=...`
6. AuthCallbackPage stores tokens in localStorage
7. Redirect to `/studio`

### Fallback Mock Authentication

If Keycloak authentication fails, tests fall back to mock auth:

- Sets mock tokens in localStorage
- Sets user_info for persona detection
- Skips onboarding modal automatically

## Test Categories

### Persona Journeys (7 specs)

| Spec | Persona | Validates |
|------|---------|-----------|
| `admin-journey.spec.ts` | Admin | Full system access |
| `alice-builder-journey.spec.ts` | Developer | Workflow building |
| `alice-analyst-journey.spec.ts` | Developer | Observability access |
| `alice-devops-journey.spec.ts` | Developer | DevOps features |
| `bob-user-journey.spec.ts` | User | Standard chat access |
| `security-admin-journey.spec.ts` | Admin | Compliance focus |
| `compliance-officer-journey.spec.ts` | Developer | Audit features |

### Feature Tests (13 specs)

| Spec | Feature |
|------|---------|
| `hybrid-shell-smoke.spec.ts` | HybridShell layout |
| `canvas-artifacts.spec.ts` | Canvas artifact editing |
| `session-sync-flow.spec.ts` | Session synchronization |
| `ai-suggestions.spec.ts` | AI inline suggestions |
| `persona-navigation.spec.ts` | RBAC nav filtering |
| `error-recovery.spec.ts` | Error handling |
| `file-operations.spec.ts` | File management |
| `execution-history.spec.ts` | Execution history view |
| `admin-alerts.spec.ts` | Alert management |

### Quality Tests (7 specs)

| Spec | Purpose |
|------|---------|
| `visual-regression.spec.ts` | Visual consistency |
| `accessibility.spec.ts` | WCAG 2.1 AA compliance |
| `performance.spec.ts` | Load time metrics |
| `responsive.spec.ts` | Mobile/tablet layouts |

## Resource Management

### Worker Calculation

Playwright workers are calculated based on:

1. **Explicit override:** `PW_WORKERS` environment variable
2. **CI mode:** Fixed 2 workers for GitHub Actions
3. **Auto-calculation:** Based on CPU cores and available memory

Each browser instance uses ~300-500MB memory.

### CI Configuration

In CI/CD (GitHub Actions):

- **Workers:** 2 (conservative for shared runners)
- **Retries:** 2 (handle flaky tests)
- **Max Failures:** 5 (fail fast to save resources)
- **Browsers:** All (chromium, firefox, webkit)

## Troubleshooting

### "Keycloak not reachable"

```bash
# Check if Keycloak is running
curl http://localhost:9082/authn/realms/default

# Restart infrastructure
make test-infra-down && make test-infra-up-build
```

### "API Server not healthy"

```bash
# Check API health
curl http://localhost:8000/health/

# Check logs
docker-compose -f docker-compose.test.yml logs api
```

### "Authentication failed"

1. Verify Keycloak realm has test users
2. Check if tokens are being stored in localStorage
3. Run with `DEBUG=pw:api` for detailed logs

### "Tests timing out"

- Increase `actionTimeout` in `playwright.config.ts`
- Check network latency to backend services
- Reduce parallel workers: `PW_WORKERS=1 npm run test:e2e`

## Local Development Tips

### Fast Iteration

```bash
# Run only Chromium (fastest)
npm run test:e2e:chromium

# Run specific test file
npx playwright test hybrid-shell-smoke.spec.ts

# Run with headed browser (see what's happening)
npx playwright test --headed

# Run with debug mode
npx playwright test --debug
```

### Visual Debugging

```bash
# Generate HTML report
npx playwright test --reporter=html

# Open report
npx playwright show-report
```

### Recording New Tests

```bash
# Start Playwright codegen
npx playwright codegen http://localhost:5175/studio
```

## Phase 7 Parity Testing

Before removing AppShell, E2E tests must validate:

1. **Chat functionality:** Message sending, session switching
2. **Navigation:** All persona-appropriate routes accessible
3. **RBAC:** Bob cannot access admin routes
4. **Persistence:** Session and workspace state preserved
5. **Performance:** P50 latency ≤ AppShell baseline

### Parity Test Command

```bash
# Run all persona journeys
npx playwright test *-journey.spec.ts

# Verify hybrid shell smoke test
npx playwright test hybrid-shell-smoke.spec.ts
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
e2e-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
    - name: Install dependencies
      run: npm ci
    - name: Start infrastructure
      run: make test-infra-up-build
    - name: Run E2E tests
      run: npm run test:e2e
      env:
        CI: true
        BACKEND_ENABLED: true
```

### Artifacts to Preserve

- `playwright-report/` - HTML test report
- `test-results/` - Screenshots and videos of failures
- `.metrics/` - Performance metrics

## Related Documentation

- [Playwright Configuration](../playwright.config.ts)
- [Auth Fixtures](../e2e/fixtures/auth.ts)
- [Global Setup](../e2e/fixtures/global-setup.ts)
- [Phase 6/7 Plan](/.claude/plans/functional-wibbling-scone.md)
