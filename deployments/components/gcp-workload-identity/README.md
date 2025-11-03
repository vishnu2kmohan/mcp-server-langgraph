# GCP Workload Identity Component

Documentation and patterns for GCP Workload Identity configuration.

## Overview

Workload Identity allows Kubernetes ServiceAccounts to authenticate as GCP Service Accounts without managing keys.

## Setup Requirements

### 1. GCP Side

```bash
# Create GCP Service Account
gcloud iam service-accounts create APP_SA_NAME \
  --project=PROJECT_ID

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:APP_SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Create Workload Identity binding
gcloud iam service-accounts add-iam-policy-binding \
  APP_SA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/K8S_SA_NAME]"
```

### 2. Kubernetes Side

Annotate ServiceAccount in your overlay:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-serviceaccount
  annotations:
    iam.gke.io/gcp-service-account: APP_SA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

### 3. Deployment

Reference the ServiceAccount:

```yaml
spec:
  template:
    spec:
      serviceAccountName: app-serviceaccount
```

## Validation

Test Workload Identity from a pod:

```bash
kubectl run -it --rm debug \
  --image=google/cloud-sdk:slim \
  --serviceaccount=app-serviceaccount \
  --namespace=NAMESPACE \
  -- gcloud auth list
```

## Common Services

- **Secret Manager**: `roles/secretmanager.secretAccessor`
- **Cloud SQL**: Automatic with Cloud SQL Proxy
- **Cloud Storage**: `roles/storage.objectViewer` or `roles/storage.objectAdmin`
- **Vertex AI**: `roles/aiplatform.user`

## Troubleshooting

1. **Permission denied**: Check IAM binding exists
2. **Wrong service account**: Verify annotation matches GCP SA
3. **Namespace mismatch**: Ensure Workload Identity binding includes correct namespace
