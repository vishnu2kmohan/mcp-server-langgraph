# Reference Documentation

This directory contains internal reference documentation that is **not** part of the Mintlify user-facing documentation site.

## What's Here

### Development Reference (`development/`)

Internal development guides and processes:
- `build-verification.md` - Build validation procedures
- `ci-cd.md` - CI/CD pipeline internals
- `development.md` - Development workflow reference
- `github-actions.md` - GitHub Actions implementation details
- `ide-setup.md` - IDE configuration for contributors

These are maintained for internal reference but are not included in the public documentation site at docs.

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
- **Operational docs** (`.md` in `docs/deployment/`): VERSION_COMPATIBILITY.md, VERSION_PINNING.md, model-configuration.md
- **Status docs** (`.md` at root level): CHANGELOG.md, SECURITY.md, VERSION_PINNING_REMEDIATION.md

See `../../README.md` for complete documentation organization strategy.
