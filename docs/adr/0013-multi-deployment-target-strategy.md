# 13. Multi-Deployment Target Strategy

Date: 2025-10-13

## Status

Accepted

## Context

Users deploy to diverse platforms:
- **Kubernetes** (GKE, EKS, AKS)
- **Cloud Run** (serverless)
- **Docker** (self-hosted)
- **Docker Compose** (local dev)

Single deployment approach limits adoption:
- K8s-only excludes serverless users
- Docker-only excludes enterprise K8s users

## Decision

Support **multiple deployment targets** with platform-specific optimizations.

### Deployment Options

1. **Docker Compose**: Local development
2. **kubectl**: Basic Kubernetes
3. **Kustomize**: Multi-environment K8s
4. **Helm**: Enterprise K8s
5. **Cloud Run**: Google serverless
6. **LangGraph Platform**: Managed service

## Consequences

### Positive

- **Flexibility**: Users choose best platform
- **Broad Adoption**: Supports all major platforms
- **Best Practices**: Platform-specific optimizations

### Negative

- **Maintenance Burden**: 7 deployment configs to maintain
- **Testing Complexity**: Must test all platforms
- **Documentation**: More docs required

## References

- Deployments: `deployments/` (7 types)
- Documentation: `deployments/README.md`, `deployments/QUICKSTART.md`
