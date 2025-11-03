# AKS Terraform Module - Foundational

**Status**: 🚧 **In Development** - Foundational structure established

This is a foundational AKS module that establishes the pattern for Azure Kubernetes Service automation.

## Current State

This module provides the basic structure but requires completion of:
- [ ] Main AKS cluster resource definitions
- [ ] Node pool configurations
- [ ] Azure AD integration
- [ ] Network policy settings
- [ ] Monitoring integration
- [ ] Managed identity configurations

## Planned Features

- AKS cluster with Azure CNI networking
- System and user node pools
- Azure AD pod identity
- Azure Monitor integration
- Azure Policy integration
- Private cluster support

## Contributing

This module is a work in progress. Contributions welcome! See the GKE and EKS modules for reference patterns.

## Manual Deployment

Until this module is complete, use the manual deployment guide:
- [AKS Manual Deployment](../../../../docs/deployment/kubernetes/aks.mdx)
- [Azure CLI Setup](../../../../scripts/deploy-azure-aks.sh)
