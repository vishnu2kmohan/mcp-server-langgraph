---
description: Guided codebase exploration before making changes. Use this command when starting work on a new area
---
# Explore Codebase

Guided codebase exploration before making changes. Use this command when starting work on a new area of the codebase.

## Usage

```bash
/explore-codebase
```

## Exploration Checklist

### 1. Understand Project Structure

- [ ] Read project README.md for overview
- [ ] Review directory structure:
  ```bash
  tree -L 3 src/
  ```
- [ ] Identify main modules and their responsibilities
- [ ] Check for separation of concerns (core/, auth/, api/, etc.)

### 2. Find Relevant Files

Use these commands to locate code related to your task:

```bash
# Find files by name pattern
find src/ -name "*pattern*"

# Search for specific functions/classes
grep -r "class ClassName" src/
grep -r "def function_name" src/

# Find all imports of a module
grep -r "from module import" src/
grep -r "import module" src/

# Search for specific functionality
grep -r "keyword" src/ --include="*.py"
```

### 3. Read Existing Tests

- [ ] Locate test files for the area you're working on:
  ```bash
  find tests/ -name "*test_module*"
  ```
- [ ] Read tests to understand expected behavior
- [ ] Identify test patterns and fixtures used
- [ ] Check test coverage:
  ```bash
  pytest --cov=src/module tests/test_module.py
  ```

### 4. Review Architecture Decisions

- [ ] Check for relevant ADRs (Architecture Decision Records):
  ```bash
  ls adr/ | grep -i "topic"
  cat adr/ADR-00XX-decision-name.md
  ```
- [ ] Read ADR index: `adr/README.md`
- [ ] Understand rationale for current implementation

### 5. Identify Patterns

- [ ] Look for similar implementations:
  ```bash
  # Find similar class structures
  grep -r "class.*Base" src/

  # Find similar API endpoints
  grep -r "@router\.(get|post)" src/

  # Find similar error handling
  grep -r "try:" src/module/
  ```

- [ ] Identify coding conventions:
  - Naming patterns (snake_case, PascalCase)
  - Docstring format
  - Type hint usage
  - Error handling approach

### 6. Check Dependencies

- [ ] Review module's dependencies:
  ```python
  # Read imports in target file
  head -20 src/module/file.py | grep "import"
  ```
- [ ] Check for circular dependencies
- [ ] Understand external library usage

### 7. Analyze Configuration

- [ ] Check for configuration files:
  ```bash
  # Environment variables
  cat .env.example | grep "MODULE"

  # Config classes
  grep -r "class Config" src/core/

  # YAML configs
  find config/ -name "*.yaml"
  ```

### 8. Review Documentation

- [ ] Check inline documentation:
  - Module docstrings
  - Function/class docstrings
  - Inline comments
- [ ] Read external docs:
  ```bash
  # Mintlify documentation
  ls docs/ | grep "topic"
  cat docs/topic.mdx
  ```

### 9. Understand Data Flow

- [ ] Trace data flow through the system:
  - Input → Validation → Processing → Output
  - Request → Middleware → Handler → Response
  - Event → Handler → Side Effects

- [ ] Identify key abstractions:
  - Interfaces/Abstract Base Classes
  - Factory patterns
  - Strategy patterns

### 10. Check for Edge Cases

- [ ] Review error handling:
  ```bash
  grep -r "raise " src/module/
  grep -r "except " src/module/
  ```
- [ ] Identify validation logic
- [ ] Look for boundary condition handling

## Exploration Output

After exploration, you should be able to answer:

1. **What does this code do?**: High-level purpose
2. **How does it work?**: Implementation approach
3. **Why was it designed this way?**: Architectural rationale (check ADRs)
4. **What patterns does it follow?**: Coding conventions
5. **What tests exist?**: Test coverage and patterns
6. **What dependencies does it have?**: Internal and external
7. **What could go wrong?**: Error scenarios and edge cases
8. **How does it integrate?**: Interfaces with other components

## Key Files to Always Check

- **README.md**: Project overview
- **adr/README.md**: Architecture decisions
- **TESTING.md**: Testing guidelines
- **CONTRIBUTING.md**: Development standards
- **.github/CLAUDE.md**: Claude Code integration guide
- **pyproject.toml**: Dependencies and project config

## Quick Reference Commands

```bash
# File search
find src/ -name "*auth*"

# Content search
grep -r "search_term" src/ --include="*.py"

# Tree view
tree -L 2 src/

# Test files
find tests/ -name "test_*.py"

# ADR search
grep -r "keyword" adr/

# Coverage
pytest --cov=src --cov-report=term-missing tests/
```

## Success Criteria

- ✅ Can explain what the code does
- ✅ Can explain how it works
- ✅ Identified patterns to follow
- ✅ Found relevant tests
- ✅ Reviewed relevant ADRs
- ✅ Understand integration points
- ✅ Identified potential edge cases

---

**Next Step**: After exploration, use `/plan-feature` to create implementation plan.
