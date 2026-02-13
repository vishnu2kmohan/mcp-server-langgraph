---
name: deploy
description: Deploy mcp-server-langgraph to Kubernetes, GKE, Cloud Run, Helm, or Kustomize targets. Use when deploying the application to any environment.
allowed-tools:
  - Bash(docker build:*)
  - Bash(docker push:*)
  - Bash(kubectl get:*)
  - Bash(kubectl describe:*)
  - Bash(kubectl logs:*)
  - Bash(helm list:*)
  - Bash(helm status:*)
  - Bash(gcloud run services list:*)
  - Bash(gcloud run services describe:*)
  - Bash(gcloud container clusters list:*)
  - Bash(gcloud container clusters describe:*)
  - Bash(make:*)
  - Read
  - Glob
  - Grep
disable-model-invocation: true
context: fork
---
# Unified Deployment Command

You are tasked with deploying the mcp-server-langgraph application to various targets. This command provides a unified interface for deploying to Kubernetes, GKE, Cloud Run, Helm, and Kustomize.

## Deployment Context

**Available Targets**:
- **Kubernetes** (kubectl + Kustomize): GCP, Azure, AWS overlays
- **GKE Staging**: Google Kubernetes Engine (preview-gke overlay)
- **Cloud Run**: Google Cloud Run serverless
- **Helm**: Kubernetes package manager with dependencies
- **Kustomize Overlays**: dev, staging, production
- **LangGraph Platform**: LangGraph Cloud deployment

**Deployment Structure**:
```
deployments/
├── base/               # Base Kubernetes manifests
├── cloudrun/           # Cloud Run deployment
├── helm/               # Helm charts
├── kubernetes/         # K8s overlays (GCP, Azure, AWS)
├── overlays/           # Kustomize overlays (dev, staging, prod)
├── langgraph-platform/ # LangGraph Cloud
└── kong/               # Kong API Gateway
```

## Step 1: Gather Deployment Information

Ask the user using the AskUserQuestion tool:

**Question 1**: What is your deployment target?
- Header: "Target"
- Options:
  - Kubernetes (GCP): Deploy to GKE or GCP Kubernetes
  - Kubernetes (Azure): Deploy to AKS
  - Kubernetes (AWS): Deploy to EKS
  - GKE Staging: Staging environment on GKE
  - Cloud Run: Google Cloud Run serverless
  - Helm: Package manager deployment
  - Kustomize Overlay: Dev/Staging/Production overlay

**Question 2**: What environment?
- Header: "Environment"
- Options:
  - dev: Development environment
  - staging: Staging environment
  - production: Production environment

**Question 3**: Deployment mode?
- Header: "Mode"
- Options:
  - Full Deploy: Complete deployment with all dependencies
  - App Only: Deploy only the application (skip dependencies)
  - Dry Run: Show what would be deployed (no actual deployment)
  - Validate Only: Validate manifests without deploying

## Step 2: Pre-Deployment Validation

Before deploying, validate the environment.

> **On-demand**: Read [references/validation-checklist.md](references/validation-checklist.md) for the full pre-deployment validation checklist and commands.

Run environment checks, manifest validation, and dependency checks as documented in the validation reference.

## Step 3: Target-Specific Deployment

> **On-demand**: Read [references/platform-configs.md](references/platform-configs.md) for the complete deployment instructions for the selected target (Kubernetes GCP/Azure/AWS, GKE Staging, Cloud Run, Helm, Kustomize Overlays, or LangGraph Platform).

Execute the deployment steps for the target selected in Step 1.

## Step 4: Post-Deployment Verification

After deployment, verify the application is healthy.

> **On-demand**: Read [references/validation-checklist.md](references/validation-checklist.md) for the full post-deployment verification checklist, verification commands, and smoke tests.

Run health checks, dependency verification, observability checks, and smoke tests as documented in the validation reference.

## Step 5: Rollback (if needed)

If deployment fails, execute rollback procedures.

> **On-demand**: Read [references/rollback-procedures.md](references/rollback-procedures.md) for target-specific rollback commands, resource configurations, and error handling guidance.

## Step 6: Deployment Summary

Provide a summary after deployment using this template:

```
+------------------------------------------------------------------+
|              DEPLOYMENT SUMMARY                                    |
|              mcp-server-langgraph -> <Target>                      |
+------------------------------------------------------------------+
|  Target:           <target> (<region>)                             |
|  Environment:      <env>                                           |
|  Namespace:        mcp-server-langgraph                            |
|  Deployment Time:  <duration>                                      |
|  Status:           SUCCESS / FAILED                                |
+------------------------------------------------------------------+
|  Resources Deployed:                                               |
|    - Deployment:       mcp-server-langgraph (<ready>/<total>)      |
|    - Service:          mcp-server-langgraph (<type>)               |
|    - Ingress:          mcp-server-langgraph                        |
|    - HPA:              mcp-server-langgraph (<min>-<max> replicas) |
|    - ServiceAccount:   mcp-server-langgraph-sa                     |
|    - ExternalSecrets:  mcp-server-langgraph-secrets                |
+------------------------------------------------------------------+
|  Endpoints:                                                        |
|    - Internal:     mcp-server-langgraph.mcp-server-langgraph.svc   |
|    - External:     https://<env>.mcp.example.com                   |
|    - Health:       https://<env>.mcp.example.com/health            |
+------------------------------------------------------------------+
|  Verification:                                                     |
|    - All pods running (<ready>/<total>)                            |
|    - Health checks passing                                         |
|    - Dependencies connected (Redis, PostgreSQL, OpenFGA)           |
|    - Metrics exporting to Prometheus                               |
|    - Smoke tests passed                                            |
+------------------------------------------------------------------+
|  Next Steps:                                                       |
|    1. Monitor logs: kubectl logs -f -n mcp-server-langgraph        |
|    2. Check metrics: <grafana-url>                                 |
|    3. Run integration tests                                        |
|    4. Notify team of successful deployment                         |
+------------------------------------------------------------------+
```

## Integration with CI/CD

This command integrates with:
- `/ci-status` (skill) - Check CI/CD pipeline status before deploying
- `/pr-checks` - Validate PR before merge and deploy
- `/validate` - Run all validations pre-deployment
- `/test-all` - Run full test suite before deployment

## Notes

- Always validate in **dry-run** mode first
- Review resource quotas before production deployment
- Ensure secrets are properly configured
- Monitor deployment closely for first 15 minutes
- Have rollback plan ready
- Notify team of production deployments

## Success Criteria

- Deployment completed without errors
- All pods running and ready
- Health checks passing
- Dependencies connected
- Smoke tests passed
- Metrics and logs flowing
- Application accessible via endpoints
