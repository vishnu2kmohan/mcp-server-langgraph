---
name: code-review
version: 1.0.0
description: Automated code review with best practices and security analysis
category: devops
author: Emergence AI
dependencies:
  - pygments>=2.17.0
  - tree-sitter>=0.20.0
sandbox_config:
  network: none
  filesystem: readonly
required_secrets: []
optional_secrets:
  - GITHUB_TOKEN
---

# Code Review Skill

Automated code review skill that analyzes code for best practices, potential bugs, security vulnerabilities, and maintainability issues.

## Capabilities

- **Static Analysis**: Identify potential bugs and code smells
- **Security Review**: Flag potential security vulnerabilities
- **Style Check**: Verify adherence to coding standards
- **Performance Review**: Identify performance bottlenecks
- **Maintainability**: Assess code readability and structure

## Usage Examples

- "Review this Python function for potential issues"
- "Check this code for security vulnerabilities"
- "Analyze the complexity of this module"
- "Suggest improvements for this implementation"

## Guidelines

1. **Be Constructive**: Provide actionable suggestions, not just criticism
2. **Prioritize Issues**: Focus on critical issues first
3. **Explain Why**: Always explain the reasoning behind suggestions
4. **Consider Context**: Understand the codebase context before reviewing
5. **Check Edge Cases**: Pay attention to error handling and edge cases

## Review Checklist

### Security
- [ ] Input validation and sanitization
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] Authentication/authorization checks
- [ ] Sensitive data handling
- [ ] Dependency vulnerabilities

### Code Quality
- [ ] Clear variable/function naming
- [ ] Appropriate error handling
- [ ] Code duplication
- [ ] Function length and complexity
- [ ] Comments for complex logic
- [ ] Type hints (Python) / type safety

### Performance
- [ ] Efficient algorithms (time complexity)
- [ ] Memory usage
- [ ] Database query optimization
- [ ] Caching opportunities
- [ ] Unnecessary computations

### Testing
- [ ] Test coverage
- [ ] Edge case coverage
- [ ] Integration tests
- [ ] Mock usage appropriateness

## Output Format

```markdown
# Code Review: [File/Function Name]

## Summary
[Overall assessment]

## Critical Issues
- **Issue 1**: [Description]
  - Location: line X
  - Suggestion: [Fix]

## Warnings
- **Warning 1**: [Description]
  - Location: line X
  - Suggestion: [Fix]

## Suggestions
- [Improvement suggestion 1]
- [Improvement suggestion 2]

## Security Notes
- [Security-related observations]

## Rating
- Security: X/10
- Maintainability: X/10
- Performance: X/10
```

## Supported Languages

- Python
- JavaScript/TypeScript
- Go
- Rust
- Java
- C/C++
