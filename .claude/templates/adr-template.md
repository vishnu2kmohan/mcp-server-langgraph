# [NUMBER]. [Title of Decision in Title Case]

Date: YYYY-MM-DD

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]

## Context

[Describe the issue or problem that needs to be addressed. Include:]

**Background**:
- What is the current situation?
- Why is a decision needed now?
- What are the business/technical drivers?

**Requirements**:
- What must the solution achieve?
- What are the constraints?
- What are the quality attributes (performance, security, scalability, etc.)?

**Stakeholders**:
- Who is affected by this decision?
- Who needs to be consulted?

## Decision

[State the decision clearly and concisely]

We will [choose/implement/adopt] **[specific solution/approach/technology]**.

**Rationale**:
- Why this solution addresses the problem
- Key benefits that drove the decision
- How it aligns with project goals

**Implementation Details**:
```[language if applicable]
[Code snippet, configuration, or architecture diagram if relevant]
```

**Components Affected**:
- [List files, modules, or services that will change]
- [Location references: `src/path/to/file.py`]

## Consequences

### Positive Consequences

- **[Benefit 1]**: Description of positive impact
- **[Benefit 2]**: Description of positive impact
- **[Benefit 3]**: Description of positive impact

[Focus on improvements in: reliability, performance, maintainability, security, scalability, developer experience]

### Negative Consequences

- **[Trade-off 1]**: Description of negative impact or limitation
- **[Trade-off 2]**: Description of negative impact or limitation

[Be honest about: added complexity, performance costs, limitations, migration effort, learning curve]

### Neutral Consequences

- **[Change 1]**: Description of neutral change
- **[Change 2]**: Description of neutral change

[Include: changes in workflow, different patterns, things that are just different not better/worse]

## Alternatives Considered

### Alternative 1: [Name of Alternative]

**Description**: Brief description of the alternative approach

**Pros**:
- Advantage 1
- Advantage 2
- Advantage 3

**Cons**:
- Disadvantage 1
- Disadvantage 2
- Disadvantage 3

**Why Rejected**: Clear reason why this wasn't chosen

---

### Alternative 2: [Name of Alternative]

**Description**: Brief description of the alternative approach

**Pros**:
- Advantage 1
- Advantage 2

**Cons**:
- Disadvantage 1
- Disadvantage 2

**Why Rejected**: Clear reason why this wasn't chosen

---

### Alternative 3: [Name of Alternative]

**Description**: Brief description of the alternative approach

**Pros**:
- Advantage 1
- Advantage 2

**Cons**:
- Disadvantage 1
- Disadvantage 2

**Why Rejected**: Clear reason why this wasn't chosen

---

## Related Decisions

- **Supersedes**: [ADR-XXXX - Title] (if replacing an old decision)
- **Relates to**: [ADR-XXXX - Title] (if connected to other decisions)
- **Requires**: [ADR-XXXX - Title] (if depends on other decisions)

## Implementation Notes

**Timeline**:
- Phase 1 (Week 1): [What gets done]
- Phase 2 (Week 2): [What gets done]
- Phase 3 (Week 3): [What gets done]

**Migration Strategy** (if replacing existing system):
1. [Step 1: How to transition]
2. [Step 2: How to maintain compatibility]
3. [Step 3: How to deprecate old approach]

**Testing Strategy**:
- Unit tests: [What to test]
- Integration tests: [What to test]
- Performance tests: [What to measure]

**Documentation Updates**:
- [ ] Update README.md
- [ ] Update API documentation
- [ ] Update deployment guides
- [ ] Create migration guide (if needed)
- [ ] Update architecture diagrams

**Success Criteria**:
- [How do we know this decision was successful?]
- [What metrics should we track?]
- [When should we revisit this decision?]

## References

**Internal**:
- [Link to design doc]
- [Link to spike/POC]
- [Link to related issues]

**External**:
- [Link to technology documentation]
- [Link to blog posts or articles]
- [Link to benchmarks or comparisons]

**Prior Art**:
- [How others solved similar problems]
- [Industry best practices]

---

## Template Usage Guide

### When to Create an ADR

Create an ADR when you need to document:
- **Architectural decisions**: Technology choices, patterns, frameworks
- **Design decisions**: API design, data models, interfaces
- **Process decisions**: Development workflows, testing strategies
- **Trade-off decisions**: Performance vs simplicity, flexibility vs complexity

### When NOT to Create an ADR

Don't create an ADR for:
- Routine bug fixes
- Minor refactoring
- Configuration changes
- Documentation updates

(Unless these involve significant trade-offs or set precedents)

### Numbering ADRs

1. Find the highest numbered ADR in `adr/` directory
2. Increment by 1 for your new ADR
3. Use 4-digit zero-padded format: `0025-title.md`

### Writing Tips

**Be Specific**:
- ❌ "Use a database"
- ✅ "Use PostgreSQL 15 with asyncpg driver for session storage"

**Focus on Why**:
- The decision itself is important, but WHY matters more
- Future developers need to understand the reasoning

**Be Honest**:
- Include negative consequences
- Document trade-offs clearly
- It's okay to say "we're not sure yet" in Status: Proposed

**Keep It Concise**:
- Aim for 1-2 pages
- Use bullet points
- Link to detailed design docs for deep dives

**Update Status**:
- Start with "Proposed" for discussion
- Move to "Accepted" when implemented
- Mark as "Deprecated" if no longer relevant
- Link to superseding ADR if replaced

---

## Quick Start Example

```markdown
# 25. Use Redis for Session Storage

Date: 2025-10-20

## Status

Accepted

## Context

Need persistent session storage for authentication tokens. In-memory storage
loses sessions on restart, causing users to re-login frequently.

Requirements:
- Persist across restarts
- Support TTL expiration
- Fast read/write (< 10ms p95)
- Handle 1000+ concurrent sessions

## Decision

We will use Redis for session storage via redis.asyncio.

## Consequences

### Positive

- **Reliability**: Sessions survive restarts
- **Performance**: Sub-millisecond operations
- **Scalability**: Can handle millions of sessions

### Negative

- **Dependency**: Requires Redis service
- **Cost**: Additional infrastructure

## Alternatives Considered

### Alternative 1: PostgreSQL
Why Rejected: Slower for this use case

### Alternative 2: In-Memory
Why Rejected: Data loss on restart
```

---

**Template Version**: 1.0
**Last Updated**: 2025-10-20
**Based On**: Project ADRs (adr/0001-0025)
