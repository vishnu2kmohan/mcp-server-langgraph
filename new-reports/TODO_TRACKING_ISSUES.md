# TODO Comments Requiring GitHub Issues

Generated: 2025-10-20
Part of: Comprehensive Codebase Cleanup Initiative

This document tracks TODO comments in the source code that should be converted to GitHub issues for proper tracking and prioritization.

---

## Storage Backend Integration TODOs

### Priority: Medium | Area: Compliance | Effort: High

These TODOs are deferred architectural decisions requiring storage backend implementation:

#### 1. Conversation Storage Integration
**File**: `src/mcp_server_langgraph/core/compliance/retention.py:330`
```python
# TODO: Integrate with actual conversation storage backend
```

**Description**: Data retention policy needs integration with conversation storage.

**Proposed Issue**:
```
Title: Integrate conversation storage backend with retention policy
Labels: enhancement, compliance, storage
Priority: Medium
Effort: High

## Description
The retention policy in `retention.py` has a placeholder for conversation
storage integration. Need to implement actual backend connection.

## Context
- File: src/mcp_server_langgraph/core/compliance/retention.py:330
- Related: Data retention requirements (GDPR, compliance)

## Tasks
- [ ] Design conversation storage schema
- [ ] Implement storage backend adapter
- [ ] Integrate with retention policy
- [ ] Add tests for storage integration
- [ ] Document storage configuration
```

---

#### 2. Audit Log Storage Integration
**File**: `src/mcp_server_langgraph/core/compliance/retention.py:353`
```python
# TODO: Integrate with actual audit log storage and cold storage backend
```

**Description**: Audit log retention needs integration with storage and cold storage.

**Proposed Issue**:
```
Title: Integrate audit log storage with cold storage backend
Labels: enhancement, compliance, storage, audit
Priority: Medium
Effort: High

## Description
Audit log retention policy requires integration with:
1. Primary audit log storage
2. Cold storage backend for archival

## Context
- File: src/mcp_server_langgraph/core/compliance/retention.py:353
- Related: SOC 2 compliance, audit trail requirements

## Tasks
- [ ] Design audit log storage schema
- [ ] Implement cold storage adapter (S3, Glacier, etc.)
- [ ] Define archival policy (hot → cold transition)
- [ ] Integrate with retention policy
- [ ] Add tests for storage tiers
- [ ] Document audit log lifecycle
```

---

#### 3. Audit Log Deletion Integration
**File**: `src/mcp_server_langgraph/core/compliance/data_deletion.py:325`
```python
# TODO: Integrate with audit log storage
```

**Description**: GDPR data deletion needs audit log storage integration.

**Proposed Issue**:
```
Title: Integrate GDPR data deletion with audit log storage
Labels: enhancement, gdpr, compliance, storage
Priority: High (GDPR requirement)
Effort: Medium

## Description
The GDPR data deletion handler needs to integrate with audit log storage
to properly delete or anonymize user data from audit logs.

## Context
- File: src/mcp_server_langgraph/core/compliance/data_deletion.py:325
- Related: GDPR Article 17 (Right to Erasure)

## Tasks
- [ ] Define audit log deletion/anonymization strategy
- [ ] Implement audit log storage adapter
- [ ] Handle retention policy conflicts (legal vs. GDPR)
- [ ] Add deletion verification
- [ ] Test with real audit log backend
- [ ] Document deletion process
```

---

## Script Implementation TODOs

### Priority: Low | Area: Tooling | Effort: Low

These are workflow automation features that can be implemented incrementally:

#### 4. Test Pattern Documentation Update
**File**: `scripts/workflow/analyze-test-patterns.py:253`
```python
# TODO: Implement pattern documentation update
```

**Description**: Script should auto-update test pattern documentation.

**Proposed Issue**:
```
Title: Implement auto-update for test pattern documentation
Labels: enhancement, tooling, documentation
Priority: Low
Effort: Low

## Description
The analyze-test-patterns.py script should automatically update
test pattern documentation when new patterns are detected.

## Context
- File: scripts/workflow/analyze-test-patterns.py:253
- Related: Test organization, documentation automation

## Tasks
- [ ] Design documentation update format
- [ ] Implement Markdown generation
- [ ] Add pattern categorization
- [ ] Test with existing patterns
- [ ] Document usage in script help
```

---

#### 5. TODO Catalog Update Logic
**File**: `scripts/workflow/todo-tracker.py:314`
```python
# TODO: Implement catalog update logic
```

**Description**: TODO tracker should update TODO catalog automatically.

**Proposed Issue**:
```
Title: Implement automatic TODO catalog updates
Labels: enhancement, tooling
Priority: Low
Effort: Low

## Description
The todo-tracker.py script should automatically update the TODO catalog
when scanning for TODOs in the codebase.

## Context
- File: scripts/workflow/todo-tracker.py:314
- Related: TODO management, project tracking

## Tasks
- [ ] Design catalog format (Markdown table)
- [ ] Implement catalog update logic
- [ ] Group TODOs by priority/area
- [ ] Add last updated timestamp
- [ ] Test with current TODOs
```

---

#### 6. Sprint File Update Logic
**File**: `scripts/workflow/generate-progress-report.py:298`
```python
# TODO: Implement sprint file update logic
```

**Description**: Progress report generator should update sprint tracking files.

**Proposed Issue**:
```
Title: Implement sprint file auto-update in progress reports
Labels: enhancement, tooling, workflow
Priority: Low
Effort: Low

## Description
The generate-progress-report.py script should automatically update
sprint tracking files when generating progress reports.

## Context
- File: scripts/workflow/generate-progress-report.py:298
- Related: Sprint planning, project management

## Tasks
- [ ] Design sprint file format
- [ ] Implement update logic
- [ ] Add progress tracking
- [ ] Test with sample sprint data
- [ ] Document in workflow guide
```

---

## Test Implementation TODOs

### Priority: Medium | Area: Testing | Effort: Medium

#### 7. GDPR Endpoint Tests with Auth Mocking
**File**: `tests/test_gdpr.py:291-319` (8 test methods)
```python
def test_get_user_data(self, client):
    pass  # TODO: Implement with auth mocking
```

**Test Methods Requiring Implementation**:
1. `test_get_user_data` (line 291)
2. `test_export_user_data_json` (line 295)
3. `test_export_user_data_csv` (line 299)
4. `test_update_user_profile` (line 303)
5. `test_delete_user_account` (line 307)
6. `test_delete_user_account_without_confirmation` (line 311)
7. `test_update_consent` (line 315)
8. `test_get_consent_status` (line 319)

**Proposed Issue**:
```
Title: Implement GDPR API endpoint tests with auth mocking
Labels: testing, gdpr, compliance
Priority: Medium
Effort: Medium

## Description
Eight GDPR API endpoint tests are currently stubs. Need to implement
with proper authentication mocking infrastructure.

## Context
- File: tests/test_gdpr.py:291-319
- Related: GDPR compliance, API testing

## Tests to Implement
- [ ] test_get_user_data
- [ ] test_export_user_data_json
- [ ] test_export_user_data_csv
- [ ] test_update_user_profile
- [ ] test_delete_user_account
- [ ] test_delete_user_account_without_confirmation
- [ ] test_update_consent
- [ ] test_get_consent_status

## Prerequisites
- [ ] Set up auth mocking infrastructure
- [ ] Create test user fixtures
- [ ] Define expected API responses

## Tasks
- [ ] Implement auth mocking helper
- [ ] Implement each test method
- [ ] Add negative test cases (unauthorized, etc.)
- [ ] Verify GDPR compliance in tests
- [ ] Document test patterns
```

---

#### 8. Concurrent Deletion Test
**File**: `tests/test_gdpr.py:502`
```python
# TODO: Implement test for concurrent deletion
```

**Proposed Issue**:
```
Title: Implement concurrent deletion test for GDPR compliance
Labels: testing, gdpr, concurrency
Priority: Low
Effort: Medium

## Description
Add test for concurrent deletion scenarios to ensure GDPR data deletion
is safe under concurrent access.

## Context
- File: tests/test_gdpr.py:502
- Related: Race conditions, data integrity

## Tasks
- [ ] Design concurrent deletion scenario
- [ ] Implement test using threading/asyncio
- [ ] Verify deletion atomicity
- [ ] Test with multiple concurrent requests
- [ ] Document concurrency guarantees
```

---

#### 9. MCP Contract Tests
**File**: `tests/contract/test_mcp_contract.py:247, 255, 263`
```python
# TODO: Implement when server fixture is available
```

**Three test methods needing server fixture**:
1. Line 247 - Test method TBD
2. Line 255 - Test method TBD
3. Line 263 - Test method TBD

**Proposed Issue**:
```
Title: Implement MCP contract tests with server fixture
Labels: testing, mcp, contract-testing
Priority: Medium
Effort: Medium

## Description
Three MCP contract tests are blocked waiting for server fixture
implementation.

## Context
- File: tests/contract/test_mcp_contract.py:247, 255, 263
- Related: MCP protocol compliance

## Prerequisites
- [ ] Implement server fixture in conftest.py
- [ ] Define MCP server lifecycle for tests

## Tasks
- [ ] Implement server fixture
- [ ] Implement pending contract tests
- [ ] Verify MCP protocol compliance
- [ ] Add fixture documentation
```

---

#### 10. Performance Regression Test - LLM Mocking
**File**: `tests/regression/test_performance_regression.py:150`
```python
# TODO: Implement proper LLM mocking that works with LangGraph checkpointing
```

**Proposed Issue**:
```
Title: Implement LLM mocking compatible with LangGraph checkpointing
Labels: testing, performance, langgraph
Priority: Low
Effort: High

## Description
Performance regression tests need proper LLM mocking that works with
LangGraph's checkpointing mechanism.

## Context
- File: tests/regression/test_performance_regression.py:150
- Challenge: LangGraph checkpointing requires specific mock structure

## Tasks
- [ ] Research LangGraph checkpointing requirements
- [ ] Design compatible LLM mock
- [ ] Implement mock with checkpoint support
- [ ] Test with existing regression tests
- [ ] Document mocking patterns for LangGraph
```

---

## Summary

### By Priority
- **High**: 1 issue (GDPR audit log deletion)
- **Medium**: 5 issues (storage integration, GDPR tests, MCP tests)
- **Low**: 4 issues (script features, concurrent deletion, LLM mocking)

### By Area
- **Compliance/Storage**: 3 issues
- **Testing**: 4 issues
- **Tooling/Scripts**: 3 issues

### By Effort
- **High**: 4 issues (storage backends, LLM mocking)
- **Medium**: 3 issues (GDPR tests, concurrent deletion, MCP tests)
- **Low**: 3 issues (script features)

---

## Next Steps

1. **Create GitHub Issues**: Use `gh issue create` or GitHub web interface
2. **Link in Code**: Update TODO comments with issue numbers
3. **Prioritize**: Schedule high-priority items (GDPR) first
4. **Track**: Add to project board/milestone

---

## Automation

To automatically create these issues:

```bash
# Example using gh CLI
gh issue create \
  --title "Integrate conversation storage backend with retention policy" \
  --body "$(cat issue_body.md)" \
  --label "enhancement,compliance,storage" \
  --milestone "v2.9.0"
```

Or use the GitHub web interface and copy the proposed issue templates above.

---

**Generated by**: Comprehensive Codebase Cleanup Analysis
**Date**: 2025-10-20
**Related**: Cleanup commit series starting with `feat(workflow): add Claude Code workflow automation`
