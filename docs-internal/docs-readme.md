# Documentation Directory

This directory contains **user-facing documentation** for the MCP Server with LangGraph project, powered by [Mintlify](https://mintlify.com).

## 📚 What's Here

All files in this directory are in `.mdx` (Mintlify) format and represent the published documentation site.

```
docs/
├── getting-started/     # Getting started guides
├── api-reference/       # API documentation
├── guides/              # How-to guides and tutorials
├── deployment/          # Deployment and infrastructure guides
├── architecture/        # Architecture Decision Records (ADRs)
├── advanced/            # Advanced topics and patterns
├── development/         # Development and contribution guides
└── security/            # Security documentation
```

## 🚀 Quick Start

### Local Development

Run the Mintlify dev server from the **project root**:

```bash
# From project root
mintlify dev

# Opens at http://localhost:3000
```

### Adding New Pages

1. Create a new `.mdx` file in the appropriate subdirectory
2. Add the page reference to `../docs/docs.json` navigation
3. Restart `mintlify dev` to see changes

Example:
```mdx
---
title: "My New Page"
description: "A brief description"
---

# My New Page

Content goes here...
```

## 📝 Writing Guidelines

### File Naming
- Use lowercase with hyphens: `multi-llm-setup.mdx`
- Be descriptive but concise
- Match the navigation slug in `docs.json`

### Content Structure
```mdx
---
title: "Page Title"
description: "Brief description (shows in search)"
---

# Main Heading (h1)

Brief introduction paragraph.

## Section Heading (h2)

Content...

### Subsection (h3)

Details...
```

### Code Blocks
````mdx
```python
# Example code
def hello_world():
    print("Hello, world!")
```
````

### Components

Mintlify provides special components:

```mdx
<Note>
  Important information for users
</Note>

<Warning>
  Critical warnings
</Warning>

<Tip>
  Helpful tips and best practices
</Tip>

<Check>
  Success messages
</Check>
```

## 🗂️ What's NOT Here

The following content types are **not** in this directory:

- **Project Reports** → `../reports/`
- **ADR Source Files** → `../adr/`
- **Runbooks** → `../runbooks/`
- **Templates** → `../template/`
- **Reference Materials** → `../reference/`
- **Source Code** → `../src/`
- **Tests** → `../tests/`

## 🔧 Configuration

All Mintlify configuration is in `../docs/docs.json`:
- Navigation structure
- Theme and branding
- API endpoints
- External links
- Search settings

## 📖 Documentation Categories

### Getting Started
New users should start here. Includes:
- Introduction and overview
- Quickstart guide
- Installation instructions
- First API request tutorial

### API Reference
Complete API documentation:
- Authentication endpoints
- MCP protocol endpoints
- Health checks
- Error responses

### Guides
Step-by-step tutorials:
- Multi-LLM setup
- Provider configuration (Google, Anthropic, OpenAI)
- OpenFGA authorization
- Secrets management with Infisical

### Deployment
Infrastructure and deployment:
- LangGraph Platform deployment
- Google Cloud Run
- Kubernetes (GKE, EKS, AKS)
- Docker and Helm
- Production checklist

### Architecture
Design decisions and patterns:
- Architecture Decision Records (ADRs)
- System architecture overview
- Design patterns used

### Advanced
Deep dives and advanced topics:
- Custom authentication providers
- Advanced authorization patterns
- Performance optimization
- Troubleshooting guide

### Development
For contributors:
- Development setup
- Testing strategy
- Contributing guidelines
- Code standards

### Security
Security-related documentation:
- Security overview
- Best practices
- Audit checklist
- Compliance information

## 🚀 Deployment

Deploy documentation to Mintlify cloud:

```bash
# From project root
mintlify deploy
```

Or use the GitHub Actions workflow (`.github/workflows/mintlify.yml`)

## 📚 Learn More

- [Mintlify Documentation](https://mintlify.com/docs)
- [MDX Syntax](https://mdxjs.com/)
---

**Note:** This directory is for Mintlify documentation. All other documentation types should be placed in their respective directories (see the main [README.md](../README.md) for details).
