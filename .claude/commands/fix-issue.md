---
description: Automated workflow for debugging and fixing GitHub issues.
argument-hint: <issue-number>
---
# Fix Issue Workflow

Automated workflow for debugging and fixing GitHub issues.

**Usage**: `/fix-issue <issue-number>` or `/fix-issue $ARGUMENTS`

## Workflow Steps

1. **Retrieve Issue Details**
   ```bash
   gh issue view $ARGUMENTS --json title,body,labels,comments
   ```

   Analyze:
   - Issue title and description
   - Labels (bug, enhancement, documentation, etc.)
   - Existing comments and discussion
   - Related PRs or issues

2. **Reproduce the Issue**

   Based on issue type:

   **For Bugs**:
   - Identify affected component from description
   - Write a minimal reproduction test case
   - Run tests to confirm the bug

   **For Features**:
   - Review requirements and acceptance criteria
   - Check for existing similar functionality
   - Identify affected modules

   **For Documentation**:
   - Locate relevant documentation files
   - Review current content vs. requested changes

3. **Investigate Root Cause**

   - Search codebase for related code
   - Read relevant files
   - Check recent changes with git log/blame
   - Review ADRs for architectural context
   - Check CLAUDE.md for project conventions

4. **Develop Solution**

   - Create fix/feature implementation
   - Follow existing code patterns
   - Maintain type hints and documentation
   - Ensure backward compatibility

5. **Test the Fix**

   ```bash
   make test-unit
   ```

   - Add new tests for the fix
   - Ensure all existing tests still pass
   - Run relevant integration tests if needed
   - Check code coverage

6. **Update Documentation**

   - Update CHANGELOG.md with details
   - Update relevant documentation files
   - Add/update docstrings
   - Create/update ADR if architectural

7. **Commit Changes**

   ```bash
   git add .
   git commit -m "fix: <description> (#$ARGUMENTS)"
   ```

   Follow conventional commit format:
   - fix: for bug fixes
   - feat: for new features
   - docs: for documentation
   - test: for tests
   - refactor: for refactoring

8. **Create Pull Request**

   ```bash
   gh pr create --fill
   ```

   - Link to the issue
   - Describe changes and rationale
   - Include test results
   - Request reviews

## Summary

Provide:
- Issue analysis and root cause
- Solution approach and implementation details
- Files modified with line references
- Test results
- PR link for review
- Next steps

## Example

```bash
# Fix issue #42
/fix-issue 42
```

Will analyze issue #42, implement a fix, test it, and create a PR.
