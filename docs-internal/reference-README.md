# Reference Documentation

This directory contains reference documentation for developers and contributors. Most content is published on the Mintlify documentation site.

## What's Here

### Development Reference (`development/`)

Developer-focused guides and technical references:
- `build-verification.mdx` - Build validation procedures
- `ci-cd/` - CI/CD pipeline reference (split into overview, workflows, testing, deployment, troubleshooting)
- `development.mdx` - Development workflow reference
- `github-actions.mdx` - GitHub Actions implementation details
- `ide-setup.mdx` - IDE configuration for contributors

**Note**: These development references are published in the Mintlify documentation site under the "Reference" section for developer access.

## What's NOT Here

**User-Facing Documentation** is in `docs/` as `.mdx` files and is published via Mintlify:
- Getting Started guides
- API Reference
- Deployment guides
- Architecture Decision Records (ADRs)
- Guides (LLM setup, authorization, secrets management)

## Organization Policy

- **Mintlify docs** (`.mdx` in `docs/`): User-facing, published documentation
- **Reference docs** (`.md` in `docs/reference/`): Internal, contributor-focused documentation
- **Operational docs** (`.md` in `docs/deployment/`): version-compatibility.md, version-pinning.md, model-configuration.md
- **Status docs** (`.md` at root level): CHANGELOG.md, SECURITY.md, VERSION_PINNING_REMEDIATION.md

See `../../README.md` for complete documentation organization strategy.
