# Documentation Authoring Guide

**Last Updated**: 2025-11-04
**Purpose**: Establish clear documentation standards and prevent content drift

---

## Documentation Philosophy

**Single Source of Truth**: Every piece of user-facing documentation should exist in exactly one canonical location.

**Discoverability First**: If documentation isn't linked from Mintlify navigation (`docs.json`), most users will never find it.

---

## File Format Policy

### ✅ USE .mdx for User-Facing Documentation

**Location**: `docs/**/*.mdx` (registered in `docs/docs.json`)

**When to use**:
- Getting started guides
- API documentation
- Deployment guides
- Architecture documentation
- Tutorials and examples
- Troubleshooting guides
- Security and compliance docs

**Requirements**:
1. **Frontmatter** (required):
   ```yaml
   ---
   title: "Page Title"
   sidebarTitle: "Short Title"  # optional, for sidebar
   description: "SEO-friendly description (140-160 chars recommended)"
   icon: "lucide-icon-name"  # See ICON_GUIDE.md
   ---
   ```

2. **Navigation** (required):
   - Must be registered in `docs/docs.json`
   - Place in appropriate tab and group
   - Use logical ordering

3. **Links** (required):
   - Use Mintlify-style paths: `/getting-started/introduction`
   - NOT relative paths: `../getting-started/introduction.md`
   - NOT file extensions: `/getting-started/introduction` (not `.mdx`)

4. **Special Characters** (required):
   - Escape `<` as `&lt;` in tables and text
   - Escape `>` as `&gt;` in tables and text
   - Escape `&` as `&amp;` if not part of HTML entity

---

### ⚠️ USE .md ONLY for Internal/Operational Files

**Allowed .md files**:
- `docs/reference/*.md` - Internal contributor documentation
- `docs/ci-cd/badges.md` - Operational status badges
- `docs/architecture/infrastructure-layer.md` - Internal implementation notes
- Root-level files: `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`

**NOT allowed**:
- User-facing guides in .md format
- Duplicates of .mdx files
- Documentation that should be in Mintlify

---

## Directory Structure

```
docs/
├── .mintlify/              # Mintlify configuration and guides
│   ├── AUTHORING_GUIDE.md  # This file
│   ├── ICON_GUIDE.md       # Icon reference
│   └── templates/          # Document templates
│
├── getting-started/        # New user onboarding
├── guides/                 # Task-oriented tutorials
├── api-reference/          # API documentation
├── deployment/             # Deployment guides
│   ├── advanced/           # Advanced deployment topics
│   ├── kubernetes/         # Kubernetes-specific guides
│   └── operations/         # Operations and maintenance
│
├── ci-cd/                  # CI/CD documentation
├── architecture/           # Architecture decisions (ADRs)
├── security/               # Security documentation
├── comparisons/            # Framework comparisons
├── advanced/               # Advanced topics
│
├── reference/              # Internal contributor docs (.md)
└── docs.json               # Mintlify navigation config
```

---

## Common Mistakes to Avoid

### ❌ DON'T: Create Duplicate Documentation

```
❌ docs/quickstart.md
❌ docs/getting-started/quickstart.mdx
```

**Why**: Creates content drift, confusion about source of truth

**Fix**: Keep only the .mdx version in the appropriate location

---

### ❌ DON'T: Forget Frontmatter

```mdx
# My Guide

This guide explains...
```

**Why**: Mintlify won't render metadata, icons, or SEO correctly

**Fix**: Always start with proper frontmatter
```mdx
---
title: "My Guide"
description: "Brief description"
icon: "book"
---

# My Guide

This guide explains...
```

---

### ❌ DON'T: Use File Extensions in Links

```mdx
See [Authentication](../getting-started/authentication.mdx)
```

**Why**: Mintlify routing doesn't use file extensions

**Fix**: Use path-style links
```mdx
See [Authentication](/getting-started/authentication)
```

---

### ❌ DON'T: Forget to Register in docs.json

Even if the file exists, it won't be accessible unless it's in `docs.json`:

```json
{
  "group": "Getting Started",
  "pages": [
    "getting-started/introduction",
    "getting-started/quickstart"  // ← Must be here!
  ]
}
```

---

### ❌ DON'T: Use `<` or `>` Unescaped

```mdx
| Deployment Frequency | <1 hour |  ❌ BREAKS
```

**Why**: MDX interprets `<` as start of JSX tag

**Fix**: Use HTML entities
```mdx
| Deployment Frequency | &lt;1 hour |  ✅ WORKS
```

---

## Creating New Documentation

### Step 1: Choose the Right Location

```
User guide? → docs/guides/your-guide.mdx
API docs? → docs/api-reference/your-endpoint.mdx
Deployment? → docs/deployment/your-topic.mdx
Internal? → docs/reference/your-notes.md
```

### Step 2: Use a Template

```bash
# Copy appropriate template
cp docs/.mintlify/templates/guide-template.mdx docs/guides/my-guide.mdx
```

Available templates:
- `adr-template.mdx` - Architecture Decision Records
- `guide-template.mdx` - How-to guides
- `deployment-template.mdx` - Deployment guides
- `reference-template.mdx` - API reference

### Step 3: Add Frontmatter

```yaml
---
title: "Clear, Descriptive Title"
sidebarTitle: "Short Title"  # Optional, for long titles
description: "What this page helps users accomplish"
icon: "appropriate-lucide-icon"  # See ICON_GUIDE.md
---
```

### Step 4: Write Content

- **Start with context**: Why does this page exist?
- **Use headings**: Organize with ##, ###, ####
- **Add examples**: Code blocks with syntax highlighting
- **Link related docs**: Help users navigate
- **Test locally**: Run `mintlify dev` to preview

### Step 5: Register in docs.json

```json
{
  "group": "Your Group",
  "pages": [
    "path/to/existing",
    "path/to/your-new-doc"  // ← Add here
  ]
}
```

### Step 6: Validate

```bash
cd docs

# Check for broken links
mintlify broken-links

# Preview locally
mintlify dev
```

---

## Migration Policy

When converting .md to .mdx:

1. ✅ **Read the original** `.md` file
2. ✅ **Add frontmatter** with appropriate metadata
3. ✅ **Preserve all content** exactly as-is
4. ✅ **Fix any `<`/`>` escaping** issues in tables
5. ✅ **Update internal links** to Mintlify format
6. ✅ **Register in docs.json** at appropriate location
7. ✅ **Delete the original** `.md` file
8. ✅ **Run validation**: `mintlify broken-links`

---

## Link Formatting

### Internal Links (Within Docs)

```mdx
✅ [Getting Started](/getting-started/introduction)
✅ [API Reference](/api-reference/sdk-quickstart)
❌ [Getting Started](../getting-started/introduction.md)
❌ [Getting Started](./getting-started/introduction.mdx)
```

### External Links

```mdx
✅ [GitHub Repo](https://github.com/vishnu2kmohan/mcp-server-langgraph)
✅ [Contributing](https://github.com/vishnu2kmohan/mcp-server-langgraph/blob/main/CONTRIBUTING.md)
```

### Anchor Links

```mdx
✅ [Jump to Section](#section-heading)
✅ [Prerequisites](/deployment/kubernetes#prerequisites)
```

---

## Icon Selection

See [`ICON_GUIDE.md`](./ICON_GUIDE.md) for comprehensive icon reference.

**Common icons**:
- `rocket` - Getting started, quickstart
- `book` - Guides, tutorials
- `code` - API, SDK
- `server` - Deployment, infrastructure
- `shield` - Security
- `chart-line` - Metrics, observability
- `infinity` - CI/CD
- `cloud` - Cloud providers

---

## Content Quality Standards

### Writing Style

- **Be concise**: Respect reader's time
- **Be specific**: "Run `make test`" not "Run tests"
- **Be actionable**: Focus on "how" more than "what"
- **Be consistent**: Use same terminology throughout

### Code Examples

```mdx
## Good Example

\`\`\`bash
# Install dependencies
uv sync --extra dev

# Run tests
make test-unit
\`\`\`

## What It Does
This installs development dependencies and runs unit tests.
```

### Screenshots/Diagrams

- **Prefer Mermaid** for diagrams (see `MERMAID_OPTIMIZATION_GUIDE.md`)
- **Optimize images**: Compress before committing
- **Add alt text**: For accessibility

---

## Pre-Commit Checklist

Before committing documentation changes:

- [ ] Frontmatter complete and accurate
- [ ] Added to `docs.json` navigation
- [ ] All `<` and `>` escaped in tables
- [ ] Internal links use Mintlify format (`/path/to/page`)
- [ ] No duplicate .md version exists
- [ ] Ran `mintlify broken-links` (no errors)
- [ ] Tested with `mintlify dev` (renders correctly)
- [ ] Spell-checked and grammar-checked

---

## Troubleshooting

### "Syntax error - Unable to parse"

**Cause**: Unescaped `<` or `>` characters

**Fix**: Replace with `&lt;` or `&gt;`

### "Page not found" in Mintlify

**Cause**: Not registered in `docs.json`

**Fix**: Add page path to appropriate group in `docs.json`

### "Broken link" warning

**Cause**: Link uses wrong format or points to non-existent page

**Fix**:
- Use `/path/to/page` format (no extension)
- Verify target page exists and is in `docs.json`

---

## Maintenance

### Weekly
- Review new documentation PRs for compliance
- Check `mintlify broken-links` output

### Monthly
- Audit for orphaned .md files
- Review docs.json for logical organization
- Update this guide as patterns emerge

---

## Getting Help

- **Icon reference**: See [`.mintlify/ICON_GUIDE.md`](./ICON_GUIDE.md)
- **Mermaid diagrams**: See [`.mintlify/MERMAID_OPTIMIZATION_GUIDE.md`](./MERMAID_OPTIMIZATION_GUIDE.md)
- **Templates**: See [`.mintlify/templates/`](./templates/)
- **Mintlify docs**: https://mintlify.com/docs
- **Questions?**: Open issue with label `documentation`

---

**Remember**: User-facing documentation belongs in .mdx files registered in docs.json. Everything else is an exception that should be justified.
