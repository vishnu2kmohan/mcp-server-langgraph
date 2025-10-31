# Project Knowledge Search

You are tasked with searching the project knowledge base for relevant information. This command provides semantic search across code, documentation, ADRs, and context files.

## Knowledge Base Context

**Sources**:
- **Code**: All Python source files
- **Documentation**: ADRs, guides, API docs
- **Context**: Testing patterns, code patterns, recent work
- **Git History**: Commit messages and changes
- **Templates**: Sprint planning, ADRs, bug investigation

**Total Knowledge**: ~220 Python files, 39 ADRs, 400+ tests, 100+ commits

## Your Task

### Step 1: Gather Search Query

Ask the user what they're looking for:

**Question**: What would you like to search for?
- Header: "Search Query"
- Provide text input
- Examples:
  - "How do we handle authentication?"
  - "What's our caching strategy?"
  - "Examples of property-based tests"
  - "How to deploy to GKE?"

### Step 2: Determine Search Scope

Based on the query, determine where to search:

**Search Scopes**:
1. **Code** - Source files in `src/`
2. **Tests** - Test files in `tests/`
3. **Documentation** - ADRs, guides in `docs/`
4. **Context** - `.claude/context/` files
5. **All** - Search everywhere

**Query-to-Scope Mapping**:
- Authentication/Authorization → Code + ADRs
- Testing patterns → Tests + Context
- Deployment → Documentation + Scripts
- Configuration → Code + ADRs
- Error handling → Code + Context

### Step 3: Execute Search

**Search Strategy**:

```bash
# 1. Grep for exact matches
grep -r "<query>" <scope>/ -l

# 2. Grep for case-insensitive matches
grep -ri "<query>" <scope>/ -l -n

# 3. Search related terms (synonyms)
# Example: "cache" → also search "redis", "session", "store"

# 4. Search ADRs specifically
grep -r "<query>" adr/ docs/architecture/ -l

# 5. Search code patterns
grep -r "class.*<query>" src/ -n
grep -r "def.*<query>" src/ -n
```

### Step 4: Rank and Filter Results

**Ranking Criteria**:
1. **Relevance**: Exact match > Partial match > Related term
2. **Recency**: Recent files > Old files (check git log)
3. **Importance**: ADRs > Code > Tests > Utils
4. **Usage**: Frequently referenced > Rarely referenced

**Filter Out**:
- Generated files (migrations, __pycache__)
- Third-party code
- Irrelevant matches

### Step 5: Present Results

**Result Format**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KNOWLEDGE SEARCH: "<query>"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Found: 15 results across 4 categories

  📋 Architecture Decisions (3 results)
  ──────────────────────────────────────────────────────────────────
  1. ADR-0002: OpenFGA Authorization
     Location: adr/adr-0002-openfga-authorization.md:45
     Context: "Fine-grained authorization using OpenFGA..."
     Relevance: ★★★★★ (exact match)

  2. ADR-0007: Authentication Provider Pattern
     Location: adr/adr-0007-authentication-provider-pattern.md:23
     Context: "Abstract authentication to support multiple providers..."
     Relevance: ★★★★☆ (related)

  3. ADR-0031: Keycloak Authoritative Identity
     Location: adr/adr-0031-keycloak-authoritative-identity.md:67
     Context: "Keycloak as the single source of truth for identity..."
     Relevance: ★★★☆☆ (related)

  💻 Code Implementation (5 results)
  ──────────────────────────────────────────────────────────────────
  1. src/mcp_server_langgraph/auth/middleware.py:145
     Code: class AuthMiddleware:
           """JWT authentication middleware"""
     Relevance: ★★★★★ (exact match)

  2. src/mcp_server_langgraph/auth/rbac.py:67
     Code: async def check_permission(self, user_id, resource, action):
           """Check user permission via OpenFGA"""
     Relevance: ★★★★★ (exact match)

  3. src/mcp_server_langgraph/auth/jwt.py:23
     Code: def encode_jwt(username: str, expiration: int) -> str:
           """Encode JWT token"""
     Relevance: ★★★★☆ (related)

  🧪 Tests & Examples (4 results)
  ──────────────────────────────────────────────────────────────────
  1. tests/unit/test_auth_middleware.py:89
     Test: test_jwt_authentication_success
     Coverage: Shows successful JWT flow
     Relevance: ★★★★☆ (example)

  2. tests/integration/test_auth_flow.py:145
     Test: test_end_to_end_authentication
     Coverage: Complete auth workflow
     Relevance: ★★★★☆ (example)

  📚 Context & Patterns (3 results)
  ──────────────────────────────────────────────────────────────────
  1. .claude/context/code-patterns.md:234
     Pattern: Authentication Middleware Pattern
     Usage: How to implement auth middleware
     Relevance: ★★★★★ (pattern guide)

  2. .claude/context/testing-patterns.md:567
     Pattern: Mocking Auth in Tests
     Usage: How to test auth components
     Relevance: ★★★★☆ (testing guide)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 6: Provide Context Snippets

For top 3-5 results, provide code/text snippets:

**Example**:
```python
# From: src/mcp_server_langgraph/auth/middleware.py:145

class AuthMiddleware:
    """
    JWT authentication middleware for FastAPI.

    Validates JWT tokens and extracts user information.
    Supports multiple authentication providers via provider pattern.

    See ADR-0007 for authentication strategy.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    async def authenticate(self, token: str) -> User:
        """
        Authenticate user from JWT token.

        Args:
            token: JWT token string

        Returns:
            User object with username, roles, permissions

        Raises:
            AuthenticationError: If token invalid or expired
        """
        # Implementation...
```

### Step 7: Suggest Related Searches

Based on results, suggest related queries:

**Related Searches**:
```
Based on your search for "authentication", you might also want to explore:

1. 🔐 Authorization
   Query: "OpenFGA permission checking"
   Reason: Authentication often works with authorization

2. 🔑 Session Management
   Query: "session storage Redis"
   Reason: Auth tokens stored in sessions

3. 🌐 API Security
   Query: "Kong JWT validation"
   Reason: Kong validates JWTs at API gateway

4. 🧪 Auth Testing
   Query: "mock authentication tests"
   Reason: How to test auth components

5. 📋 Security ADRs
   Command: grep -l "security\|auth" adr/*.md
   Reason: All security-related decisions
```

## Advanced Search Features

### Semantic Search (Query Expansion)

Automatically expand queries with related terms:

**Examples**:
- "cache" → ["cache", "redis", "session", "store", "memoiz"]
- "test" → ["test", "pytest", "unit", "integration", "mock"]
- "deploy" → ["deploy", "kubernetes", "helm", "k8s", "gke"]
- "auth" → ["auth", "jwt", "keycloak", "rbac", "permission"]

### Time-Based Search

Search by recency:

```bash
# Files modified in last 7 days mentioning "auth"
git log --since="7 days ago" --name-only | grep "auth" | sort -u

# Recent commits about authentication
git log --all --grep="auth" --since="1 month ago"
```

### Dependency Search

Find what depends on a module:

```bash
# Find all imports of auth.middleware
grep -r "from.*auth.*middleware import" src/ tests/

# Find all files that use OpenFGA
grep -r "openfga" src/ -l
```

### Pattern Search

Search for code patterns:

```bash
# Find all async functions
grep -r "async def" src/ -n

# Find all pytest fixtures
grep -r "@pytest.fixture" tests/ -n

# Find all data classes
grep -r "@dataclass" src/ -n

# Find all FastAPI routes
grep -r "@app\.(get|post|put|delete)" src/ -n
```

## Search Index

**Maintain a searchable index** (optional optimization):

```json
{
  "topics": {
    "authentication": {
      "adrs": ["ADR-0007", "ADR-0031"],
      "code": ["src/mcp_server_langgraph/auth/middleware.py"],
      "tests": ["tests/unit/test_auth_middleware.py"],
      "keywords": ["jwt", "keycloak", "token", "login"]
    },
    "caching": {
      "adrs": ["ADR-0028"],
      "code": ["src/mcp_server_langgraph/session/store.py"],
      "keywords": ["redis", "cache", "session", "ttl"]
    }
  }
}
```

## Example Searches

### Example 1: "How do we handle errors?"

**Search**:
```bash
grep -r "error\|exception" adr/ -l
grep -r "class.*Error" src/ -n
grep -r "raise " src/ -n | head -20
```

**Results**:
- ADR-0017: Error Handling Strategy
- ADR-0029: Custom Exception Hierarchy
- src/mcp_server_langgraph/core/exceptions.py
- 45+ error classes defined

### Example 2: "Property testing examples"

**Search**:
```bash
grep -r "@given\|hypothesis" tests/ -l
cat .claude/context/testing-patterns.md | grep -A 30 "Property"
```

**Results**:
- tests/property/*.py (27 tests)
- .claude/context/testing-patterns.md section on Hypothesis
- Examples of property-based testing patterns

### Example 3: "Deployment to GKE"

**Search**:
```bash
grep -r "gke\|GKE" docs/ deployments/ -l
cat docs/deployment/kubernetes.mdx
ls deployments/overlays/staging-gke/
```

**Results**:
- docs/deployment/gke-staging-implementation-summary.mdx
- deployments/overlays/staging-gke/ (complete config)
- ADR-0013: Multi-Deployment Target Strategy

## Integration with Existing Commands

**Related Commands**:
- `/docs-audit` - Find missing documentation
- `/create-adr` - Create new ADR for missing topics
- `/create-test` - Create tests for found code

## Notes

- **Fast searches**: Use grep/ripgrep for speed
- **Comprehensive**: Check code, docs, tests, ADRs
- **Contextual**: Provide code snippets, not just filenames
- **Related**: Suggest follow-up searches
- **Index**: Can maintain search index for faster lookups

---

**Success Criteria**:
- ✅ Query understood and expanded
- ✅ Multiple sources searched
- ✅ Results ranked by relevance
- ✅ Context snippets provided
- ✅ Related searches suggested
- ✅ Fast execution (< 5 seconds)
