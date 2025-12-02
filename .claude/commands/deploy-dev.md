---
description: Execute the complete development deployment workflow.
---
# Deploy to Development Environment

Execute the complete development deployment workflow.

## Prerequisites Check

1. Verify Kubernetes context is set to development cluster
2. Check that all environment variables are configured
3. Ensure Docker images are built

## Deployment Steps

1. **Validate Configurations**
   ```bash
   make validate-deployments
   ```

2. **Deploy to Development**
   ```bash
   make deploy-dev
   ```

3. **Verify Deployment**
   - Check pod status
   - View logs for any errors
   - Run health checks

4. **Post-Deployment**
   ```bash
   make health-check
   ```

## Troubleshooting

If deployment fails:
- Check pod events: `kubectl get events -n langgraph-agent-dev`
- View pod logs: `kubectl logs -f deployment/dev-langgraph-agent -n langgraph-agent-dev`
- Review configuration: `kubectl describe deployment dev-langgraph-agent -n langgraph-agent-dev`

## Summary

Provide:
- Deployment status (success/failure)
- Pod status and readiness
- Any warnings or errors encountered
- Next steps for testing the deployed application
