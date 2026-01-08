# Contributing to MCP Server LangGraph

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Testing GitHub Actions Workflows](#testing-github-actions-workflows)
- [Code Contribution Process](#code-contribution-process)
  - [Pre-Push Validation](#4-pre-push-validation-recommended)
- [Testing Requirements](#testing-requirements)
- [Code Style](#code-style)
  - [Numeric Safety and NaN Handling](#numeric-safety-and-nan-handling)
- [Agent Studio Frontend Contribution Guidelines](#agent-studio-frontend-contribution-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Architecture Decision Records (ADRs)](#architecture-decision-records-adrs)

---

## Development Setup

### Quick Start

```bash
# Clone repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph

# Install dependencies
uv sync --extra dev

# Setup git hooks (REQUIRED)
make git-hooks
# Or manually: pre-commit install --hook-type pre-commit --hook-type pre-push

# Setup infrastructure
make dev-setup

# Run tests
make test
```

### Prerequisites

- **Python**: 3.10, 3.11, or 3.12 (3.13+ not supported)
- **uv**: Package manager (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker**: For test infrastructure and workflow testing
- **act**: For local GitHub Actions testing (install: `brew install act`)

**Additional Tools for Pre-commit Hooks** (required for full validation):
- **helm**: Kubernetes manifest validation (install: `brew install helm` or see [helm.sh](https://helm.sh/docs/intro/install/))
- **kubectl**: Kustomize validation (install: `brew install kubectl` or see [kubernetes.io](https://kubernetes.io/docs/tasks/tools/))
- **actionlint**: GitHub Actions workflow validation (install: `brew install actionlint` or see [github.com/rhysd/actionlint](https://github.com/rhysd/actionlint))

---

## Testing GitHub Actions Workflows

### ⚠️ REQUIRED: Test Workflows with act Before Committing

All changes to `.github/workflows/*.yaml` files **MUST** be tested locally with `act` before pushing.

**Why?** Recent CI failures were caused by issues that `act` would have caught:
- Missing dependencies (ModuleNotFoundError)
- Missing system tools (jq: command not found)
- Incorrect Python usage (bare `python` instead of `uv run --frozen python`)

### Quick Testing

```bash
# Validate syntax only (fast - 2 seconds)
make validate-workflows

# Test with act (2-5 minutes)
act push -W .github/workflows/YOUR_WORKFLOW.yaml -j JOB_NAME
```

### Complete Testing Checklist

See [.github/WORKFLOW_TESTING_CHECKLIST.md](.github/WORKFLOW_TESTING_CHECKLIST.md) for detailed checklist.

**Summary**:
1. ✅ Validate YAML syntax: `make validate-workflows`
2. ✅ Test with act: `act push -W .github/workflows/FILE.yaml -j JOB`
3. ✅ Fix any issues found
4. ✅ Run pre-commit hooks
5. ✅ Commit and push
6. ✅ Monitor CI: `gh run watch`

**Documentation**: [docs/reference/development/ci-cd/testing.mdx](docs/reference/development/ci-cd/testing.mdx)

---

## Code Contribution Process

### 1. Fork and Create Branch

```bash
# Fork repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/mcp-server-langgraph.git
cd mcp-server-langgraph

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow code style guidelines (Ruff linting + formatting, mypy type checking)
- Add tests for new features (TDD required)
- Update documentation as needed

### 3. Run Tests Locally

```bash
# Run all tests
make test

# Run specific test types
make test-unit              # Fast unit tests
make test-integration       # Integration tests
make test-e2e               # End-to-end tests (requires infrastructure)
make test-property          # Property-based tests
make test-contract          # Contract tests

# Run linting
make lint-check

# Run security checks
make security-check
```

### 4. Git Hooks and Validation

**🚨 CRITICAL: Eliminate CI Surprises**

**Updated 2025-11-13**: Reorganized for developer productivity and CI parity

This project uses a **two-stage validation strategy** optimized for rapid iteration while ensuring zero CI surprises:

#### Pre-commit Hooks (Fast - < 30 seconds)
Runs automatically on `git commit` for **changed files only**.

**What runs:**
- Auto-fixers: Ruff format + auto-fix, trailing-whitespace
- Fast linters: Ruff check, bandit, shellcheck
- Critical safety: memory safety, fixture organization
- File-specific validators: workflow syntax, MDX frontmatter

**Note**: Legacy tools (black, isort, flake8) replaced by Ruff for 10-100x faster performance

```bash
# Test pre-commit speed
git commit -m "feat: your changes"
# Target: < 30 seconds ⚡
```

**Performance**: **80-90% faster** than before (2-5 min → 15-30s)

#### Pre-push Hooks (Comprehensive - 8-12 minutes)
Runs automatically on `git push` for **all files**. Matches CI exactly.

**4-Phase Validation:**

**Phase 1: Fast Checks** (< 30s)
- Lockfile validation (`uv lock --check`)
- Workflow validation tests

**Phase 2: Type Checking** (1-2 min, warning only)
- MyPy type checking (non-blocking)

**Phase 3: Test Suite** (3-5 min)
- Unit tests: `pytest tests/ -m unit -x --tb=short`
- Smoke tests: `pytest tests/smoke/ -v --tb=short`
- Integration tests (last failed): `pytest tests/integration/ -x --tb=short --lf`
- Property tests: `HYPOTHESIS_PROFILE=ci pytest -m property -x --tb=short`

**Phase 4: Pre-commit Hooks (Pre-Push Stage)** (5-8 min)
- All comprehensive validators (documentation, deployment, etc.)
- Runs with `--hook-stage pre-push` flag

```bash
# Auto-runs on push
git push
# Target: 8-12 minutes, matches CI exactly 🎯
```

**Benefits:**
- **Fast commits**: Commit 10-20x more often
- **Zero surprises**: Pre-push matches CI exactly
- **Early detection**: Catches issues before push, not in CI
- **CI reliability**: Expected 80%+ reduction in CI failures

#### Manual Validation

Run pre-push validation manually anytime:
```bash
# Run complete 4-phase validation
make validate-pre-push

# Or run specific phases
uv run --frozen pytest tests/ -m unit           # Phase 3: Unit tests
uv run --frozen pytest tests/smoke/             # Phase 3: Smoke tests
pre-commit run --all-files --hook-stage pre-push  # Phase 4
```

#### CI Parity Mode (Optional)

**Run full integration tests locally to match CI exactly**:

```bash
# Enable CI_PARITY mode for pre-push hooks
export CI_PARITY=1
git push

# Or run integration tests manually
CI_PARITY=1 pytest tests/integration/ -v
```

**What CI_PARITY Does**:
- **Normal Mode** (default): Runs ~200 critical tests (unit, api, property) - completes in ~3 min
- **CI_PARITY=1 Mode**: Adds integration tests if Docker is available - matches CI exactly

**When to Use CI_PARITY**:
- ✅ Before opening a pull request (full validation)
- ✅ After making infrastructure changes (database, Docker, Kubernetes)
- ✅ When CI failures are hard to reproduce locally
- ❌ Not needed for routine development (normal mode is sufficient)

**Prerequisites**:
- Docker must be running
- Infrastructure containers must be healthy: `make dev-setup`

**Performance Impact**:
- Without CI_PARITY: ~3 min (fast feedback)
- With CI_PARITY: ~8-12 min (matches CI exactly)

**Example Workflow**:
```bash
# Routine development (fast)
git add .
git commit -m "feat: add new feature"
git push  # Runs ~200 critical tests in ~3 min

# Before PR (thorough)
export CI_PARITY=1
git push  # Runs full integration suite in ~8-12 min
```

**Implementation Details**:
- Defined in `scripts/run_pre_push_tests.py`
- Uses consolidated test marker: `(unit or api or property or integration) and not llm`
- Checks Docker availability before running integration tests
- See: `docs-internal/PRE_PUSH_OPTIMIZATION_ANALYSIS.md` for design rationale

#### Performance Monitoring

```bash
# Measure pre-commit performance
python scripts/dev/measure_hook_performance.py --stage commit

# Measure pre-push performance
python scripts/dev/measure_hook_performance.py --stage push
```

#### Bypass (EMERGENCY ONLY)

```bash
# Skip pre-commit (changed files only)
git commit --no-verify

# Skip pre-push (DANGEROUS - will likely fail CI!)
git push --no-verify
```

**⚠️ WARNING**: Bypassing hooks will likely cause CI failures!

#### Troubleshooting

**Pre-commit failures:**
```bash
# See specific failures
pre-commit run --all-files

# Run specific hook (use ruff-format for formatting, ruff for linting)
pre-commit run ruff-format --all-files
pre-commit run ruff --all-files
```

**Pre-push failures:**
```bash
# Run specific phase
uv run --frozen pytest tests/ -m unit     # Phase 3: Unit tests
uv lock --check                  # Phase 1: Lockfile
pre-commit run --all-files --hook-stage push  # Phase 4
```

#### Documentation

- Full guide: [TESTING.md](docs-internal/testing/TESTING.md#git-hooks-and-validation)
- Categorization: `docs-internal/HOOK_CATEGORIZATION.md`
- Migration guide: `docs-internal/PRE_COMMIT_PRE_PUSH_REORGANIZATION.md`

#### CI/Local Parity

**Pre-push hooks are designed to exactly match CI validation** to eliminate surprises after pushing.

**Identical Configurations:**
- ✅ **pytest worker count**: Both use `-n auto` (adapts to available cores)
- ✅ **MyPy type checking**: Both are **blocking** (push/build fails on type errors)
- ✅ **Hypothesis profile**: Both use `HYPOTHESIS_PROFILE=ci` (100 examples)
- ✅ **OpenTelemetry**: Both use `OTEL_SDK_DISABLED=true` to disable SDK

**Intentional Differences:**

| Aspect | Local Pre-push | CI | Rationale |
|--------|---------------|-----|-----------|
| **Test markers** | `unit and not contract` | `unit and not llm` | Contract tests may need services; LLM tests need API keys |
| **Integration tests** | Last-failed only (`--lf`), non-blocking | Full suite | Speed optimization - full suite in CI |
| **Smoke tests** | Always run | Dedicated workflow | Critical path validation before push |

**Validation Tests:**
- `tests/meta/test_hook_sync_validation.py` - Validates hook configuration
- `tests/meta/test_local_ci_parity.py` - Validates CI/local parity
- `tests/meta/test_pytest_xdist_enforcement.py` - Validates xdist isolation

**Why This Matters:**
- **Zero CI surprises**: What passes locally will pass in CI
- **Fast feedback**: Catch issues in seconds, not minutes waiting for CI
- **Consistent environment**: Same Python runtime (uv), same worker count, same strictness
- **Memory safety**: `-n auto` ensures consistent pytest-xdist behavior locally and in CI

**Enforcement:**
If hook configuration drifts from CI, meta-tests will fail with clear instructions to fix.

### 5. Test Workflow Changes (If Applicable)

If you modified `.github/workflows/*.yaml`:

```bash
# Required: Test with act
act push -W .github/workflows/YOUR_FILE.yaml -j JOB_NAME

# See: .github/WORKFLOW_TESTING_CHECKLIST.md
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: your feature description"
# Pre-commit hooks run automatically (< 30s) ⚡

git push origin feature/your-feature-name
# Pre-push hooks run automatically (8-12 min) 🎯
```

**Note**: Git hooks run automatically:
- **Pre-commit**: Fast validation on changed files (< 30s)
- **Pre-push**: Comprehensive validation matching CI (8-12 min)

Both hooks are installed automatically via `make git-hooks` during setup.

### 7. Create Pull Request

- Open PR on GitHub
- Fill out PR template
- Link related issues
- Wait for CI checks to pass
- Address review comments

---

## Testing Requirements

### Test-Driven Development (TDD)

This project follows TDD principles (see global CLAUDE.md for details):

1. **Write tests FIRST** before implementation
2. **Verify tests FAIL** initially (RED phase)
3. **Implement minimally** to make tests pass (GREEN phase)
4. **Refactor** while keeping tests green

### Test Coverage

- **Minimum**: 80% code coverage
- **Target**: 90%+ coverage
- **Critical paths**: 100% coverage (security, payments, data handling)

### Test Types Required

| Feature Type | Required Tests |
|--------------|----------------|
| **New Feature** | Unit + Integration + Property-based |
| **Bug Fix** | Regression test + Unit test |
| **Refactoring** | Existing tests must pass |
| **API Changes** | Contract tests + Integration tests |

### Multi-Python Version Testing

**Supported Python Versions**: 3.10, 3.11, 3.12 (3.13+ not supported)

#### Local Testing Limitations

**Challenge**: Local environments typically have only one Python version installed.

**CI Testing**: CI runs tests on all three Python versions (3.10, 3.11, 3.12) in parallel.

**Recommendation**:
- **Primary**: Test locally with Python 3.12 (most common)
- **Rely on CI**: Multi-version testing handled by CI
- **Optional**: Use Docker matrix for local multi-version testing

#### Optional: Local Multi-Version Testing with Docker

If you need to test multiple Python versions locally:

```bash
# Using Docker to test against Python 3.11
docker run --rm -v $(pwd):/app -w /app python:3.11 bash -c "pip install uv && uv sync && uv run --frozen pytest tests/"

# Using Docker to test against Python 3.12
docker run --rm -v $(pwd):/app -w /app python:3.12 bash -c "pip install uv && uv sync && uv run --frozen pytest tests/"

# Using Docker to test against Python 3.13
docker run --rm -v $(pwd):/app -w /app python:3.13 bash -c "pip install uv && uv sync && uv run --frozen pytest tests/"
```

#### Python Version Compatibility

**Best Practices**:
1. **Avoid version-specific features** - Don't use features only available in one Python version
2. **Check type hints** - Some type hint syntax varies between versions
3. **Test imports** - Ensure all imports work across versions
4. **Monitor CI** - Watch CI results for version-specific failures

**Common Compatibility Issues**:
- **Type hints**: Use `from __future__ import annotations` for compatibility
- **AsyncIO**: Behavior varies slightly between versions
- **Typing**: Some `typing` module features added in specific versions

**When CI Finds Version-Specific Issues**:
1. Check the failing Python version in CI logs
2. Use Docker locally to reproduce the failure
3. Fix the issue ensuring compatibility
4. Verify all versions pass in CI

---

## Code Style

### Python Style Guide

**Linting & Formatting** (enforced by pre-commit, consolidated to Ruff for 10-100x faster performance):
- **Ruff**: All-in-one linter + formatter (replaces black, isort, flake8)
  - Line length: 127
  - Linting rules: E/F (pycodestyle/pyflakes), I (isort), UP (pyupgrade), B (bugbear)
  - Formatting: black-compatible
- **mypy**: Type checking (preserved, Ruff doesn't do type checking)
- **bandit**: Security scanning (preserved, Ruff doesn't do security analysis)

**Type Checking** (gradually enforced):
- **mypy**: Gradual strict mode (see pyproject.toml)
- All new code must have type hints

### Running Formatters

```bash
# Check linting (replaces flake8 + isort checks)
make lint-check

# Auto-fix linting issues + format code (replaces black + isort)
make lint-fix

# Format code only (replaces black)
make lint-format

# Type checking (unchanged)
make lint-type-check

# Security scanning (unchanged)
make lint-security
```

**Note**: Legacy tools (black, isort, flake8) have been replaced by Ruff. All configuration is in `pyproject.toml`.

### Configuration

All style configuration is in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 127
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]  # pycodestyle, pyflakes, isort, pyupgrade, bugbear

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
disallow_untyped_defs = true
```

**Legacy configurations** (deprecated, will be removed):
- `[tool.black]` - Use `ruff format` instead
- `[tool.isort]` - Use `ruff check --select I` instead
- `[tool.flake8]` - Use `ruff check` instead

### Numeric Safety and NaN Handling

**Critical**: All API response models with float fields MUST handle NaN/Infinity values to prevent JSON serialization failures.

#### The Problem

Prometheus `histogram_quantile()` and other metrics calculations can return `NaN` when there's insufficient data. Python's `json.dumps()` raises `ValueError` for NaN/Infinity:

```python
>>> import json
>>> json.dumps({"latency_p99": float("nan")})
ValueError: Out of range float values are not JSON compliant
```

#### The Solution

Use the `safe_float()` utility from `mcp_server_langgraph.core.numeric` with Pydantic field validators:

```python
from pydantic import BaseModel, Field, field_validator
from mcp_server_langgraph.core.numeric import safe_float

class MetricsResponse(BaseModel):
    latency_p99: float = Field(..., description="99th percentile latency")

    @field_validator("latency_p99", mode="before")
    @classmethod
    def validate_latency_p99(cls, v: float | None) -> float:
        """Convert NaN/Inf to 0.0 for JSON serialization safety."""
        return safe_float(v)
```

#### Available Numeric Utilities

All utilities are in `mcp_server_langgraph.core.numeric`:

| Function | Description | Default |
|----------|-------------|---------|
| `safe_float(value, default=0.0)` | Converts NaN/Inf to safe default | 0.0 |
| `safe_average(values, default=0.0)` | Safe mean calculation | 0.0 |
| `safe_divide(a, b, default=0.0)` | Division with zero protection | 0.0 |
| `safe_round(value, ndigits, default=0.0)` | Safe rounding | 0.0 |
| `safe_sum(values)` | Sum ignoring NaN values | 0.0 |

#### When to Add Validators

Add `safe_float` validators to response models when:
- Field comes from Prometheus/metrics calculations
- Field is a percentile (p50, p95, p99)
- Field is a ratio/percentage
- Field is a confidence score
- Field is a cost/budget value

#### Testing Pattern

Follow TDD with NaN test cases:

```python
def test_response_model_nan_field(self) -> None:
    """GIVEN NaN value for field
    WHEN ResponseModel is created
    THEN field is converted to 0.0
    """
    response = ResponseModel(field=float("nan"))
    assert response.field == 0.0
    assert math.isfinite(response.field)
```

See `tests/unit/api/v1/test_response_model_nan_validators.py` for comprehensive examples.

#### Architecture Decision

For complete rationale, see ADR-0097: NaN Safety in API Response Models.

---

## Agent Studio Frontend Contribution Guidelines

### Overview

Agent Studio is the web-based visual interface for building, managing, and monitoring LangGraph agents. The frontend is a React-based single-page application (SPA) with advanced features for agent configuration, workflow visualization, and real-time monitoring.

### Frontend Development Setup

#### Prerequisites

- **Node.js**: 18.x or 20.x (recommended)
- **npm**: 9.x or higher
- **Backend**: MCP Server LangGraph backend must be running

#### Quick Start

```bash
# Navigate to frontend directory
cd src/mcp_server_langgraph/studio/frontend

# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Development server will be available at http://localhost:5173
```

#### Backend Integration

The frontend requires the MCP Server LangGraph backend to be running:

```bash
# In a separate terminal, from project root
make dev-setup          # Start infrastructure (PostgreSQL, Redis, etc.)
make dev-run-studio     # Start the backend API server

# Backend API will be available at http://localhost:8000
```

### Technology Stack

#### Core Framework
- **React 18**: Modern React with hooks and concurrent features
- **TypeScript**: Strict type checking for enhanced code quality
- **Vite**: Fast build tool with hot module replacement (HMR)

#### State Management
- **Redux Toolkit**: Centralized state management with slices
- **RTK Query**: Powerful data fetching and caching
- **React Query**: Additional data synchronization (if applicable)

#### UI Components
- **Tailwind CSS**: Utility-first CSS framework
- **React Flow**: Interactive workflow visualization and node-based graphs
- **Headless UI**: Unstyled, accessible UI components
- **Lucide React**: Modern icon library

#### Development Tools
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting
- **TypeScript Compiler**: Type checking
- **Vitest**: Fast unit testing framework
- **React Testing Library**: Component testing utilities

### Project Structure

```
src/mcp_server_langgraph/studio/frontend/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── agents/          # Agent-specific components
│   │   ├── workflows/       # Workflow visualization components
│   │   ├── common/          # Shared UI components
│   │   └── layout/          # Layout components (navbar, sidebar)
│   ├── features/            # Feature-based modules (Redux slices)
│   │   ├── agents/          # Agent management feature
│   │   ├── workflows/       # Workflow builder feature
│   │   └── auth/            # Authentication feature
│   ├── services/            # API services (RTK Query)
│   ├── hooks/               # Custom React hooks
│   ├── types/               # TypeScript type definitions
│   ├── utils/               # Utility functions
│   ├── styles/              # Global styles
│   └── App.tsx              # Root application component
├── public/                  # Static assets
├── tests/                   # Test files
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
├── eslint.config.js         # ESLint configuration
├── prettier.config.js       # Prettier configuration
└── package.json             # Dependencies and scripts
```

### Code Standards

#### TypeScript Strict Mode

All frontend code **MUST** use TypeScript strict mode:

```typescript
// tsconfig.json enforces:
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true
  }
}
```

**Type Safety Requirements**:
- ✅ All component props must have explicit types
- ✅ All function parameters and return types must be typed
- ✅ No `any` types (use `unknown` if type is truly unknown)
- ✅ Null/undefined handling must be explicit

**Example - Component with proper typing**:
```typescript
// Good: Explicit types
interface AgentCardProps {
  agentId: string;
  name: string;
  status: 'active' | 'inactive';
  onEdit?: (id: string) => void;
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agentId,
  name,
  status,
  onEdit
}) => {
  // Implementation
};

// Bad: Missing types
export const AgentCard = ({ agentId, name, status, onEdit }) => {
  // TypeScript errors!
};
```

#### ESLint Configuration

ESLint enforces code quality and consistency:

```javascript
// eslint.config.js
export default {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',
    'react/react-in-jsx-scope': 'off',  // Not needed in React 18
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
  }
};
```

**Key Rules**:
- No `any` types (error)
- Explicit function return types (warning)
- Proper React hooks usage (error)
- Exhaustive dependency arrays (warning)

#### Prettier Formatting

Prettier ensures consistent code formatting:

```javascript
// prettier.config.js
export default {
  semi: true,
  trailingComma: 'es5',
  singleQuote: true,
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
};
```

**Running Formatters**:
```bash
# Check code style
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Format code with Prettier
npm run format

# Check formatting without modifying files
npm run format:check
```

### Component Development Guidelines

#### Component Structure

Use functional components with TypeScript and hooks:

```typescript
import React, { useState, useEffect } from 'react';

interface MyComponentProps {
  title: string;
  count?: number;
}

export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  count = 0
}) => {
  const [value, setValue] = useState<number>(count);

  useEffect(() => {
    // Side effects
  }, [count]);

  return (
    <div className="p-4">
      <h1>{title}</h1>
      <p>Count: {value}</p>
    </div>
  );
};
```

#### Redux Toolkit State Management

Create feature slices for state management:

```typescript
// features/agents/agentsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface AgentsState {
  agents: Agent[];
  selectedId: string | null;
  loading: boolean;
}

const initialState: AgentsState = {
  agents: [],
  selectedId: null,
  loading: false,
};

const agentsSlice = createSlice({
  name: 'agents',
  initialState,
  reducers: {
    setAgents(state, action: PayloadAction<Agent[]>) {
      state.agents = action.payload;
    },
    selectAgent(state, action: PayloadAction<string>) {
      state.selectedId = action.payload;
    },
  },
});

export const { setAgents, selectAgent } = agentsSlice.actions;
export default agentsSlice.reducer;
```

#### RTK Query API Services

Define API endpoints using RTK Query:

```typescript
// services/api.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: '/api/v1' }),
  endpoints: (builder) => ({
    getAgents: builder.query<Agent[], void>({
      query: () => 'agents',
    }),
    createAgent: builder.mutation<Agent, CreateAgentRequest>({
      query: (agent) => ({
        url: 'agents',
        method: 'POST',
        body: agent,
      }),
    }),
  }),
});

export const { useGetAgentsQuery, useCreateAgentMutation } = api;
```

#### React Flow Workflow Visualization

Build interactive workflows using React Flow:

```typescript
import ReactFlow, { Node, Edge, Controls, Background } from 'reactflow';
import 'reactflow/dist/style.css';

interface WorkflowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (changes: any) => void;
  onEdgesChange: (changes: any) => void;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
}) => {
  return (
    <div className="h-screen w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
};
```

### Testing Requirements

#### Test Framework

- **Vitest**: Unit and integration testing
- **React Testing Library**: Component testing
- **MSW (Mock Service Worker)**: API mocking (optional)

#### Test Coverage Requirements

| Code Type | Minimum Coverage | Target Coverage |
|-----------|------------------|-----------------|
| **Components** | 70% | 85% |
| **Utilities** | 80% | 95% |
| **Redux Slices** | 80% | 90% |
| **API Services** | 60% | 80% |

#### Writing Tests

**Component Testing Example**:
```typescript
// AgentCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AgentCard } from './AgentCard';

describe('AgentCard', () => {
  it('renders agent name and status', () => {
    render(
      <AgentCard
        agentId="123"
        name="Test Agent"
        status="active"
      />
    );

    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn();
    render(
      <AgentCard
        agentId="123"
        name="Test Agent"
        status="active"
        onEdit={onEdit}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith('123');
  });
});
```

**Redux Slice Testing Example**:
```typescript
// agentsSlice.test.ts
import { describe, it, expect } from 'vitest';
import agentsReducer, { setAgents, selectAgent } from './agentsSlice';

describe('agentsSlice', () => {
  it('should set agents', () => {
    const initialState = { agents: [], selectedId: null, loading: false };
    const agents = [{ id: '1', name: 'Agent 1' }];

    const newState = agentsReducer(initialState, setAgents(agents));

    expect(newState.agents).toEqual(agents);
  });
});
```

#### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode (for development)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run tests for specific file
npm test -- AgentCard.test.tsx
```

### Pull Request Requirements

Before submitting a frontend PR, ensure:

#### Code Quality
- [ ] All TypeScript errors resolved (`npm run type-check`)
- [ ] No ESLint errors (`npm run lint`)
- [ ] Code formatted with Prettier (`npm run format`)
- [ ] No unused imports or variables

#### Testing
- [ ] All tests pass (`npm test`)
- [ ] New components have tests
- [ ] Coverage meets minimum requirements (70%+)
- [ ] No console errors in tests

#### Build
- [ ] Production build succeeds (`npm run build`)
- [ ] No build warnings
- [ ] Bundle size is reasonable (check with `npm run build -- --stats`)

#### Browser Testing
- [ ] Tested in Chrome/Edge (Chromium)
- [ ] Tested in Firefox
- [ ] Tested in Safari (if available)
- [ ] No console errors or warnings in browser
- [ ] Responsive design works on mobile/tablet

#### Documentation
- [ ] Component props documented with JSDoc
- [ ] Complex logic has inline comments
- [ ] README updated if adding new features
- [ ] Storybook stories added (if using Storybook)

### Development Workflow

#### Feature Development

```bash
# 1. Create feature branch
git checkout -b feature/agent-studio-new-feature

# 2. Start dev server
cd src/mcp_server_langgraph/studio/frontend
npm run dev

# 3. Make changes with hot reload

# 4. Run tests frequently
npm run test:watch

# 5. Before committing
npm run lint:fix
npm run format
npm test
npm run type-check

# 6. Commit changes
git add .
git commit -m "feat(studio): add new feature"
```

#### Debugging

**React DevTools**: Install browser extension for component inspection

**Redux DevTools**: Install browser extension for state debugging

**Vite DevTools**: Built-in HMR overlay for errors

**Console Logging**:
```typescript
// Development only
if (import.meta.env.DEV) {
  console.log('Debug info:', data);
}
```

### Common Issues and Solutions

#### Issue: TypeScript errors after `npm install`

**Solution**:
```bash
# Rebuild TypeScript declarations
npm run type-check
# If errors persist, clear node_modules
rm -rf node_modules package-lock.json
npm install
```

#### Issue: Vite dev server not hot-reloading

**Solution**:
```bash
# Restart dev server
npm run dev
# Or clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

#### Issue: Tests failing with "Cannot find module"

**Solution**:
```bash
# Ensure test environment is set up
npm install --include=dev
# Check vitest.config.ts has correct resolve.alias
```

#### Issue: Redux state not updating

**Solution**:
- Ensure reducers are immutable (use Redux Toolkit's `createSlice`)
- Check Redux DevTools for action dispatches
- Verify selectors are using correct state paths

### Resources

- **React Documentation**: [react.dev](https://react.dev)
- **TypeScript Handbook**: [typescriptlang.org/docs](https://www.typescriptlang.org/docs/)
- **Redux Toolkit**: [redux-toolkit.js.org](https://redux-toolkit.js.org/)
- **React Flow**: [reactflow.dev](https://reactflow.dev/)
- **Tailwind CSS**: [tailwindcss.com](https://tailwindcss.com/)
- **Vitest**: [vitest.dev](https://vitest.dev/)
- **React Testing Library**: [testing-library.com/react](https://testing-library.com/react)

---

## Commit Guidelines

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples**:

```text
feat(auth): add JWT token rotation

Implements automatic token refresh when token expires within 5 minutes.
Includes comprehensive tests and metrics.

Closes #123
```

```text
fix(ci): add missing optional dependencies to workflows

- Add --extra dev to uv sync commands
- Fixes ModuleNotFoundError in E2E and unit tests
- Tested locally with act before committing

Fixes: #456
```

### Signing Commits

```bash
# Configure GPG signing
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_KEY_ID

# Or use -S flag
git commit -S -m "feat: add feature"
```

---

## CI/CD Guidelines

### Workflow Modification Guidelines

**MUST**:
- ✅ Use `uv` for all Python operations (not `pip`)
- ✅ Use `uv run --frozen python` for scripts (not bare `python`)
- ✅ Use `uv sync --extra dev` for tests
- ✅ Test with `act` before committing
- ✅ Add timeouts to all jobs
- ✅ Use path filters to skip unnecessary runs

**MUST NOT**:
- ❌ Use `pip install` directly
- ❌ Use bare `python` or `python3` for project scripts
- ❌ Skip act testing for workflow changes
- ❌ Push workflow changes without local validation

### Testing Workflows Before Commit

**Minimum**:
```bash
make validate-workflows  # Syntax check
```

**Recommended**:
```bash
act push -W .github/workflows/YOUR_FILE.yaml -j JOB_NAME
```

**Best Practice**:
```bash
# Follow complete checklist
cat .github/WORKFLOW_TESTING_CHECKLIST.md
```

---

## Pull Request Process

### Before Submitting PR

- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Workflows tested with act (if modified)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for features/fixes)
- [ ] No debug code or console.log statements

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] CI/CD improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Tested locally
- [ ] Workflows tested with act (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings

## Related Issues
Closes #<issue_number>
```

---

## Questions or Issues?

- **Documentation**: See [docs/](docs/)
- **Development Setup**: [docs/advanced/development-setup.mdx](docs/advanced/development-setup.mdx)
- **Workflow Testing**: [docs/reference/development/ci-cd/testing.mdx](docs/reference/development/ci-cd/testing.mdx)
- **CI/CD Troubleshooting**: [docs/ci-cd-troubleshooting.mdx](docs/ci-cd-troubleshooting.mdx)
- **GitHub Discussions**: Open a discussion
- **Issues**: Open an issue with the bug/feature template

---

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build great software together.

---

## Architecture Decision Records (ADRs)

### What are ADRs?

Architecture Decision Records (ADRs) document significant architectural decisions made in the project. They provide context, rationale, and consequences of design choices.

### When to Create an ADR

Create an ADR when making decisions about:

- **Core Architecture**: System design, patterns, frameworks
- **Technology Choices**: Databases, libraries, cloud services
- **Security**: Authentication, authorization, encryption
- **Deployment**: Infrastructure, CI/CD, monitoring
- **Compliance**: GDPR, HIPAA, SOC 2 requirements

### ADR Creation Process

#### 1. Create Source ADR

```bash
# Copy template
cp adr/adr-0000-template.md adr/adr-NNNN-your-decision.md

# Edit the ADR
vim adr/adr-NNNN-your-decision.md
```

**Template structure**:
```markdown
# ADR-NNNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue we're addressing?

## Decision
What are we doing to address it?

## Consequences
What are the positive and negative effects?

## Alternatives Considered
What other options did we evaluate?
```

#### 2. Create Mintlify Documentation Version

```bash
# Copy to docs/architecture/
cp adr/adr-NNNN-your-decision.md docs/architecture/adr-NNNN-your-decision.mdx

# Add frontmatter
```

**Frontmatter example**:
```yaml
---
title: 'ADR-NNNN: Your Decision Title'
description: 'Brief description of the decision'
icon: 'lightbulb'
seoTitle: "ADR-NNNN: Your Decision Title"
seoDescription: "Architecture Decision Record NNNN: Brief description"
keywords: ["ADR", "architecture decision", "keyword1", "keyword2"]
contentType: "explanation"
---
```

#### 3. Update Navigation

Edit `docs/docs.json` and add your ADR to the appropriate section:

```json
{
  "group": "Architecture Decisions",
  "pages": [
    "architecture/adr-NNNN-your-decision"
  ]
}
```

#### 4. Commit Both Files

**IMPORTANT**: Always commit both the source ADR and the Mintlify version together.

```bash
git add adr/adr-NNNN-your-decision.md docs/architecture/adr-NNNN-your-decision.mdx docs/docs.json
git commit -m "docs(adr): add ADR-NNNN for [decision topic]"
```

### ADR Sync Validation

The project includes an automated pre-commit hook that validates ADR synchronization:

**Hook location**: `.githooks/pre-commit-adr-sync`

**What it checks**:
- ✅ Every `adr/*.md` has a matching `docs/architecture/*.mdx`
- ✅ Every `docs/architecture/*.mdx` has a matching `adr/*.md`
- ✅ Filenames use lowercase (`adr-NNNN-*`, not `ADR-NNNN-*`)
- ✅ ADR numbers match between source and docs

**To install the hook**:
```bash
ln -s ../../.githooks/pre-commit-adr-sync .git/hooks/pre-commit-adr-sync
```

### ADR Naming Conventions

- **Filename**: `adr-NNNN-kebab-case-title.md`
  - Use lowercase `adr-` prefix
  - Four-digit zero-padded number (e.g., `0001`, `0042`)
  - Kebab-case title (hyphens, no spaces)

- **Examples**:
  - ✅ `adr-0001-llm-multi-provider.md`
  - ✅ `adr-0042-visual-workflow-builder.md`
  - ❌ `ADR-0001-llm-multi-provider.md` (uppercase)
  - ❌ `adr-1-llm-provider.md` (not zero-padded)

### ADR Lifecycle

1. **Proposed**: Under discussion, not yet accepted
2. **Accepted**: Decision is final and being/has been implemented
3. **Deprecated**: No longer recommended, but still in use
4. **Superseded**: Replaced by a newer ADR (link to replacement)

### Updating Existing ADRs

**For minor updates** (typos, clarifications):
- Update both `adr/*.md` and `docs/architecture/*.mdx`
- Commit with message: `docs(adr): update ADR-NNNN [description]`

**For major changes** (reversing decision):
- Create a new ADR that supersedes the old one
- Update old ADR status to "Superseded by ADR-YYYY"

### Example ADR Commit Messages

```bash
# New ADR
git commit -m "docs(adr): add ADR-0044 for GraphQL API design"

# Update existing ADR
git commit -m "docs(adr): update ADR-0042 with implementation status"

# Deprecate ADR
git commit -m "docs(adr): deprecate ADR-0010, superseded by ADR-0044"
```

### Common Issues and Solutions

#### Issue: Pre-commit hook fails with "missing docs version"

**Solution**:
```bash
# Create the missing Mintlify version
cp adr/adr-NNNN-title.md docs/architecture/adr-NNNN-title.mdx
# Add frontmatter to .mdx file
git add docs/architecture/adr-NNNN-title.mdx
```

#### Issue: Pre-commit hook fails with "missing source version"

**Solution**:
```bash
# Create the missing source ADR
cp docs/architecture/adr-NNNN-title.mdx adr/adr-NNNN-title.md
# Remove frontmatter from .md file
git add adr/adr-NNNN-title.md
```

#### Issue: Pre-commit hook fails with "Uppercase filename detected"

**Solution**:
```bash
# Rename to lowercase
git mv adr/ADR-0041-title.md adr/adr-0041-title.md
```

### Resources

- **ADR Template**: `adr/adr-0000-template.md`
- **Existing ADRs**: `adr/` directory (source) and `docs/architecture/` (Mintlify)
- **ADR Best Practices**: [https://github.com/joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)

---

**Last Updated**: 2025-11-06
**Maintained By**: MCP Server LangGraph Team
