# Rollback Procedures & Error Handling

Rollback strategies, deployment resource configurations, and common error handling.

---

## Rollback Plan

```
  ROLLBACK PLAN

  Automatic Rollback (K8s):
    kubectl rollout undo deployment/mcp-server-langgraph -n mcp-server-langgraph

  Helm Rollback:
    helm rollback mcp-server-langgraph -n mcp-server-langgraph

  Manual Rollback (Kustomize):
    git checkout <previous-commit>
    kubectl apply -k deployments/overlays/<env>/

  Cloud Run Rollback:
    gcloud run services update-traffic mcp-server-langgraph \
      --to-revisions=<previous-revision>=100 \
      --region=us-central1

  Verification After Rollback:
    1. Check pod status
    2. Verify application health
    3. Run smoke tests
    4. Monitor error rates
```

---

## Deployment Configurations

### Resource Requirements

```yaml
# Dev
requests:
  cpu: 100m
  memory: 256Mi
limits:
  cpu: 500m
  memory: 512Mi

# Staging
requests:
  cpu: 250m
  memory: 512Mi
limits:
  cpu: 1000m
  memory: 1Gi

# Production
requests:
  cpu: 500m
  memory: 1Gi
limits:
  cpu: 2000m
  memory: 2Gi
```

### Scaling Configuration

- **Dev**: 1 replica (no autoscaling)
- **Staging**: 1-3 replicas (HPA: CPU > 70%)
- **Production**: 3-10 replicas (HPA: CPU > 60%, Memory > 70%)

---

## Error Handling

### Common Errors

1. **ImagePullBackOff**:
   - Check image exists in registry
   - Verify image pull secrets
   - Check image tag is correct

2. **CrashLoopBackOff**:
   - Check application logs
   - Verify environment variables
   - Check secrets are mounted

3. **Pending Pods**:
   - Check resource quotas
   - Verify node resources available
   - Check PV/PVC status

4. **Ingress Not Working**:
   - Verify ingress controller installed
   - Check ingress annotations
   - Verify DNS records
