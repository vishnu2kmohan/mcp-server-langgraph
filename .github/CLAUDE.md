# Claude Code Integration Guide

This document provides guidance for using Claude Code (Anthropic's CLI) with the MCP Server LangGraph project.

## Overview

Claude Code is an AI-powered coding assistant that provides:
- **Autonomous task execution**: Complete multi-step tasks without constant supervision
- **Codebase understanding**: Deep analysis of project structure and dependencies
- **Test generation**: Comprehensive test suite creation with high coverage
- **Documentation**: Automated documentation generation and maintenance
- **Refactoring**: Safe code refactoring with validation

## Project Structure for Claude Code

The project follows a pythonic src/ layout that Claude Code can navigate efficiently:

```
mcp_server_langgraph/
├── src/mcp_server_langgraph/     # Main package
│   ├── core/                      # Core functionality (agent, config, feature_flags)
│   ├── auth/                      # Authentication & authorization
│   │   ├── middleware.py          # AuthMiddleware with session support
│   │   ├── keycloak.py           # Keycloak integration
│   │   ├── session.py            # Session management (InMemory, Redis)
│   │   ├── role_mapper.py        # Advanced role mapping engine
│   │   ├── metrics.py            # 30+ authentication metrics
│   │   └── openfga.py            # OpenFGA client
│   ├── llm/                      # LLM factory and validators
│   ├── mcp/                      # MCP server implementations
│   ├── observability/            # Telemetry, tracing, metrics
│   ├── secrets/                  # Secrets management
│   └── health/                   # Health checks
├── tests/                        # Comprehensive test suite
│   ├── test_session.py          # Session management tests (26 tests)
│   ├── test_role_mapper.py      # Role mapper tests (23 tests)
│   ├── test_keycloak.py         # Keycloak tests (31 tests)
│   └── test_user_provider.py    # User provider tests (50+ tests)
├── config/                       # Configuration files
│   └── role_mappings.yaml       # Declarative role mapping config
├── docs/                         # Comprehensive documentation
├── deployments/                  # Kubernetes, Helm, Kustomize
└── monitoring/                   # Grafana dashboards, Prometheus alerts
```

## Workflow Optimization Features (New!)

**Added**: 2025-10-20

The project now includes optimized workflow templates and automation to make Claude Code sessions more efficient.

### Available Resources

**Templates** (`.claude/templates/`):
- `sprint-planning.md` - Comprehensive sprint initialization template
- `technical-analysis.md` - Deep technical analysis framework
- `progress-tracking.md` - Real-time sprint progress tracking

**Context Files** (`.claude/context/`):
- `recent-work.md` - Last 15 commits, recent sprint summary, current TODO status
- `testing-patterns.md` - Complete testing patterns with examples from 437+ tests
- `code-patterns.md` - Common code patterns and conventions from the codebase

**Slash Commands** (`.claude/commands/`):
- `/start-sprint <type>` - Initialize sprint with template (types: technical-debt, feature, bug-fix, docs, refactoring)
- `/progress-update` - Generate comprehensive sprint progress report
- `/test-summary [scope]` - Detailed test analysis (scopes: all, unit, integration, quality, failed)
- `/validate` - Run all validations (existing)
- `/test-all` - Run complete test suite (existing)
- `/fix-issue <number>` - Fix GitHub issue workflow (existing)
- `/deploy-dev` - Development deployment (existing)
- `/debug-auth` - Debug authentication (existing)
- `/setup-env` - Environment setup (existing)

### Quick Start with New Workflow

**Starting a Sprint**:
```
/start-sprint technical-debt

# Automatically:
1. Reads recent-work.md for context
2. Analyzes TODO_CATALOG.md with ultrathink
3. Creates sprint plan from template
4. Sets up progress tracking
5. Provides first task to work on
```

**Tracking Progress**:
```
/progress-update

# Automatically:
1. Collects git metrics (commits, files, lines)
2. Runs tests and captures results
3. Calculates completion rate and velocity
4. Assesses sprint health
5. Generates comprehensive update
```

**Checking Tests**:
```
/test-summary

# Automatically:
1. Runs all tests with coverage
2. Analyzes pass/fail/skip counts
3. Categorizes by test type
4. Identifies slow tests
5. Provides actionable recommendations
```

### Context Loading Benefits

**Before Optimization**:
- Manual context gathering: ~10 minutes per session
- Repeated explanations of recent work
- Inconsistent progress tracking

**After Optimization** (projected):
- Automated context loading: ~2 minutes
- Immediate understanding of recent changes
- Structured progress updates

**Expected Efficiency Gain**: 25-35% overall workflow improvement

---

## Best Practices for Claude Code

### 1. Task Decomposition

Claude Code excels when tasks are well-defined:

✅ **Good**: "Implement session management with Redis backend, including tests"
- Clear scope
- Testable outcome
- Well-defined deliverable

❌ **Avoid**: "Make the auth better"
- Vague requirements
- Unclear success criteria
- No measurable outcome

### 2. Incremental Development

Claude Code works best with incremental phases:

**Phase 1**: Core implementation
- Create interfaces and base classes
- Implement core functionality
- Add configuration support

**Phase 2**: Testing
- Unit tests for each component
- Integration tests
- Edge case coverage

**Phase 3**: Documentation
- Update ../CHANGELOG.md
- Add inline documentation
- Create usage examples

### 3. Testing Strategy

Claude Code can generate comprehensive test suites:

```python
# Claude Code generates tests with:
- Multiple test classes (by component)
- Comprehensive coverage (86%+ pass rate achieved)
- Mock-based testing (avoiding external dependencies)
- Integration scenarios (realistic use cases)
- Edge cases (error handling, validation)
```

Example from this project:
- **test_session.py**: 687 lines, 26 tests, full lifecycle coverage
- **test_role_mapper.py**: 712 lines, 23 tests, enterprise scenarios

### 4. Code Organization

Claude Code maintains clean code organization:

```python
# File structure Claude Code follows:
"""
Module docstring explaining purpose

Imports (grouped by: stdlib, third-party, local)

Constants and configuration

Classes (with comprehensive docstrings)

Helper functions

Main execution (if applicable)
"""
```

### 5. Documentation Standards

Claude Code generates documentation with:

- **Docstrings**: Comprehensive for all public APIs
- **Type hints**: Full type annotation throughout
- **../CHANGELOG.md**: Detailed with file references and line numbers
- **README updates**: Keep main README synchronized

## Recent Implementations by Claude Code

### Mintlify Documentation Integration (2025-10-14)

**Documentation Structure**:
- Moved `mint.json` to `docs/` directory for clean scanning
- Fixed all MDX/Markdown parsing errors (HTML entity escaping)
- 100% documentation coverage across all features
- Comprehensive navigation structure with 4 main tabs

**Files Updated**:
- `docs/mint.json` (currently backed up as `mint.json.backup`)
- `.mintlifyignore` - Enhanced ignore patterns
- Multiple `.mdx` files - Fixed `<` character escaping

### LangGraph 0.6.10 Upgrade (2025-10-13)

**Major Version Upgrade**:
- Upgraded from 0.2.28 → 0.6.10
- All 15 Dependabot PRs successfully merged
- 100% test pass rate (11/11 agent tests)
- Zero breaking changes detected
- Full API compatibility maintained

### Session Management

**Files Created**:
- `src/mcp_server_langgraph/auth/session.py` (450 lines)
  - InMemorySessionStore
  - RedisSessionStore
  - SessionStore ABC
  - Factory function

**Tests Created**:
- `tests/test_session.py` (687 lines)
  - 17 InMemorySessionStore tests
  - 9 RedisSessionStore tests
  - 5 Factory tests
  - 2 Integration tests

**Configuration Added**:
- 7 new settings in `core/config.py`
- Redis service in `docker-compose.yml`

### Advanced Role Mapping

**Files Created**:
- `src/mcp_server_langgraph/auth/role_mapper.py` (320 lines)
  - SimpleRoleMapping
  - GroupMapping
  - ConditionalMapping
  - RoleMapper engine

- `config/role_mappings.yaml` (142 lines)
  - Simple mappings
  - Group patterns
  - Conditional mappings
  - Role hierarchies

**Tests Created**:
- `tests/test_role_mapper.py` (712 lines)
  - 3 SimpleRoleMapping tests
  - 3 GroupMapping tests
  - 6 ConditionalMapping tests
  - 10 RoleMapper tests
  - 1 Enterprise integration test

### Enhanced Observability

**Files Created**:
- `src/mcp_server_langgraph/auth/metrics.py` (312 lines)
  - 30+ OpenTelemetry metrics
  - 6 helper functions
  - Comprehensive attribute tagging

## Working with Claude Code

### Starting a Task

```bash
# Launch Claude Code
claude

# Describe your task clearly
"Implement user profile management with the following requirements:
1. User CRUD operations
2. Profile photo upload to S3
3. Email verification workflow
4. Comprehensive tests
5. Update ../CHANGELOG.md"
```

### Reviewing Claude Code's Work

Claude Code provides:
- **Clear explanations**: What was implemented and why
- **File references**: Exact file paths and line numbers
- **Test results**: Pass/fail status with details
- **Next steps**: Recommendations for follow-up work

### Iterating with Claude Code

```bash
# If tests fail or adjustments needed:
"The session tests are failing due to Redis mock issues.
Please update the tests to properly mock the Redis client."

# Claude Code will:
1. Analyze the failure
2. Identify the root cause
3. Implement the fix
4. Verify with test execution
5. Report results
```

## Configuration for Claude Code

### Python Environment

**IMPORTANT**: Always use the project's virtual environment, never system Python.

**Virtual Environment**: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv`
**Python Version**: 3.13.7
**Package Manager**: uv

**Approved Methods** (in order of preference):

1. **Use `uv run`** (preferred):
   ```bash
   uv run python script.py
   uv run pytest tests/
   uv run mypy src/
   ```

2. **Explicit venv path**:
   ```bash
   .venv/bin/python script.py
   .venv/bin/pytest tests/
   ```

3. **Activate first** (only for multiple commands):
   ```bash
   source .venv/bin/activate && python -m pytest && mypy src/
   ```

**Never Use**: Bare `python`, `python3`, `pytest`, or `pip` commands (these use system Python).

**Full Documentation**: See `.claude/memory/python-environment-usage.md` for complete guidelines, troubleshooting, and examples.

### Environment Setup

Claude Code automatically detects:
- Python virtual environment (.venv)
- Package manager (uv, pip, poetry)
- Test framework (pytest)
- Code style tools (black, isort, mypy)

### Project-Specific Settings

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = ["unit", "integration", "e2e"]

[tool.black]
line-length = 120
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 120
```

## Tips for Maximum Productivity

### 1. Use TodoWrite Tool
Claude Code tracks tasks with TodoWrite:
- ✅ Completed tasks
- 🔄 In-progress tasks
- ⏸️ Pending tasks

### 2. Provide Context
Give Claude Code context about:
- Related files to read
- Existing patterns to follow
- Integration points to consider

### 3. Request Comprehensive Tests
Always ask for "comprehensive tests" to get:
- Multiple test classes
- Edge case coverage
- Integration scenarios
- Mock-based isolation

### 4. Review Generated Code
Claude Code generates production-quality code, but review:
- Security implications
- Performance considerations
- Edge cases specific to your domain

### 5. Maintain Documentation
After each Claude Code session:
- Update ../CHANGELOG.md (Claude Code does this automatically)
- Review generated documentation
- Verify README is current

## Code Quality Standards

Claude Code maintains:
- **Type safety**: Full type hints with mypy validation
- **Test coverage**: 70%+ coverage target (achieved 86% in Phase 2)
- **Documentation**: Docstrings for all public APIs
- **Code style**: Black, isort, flake8 compliance
- **Security**: Bandit scanning for vulnerabilities

## Example Claude Code Workflow

### Task: Add JWT Token Rotation

```
User: "Implement automatic JWT token rotation with the following:
1. Detect tokens expiring within 5 minutes
2. Automatically refresh using refresh token
3. Update session with new tokens
4. Add metrics for rotation events
5. Comprehensive tests
6. Update ../CHANGELOG.md"

Claude Code Response:
✅ Created src/mcp_server_langgraph/auth/token_rotation.py (250 lines)
✅ Updated src/mcp_server_langgraph/auth/middleware.py (+80 lines)
✅ Added rotation metrics to src/mcp_server_langgraph/auth/metrics.py (+15 lines)
✅ Created tests/test_token_rotation.py (350 lines, 18 tests)
✅ Updated ../CHANGELOG.md with implementation details
✅ All 18 tests passing

Summary:
- Implemented TokenRotationManager with configurable thresholds
- Integrated with AuthMiddleware.verify_token()
- Added 3 new metrics: token_rotation_attempts, token_rotation_success, token_rotation_failures
- Comprehensive test coverage including edge cases
- Backward compatible (rotation disabled by default)
```

## Troubleshooting

### Common Issues

**Issue**: Tests failing after implementation
- **Solution**: Ask Claude Code to analyze and fix test failures
- **Prevention**: Request tests be run after each implementation

**Issue**: Mock objects not working correctly
- **Solution**: Provide examples of correct mock usage from existing tests
- **Prevention**: Reference similar test files for consistency

**Issue**: Type checking errors
- **Solution**: Run `mypy src/` and provide output to Claude Code
- **Prevention**: Request type hints during initial implementation

## Best Practices Summary

1. ✅ **Clear requirements**: Provide detailed, specific requirements
2. ✅ **Incremental development**: Break large tasks into phases
3. ✅ **Comprehensive tests**: Always request full test coverage
4. ✅ **Documentation**: Update ../CHANGELOG.md and docstrings
5. ✅ **Review**: Review generated code before deployment
6. ✅ **Iterate**: Use Claude Code for refinements and fixes
7. ✅ **Test-driven**: Run tests early and often
8. ✅ **Context**: Provide examples and existing patterns

## Makefile Commands Reference

This project includes 40+ custom Makefile commands for common development tasks. Claude Code can use these commands directly via the Bash tool.

### Testing Commands

```bash
make test                 # Run all automated tests (unit + integration)
make test-unit            # Run unit tests only (fast, no external deps)
make test-integration     # Run integration tests (requires infrastructure)
make test-coverage        # Generate comprehensive coverage report
make test-property        # Run property-based tests (Hypothesis)
make test-contract        # Run contract tests (MCP protocol compliance)
make test-regression      # Run performance regression tests
make test-mutation        # Run mutation tests (test effectiveness)
make test-all-quality     # Run all quality tests
```

### Infrastructure & Setup

```bash
make install              # Install production dependencies
make install-dev          # Install development + test dependencies
make setup-infra          # Start Docker infrastructure (all services)
make setup-openfga        # Initialize OpenFGA (authorization)
make setup-keycloak       # Initialize Keycloak (SSO)
make dev-setup            # Complete developer setup (install+infra+setup)
make quick-start          # Quick start with defaults
```

### Validation Commands

```bash
make validate-openapi         # Validate OpenAPI schema
make validate-deployments     # Validate all deployment configs
make validate-docker-compose  # Validate Docker Compose
make validate-helm            # Validate Helm chart
make validate-kustomize       # Validate Kustomize overlays
make validate-all             # Run all deployment validations
```

### Deployment Commands

```bash
make deploy-dev               # Deploy to development (Kustomize)
make deploy-staging           # Deploy to staging (Kustomize)
make deploy-production        # Deploy to production (Helm)
make deploy-rollback-dev      # Rollback development deployment
make deploy-rollback-staging  # Rollback staging deployment
make deploy-rollback-production  # Rollback production deployment
```

### Code Quality Commands

```bash
make lint                 # Run linters (flake8, mypy)
make format               # Format code (black, isort)
make security-check       # Run security scans (bandit)
make pre-commit-setup     # Setup pre-commit hooks
```

### Running & Monitoring

```bash
make run                  # Run stdio MCP server
make run-streamable       # Run StreamableHTTP server
make health-check         # Check system health
make monitoring-dashboard # Open Grafana dashboards
make logs                 # Show infrastructure logs
make logs-follow          # Follow all logs in real-time
```

### Documentation

```bash
make docs-serve           # Serve Mintlify docs locally
make docs-build           # Build Mintlify docs
make docs-deploy          # Deploy docs to Mintlify
```

### Usage Examples

When working on tasks, Claude Code should use these commands directly:

```bash
# Example: Testing workflow
"Run the unit tests to verify the changes"
→ make test-unit

# Example: Validation workflow
"Validate all deployment configurations"
→ make validate-all

# Example: Setup workflow
"Set up the complete development environment"
→ make dev-setup
```

**Tip**: Run `make help` to see all available commands with descriptions.

## Custom Slash Commands

This project includes custom slash commands in `.claude/commands/` for common workflows:

### Available Commands

- **`/test-all`** - Run complete test suite (unit, integration, property, contract, regression)
- **`/deploy-dev`** - Execute development deployment workflow
- **`/validate`** - Run all validations (OpenAPI, deployments, Helm, Kustomize)
- **`/debug-auth`** - Debug authentication and authorization issues
- **`/setup-env`** - Complete environment setup from scratch
- **`/fix-issue <number>`** - Automated issue debugging workflow

### Using Slash Commands

```bash
# Run all tests and generate coverage report
/test-all

# Deploy to development environment
/deploy-dev

# Debug authentication problems
/debug-auth

# Fix GitHub issue #42
/fix-issue 42
```

Each command includes:
- Comprehensive step-by-step instructions
- Common troubleshooting scenarios
- Expected outputs and verification steps
- Integration with Makefile commands

## Planning Strategies with Extended Thinking

Claude Code supports extended thinking modes for complex problems. Use these keywords to request different levels of planning depth:

### Thinking Modes

1. **`"think"`** - Basic planning (default)
   - Quick analysis
   - Simple task breakdown
   - Good for straightforward tasks

2. **`"think hard"`** - Enhanced planning
   - Deeper analysis
   - More detailed considerations
   - Better for moderately complex tasks

3. **`"think harder"`** - Advanced planning
   - Comprehensive analysis
   - Multiple approaches considered
   - Edge case identification
   - Good for complex features

4. **`"ultrathink"`** - Maximum planning depth
   - Exhaustive analysis
   - Architecture considerations
   - Security and performance implications
   - Multiple solution comparisons
   - Best for critical or complex architectural changes

### When to Use Each Mode

**Use `"think"`** for:
- Bug fixes with clear root cause
- Adding simple tests
- Documentation updates
- Minor refactoring

**Use `"think hard"`** for:
- New feature implementation
- Significant refactoring
- Integration with external systems
- Performance optimization

**Use `"think harder"`** for:
- Complex multi-component features
- Architectural changes
- Security-critical implementations
- Database schema changes

**Use `"ultrathink"`** for:
- Major architectural decisions
- Breaking changes requiring migration
- Complex distributed system features
- Critical security or compliance features

### Example Usage

```bash
# Simple bug fix
"Fix the session expiration bug in auth/middleware.py"

# Complex feature
"think hard: Implement distributed caching with Redis cluster support"

# Architectural change
"ultrathink: Design and implement a plugin system for custom authentication providers"
```

### Planning Output

When using extended thinking, Claude Code will:
1. Analyze the problem from multiple angles
2. Consider edge cases and failure modes
3. Evaluate trade-offs between approaches
4. Provide a detailed implementation plan
5. Identify potential risks and mitigations
6. Suggest testing strategies

**Best Practice**: For tasks requiring significant code changes or architectural decisions, always use at least `"think hard"` to ensure thorough planning before implementation.

## Resources

- **Claude Code Documentation**: https://docs.claude.com/claude-code
- **Project README**: [../README.md](../README.md)
- **Mintlify Documentation**: See `docs/` directory - Comprehensive docs with 100% coverage
- **Testing Guide**: [../docs/advanced/testing.mdx](../docs/advanced/testing.mdx)
- **Development Guide**: [../docs/advanced/development-setup.mdx](../docs/advanced/development-setup.mdx)
- **CHANGELOG**: [../CHANGELOG.md](../CHANGELOG.md)

## Support

For issues or questions about Claude Code integration:
1. Check the [Claude Code documentation](https://docs.claude.com/claude-code)
2. Review recent conversations in `.claude/` directory
3. Report issues at https://github.com/anthropics/claude-code/issues

---

**Last Updated**: 2025-10-14
**Claude Code Version**: Sonnet 4.5 (claude-sonnet-4-5-20250929)
**LangGraph Version**: 0.6.10 (upgraded from 0.2.28 - all 15 Dependabot PRs merged)
