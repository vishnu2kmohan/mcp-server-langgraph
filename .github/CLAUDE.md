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
- Update CHANGELOG.md
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
- **CHANGELOG.md**: Detailed with file references and line numbers
- **README updates**: Keep main README synchronized

## Recent Implementations by Claude Code

### Session Management (Phase 2)

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

### Advanced Role Mapping (Phase 2)

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

### Enhanced Observability (Phase 2)

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
5. Update CHANGELOG.md"
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
- Update CHANGELOG.md (Claude Code does this automatically)
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
6. Update CHANGELOG.md"

Claude Code Response:
✅ Created src/mcp_server_langgraph/auth/token_rotation.py (250 lines)
✅ Updated src/mcp_server_langgraph/auth/middleware.py (+80 lines)
✅ Added rotation metrics to src/mcp_server_langgraph/auth/metrics.py (+15 lines)
✅ Created tests/test_token_rotation.py (350 lines, 18 tests)
✅ Updated CHANGELOG.md with implementation details
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
4. ✅ **Documentation**: Update CHANGELOG.md and docstrings
5. ✅ **Review**: Review generated code before deployment
6. ✅ **Iterate**: Use Claude Code for refinements and fixes
7. ✅ **Test-driven**: Run tests early and often
8. ✅ **Context**: Provide examples and existing patterns

## Resources

- **Claude Code Documentation**: https://docs.claude.com/claude-code
- **Project README**: [README.md](README.md)
- **Testing Guide**: [docs/development/testing.md](docs/development/testing.md)
- **Development Guide**: [docs/development/development.md](docs/development/development.md)
- **CHANGELOG**: [CHANGELOG.md](CHANGELOG.md)

## Support

For issues or questions about Claude Code integration:
1. Check the [Claude Code documentation](https://docs.claude.com/claude-code)
2. Review recent conversations in `.claude/` directory
3. Report issues at https://github.com/anthropics/claude-code/issues

---

**Last Updated**: 2025-10-12
**Claude Code Version**: Sonnet 4.5 (claude-sonnet-4-5-20250929)
