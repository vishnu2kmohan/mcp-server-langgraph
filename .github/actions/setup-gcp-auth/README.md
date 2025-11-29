# Setup GCP Authentication Composite Action

Composite action for authenticating to Google Cloud Platform using Workload Identity Federation.

## Features

- ✅ **Workload Identity Federation**: Keyless authentication using WIF (no service account keys)
- ✅ **Flexible token formats**: Support for Application Default Credentials, access tokens, and ID tokens
- ✅ **Output propagation**: Exposes all outputs from google-github-actions/auth
- ✅ **Version pinning**: Configurable auth action version (defaults to v3)
- ✅ **Standardized setup**: Consistent GCP authentication across all workflows

## Usage

### Basic Authentication (Application Default Credentials)

```yaml
- name: Authenticate to Google Cloud
  uses: ./.github/actions/setup-gcp-auth
  with:
    workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
    service-account: ${{ secrets.GCP_SERVICE_ACCOUNT_EMAIL }}
```

### Authentication with Access Token (for Docker/Artifact Registry)

```yaml
- name: Authenticate to Google Cloud
  uses: ./.github/actions/setup-gcp-auth
  with:
    workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
    service-account: ${{ secrets.GCP_PRODUCTION_SA_EMAIL }}
    token-format: access_token

- name: Configure Docker for Artifact Registry
  run: |
    echo '${{ steps.auth.outputs.access_token }}' | docker login -u oauth2accesstoken --password-stdin https://us-central1-docker.pkg.dev
```

### Using Outputs

```yaml
- name: Authenticate to Google Cloud
  id: gcp_auth
  uses: ./.github/actions/setup-gcp-auth
  with:
    workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
    service-account: ${{ secrets.GCP_STAGING_SA_EMAIL }}

- name: Use Project ID
  run: |
    echo "Authenticated to project: ${{ steps.gcp_auth.outputs.project_id }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `workload-identity-provider` | Workload Identity Provider ID (full resource name) | Yes | - |
| `service-account` | Service Account email | Yes | - |
| `token-format` | Token format: none, access_token, or id_token | No | `''` (Application Default Credentials) |
| `auth-version` | Version of google-github-actions/auth | No | `v3` |

## Outputs

| Output | Description |
|--------|-------------|
| `project_id` | GCP Project ID from authenticated service account |
| `access_token` | Access token (only when token-format is access_token) |
| `id_token` | ID token (only when token-format is id_token) |
| `credentials_file_path` | Path to generated credentials file |

## Examples

### Deployment Workflow (with GKE)

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Required for Workload Identity Federation
    steps:
      - uses: actions/checkout@v5

      - name: Authenticate to Google Cloud
        uses: ./.github/actions/setup-gcp-auth
        with:
          workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service-account: ${{ secrets.GCP_PRODUCTION_SA_EMAIL }}

      - name: Get GKE Credentials
        uses: google-github-actions/get-gke-credentials@v3
        with:
          cluster_name: production-cluster
          location: us-central1

      - name: Deploy to GKE
        run: |
          kubectl apply -k deployments/overlays/production
```

### Terraform Workflow

```yaml
jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v5

      - name: Authenticate to Google Cloud
        uses: ./.github/actions/setup-gcp-auth
        with:
          workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service-account: ${{ secrets.GCP_TERRAFORM_SA_EMAIL }}

      - name: Terraform Init
        run: |
          terraform init
          terraform plan
```

### Docker Build and Push to Artifact Registry

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v5

      - name: Authenticate to Google Cloud
        id: auth
        uses: ./.github/actions/setup-gcp-auth
        with:
          workload-identity-provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service-account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          token-format: access_token

      - name: Configure Docker for Artifact Registry
        run: |
          echo '${{ steps.auth.outputs.access_token }}' | docker login -u oauth2accesstoken --password-stdin https://us-central1-docker.pkg.dev

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          push: true
          tags: us-central1-docker.pkg.dev/${{ steps.auth.outputs.project_id }}/my-repo/my-image:latest
```

## Benefits

1. **Reduced duplication**: Consolidates GCP auth from 13 instances across 5 workflows
2. **Consistent authentication**: All workflows use the same pattern and version
3. **Easier maintenance**: Update auth version once, apply everywhere
4. **Improved security**: Centralized configuration reduces misconfiguration risk
5. **Better discoverability**: Single place to learn GCP authentication patterns

## Workload Identity Federation Setup

This action assumes you have already configured Workload Identity Federation in your GCP project. If not, follow these steps:

### Prerequisites

1. **Create Workload Identity Pool**:
   ```bash
   gcloud iam workload-identity-pools create "github-actions-pool" \
     --project="${PROJECT_ID}" \
     --location="global" \
     --display-name="GitHub Actions Pool"
   ```

2. **Create Workload Identity Provider**:
   ```bash
   gcloud iam workload-identity-pools providers create-oidc "github-provider" \
     --project="${PROJECT_ID}" \
     --location="global" \
     --workload-identity-pool="github-actions-pool" \
     --display-name="GitHub Provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

3. **Grant Service Account Permissions**:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_EMAIL}" \
     --project="${PROJECT_ID}" \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/${GITHUB_REPOSITORY}"
   ```

4. **Set GitHub Secrets**:
   - `GCP_WIF_PROVIDER`: Full resource name of the Workload Identity Provider
   - `GCP_*_SA_EMAIL`: Service account email for each environment

### Full Resource Name Format

The `workload-identity-provider` input requires the full resource name:

```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
```

Example:
```
projects/123456789/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
```

## Related Workflows

This composite action is used in:
- `.github/workflows/deploy-production-gke.yaml` - Production GKE deployments (4 jobs)
- `.github/workflows/deploy-staging-gke.yaml` - Staging GKE deployments (4 jobs)
- `.github/workflows/gcp-drift-detection.yaml` - Terraform drift detection (3 jobs)
- `.github/workflows/gcp-compliance-scan.yaml` - Compliance scanning (1 job)
- `.github/workflows/ci.yaml` - CI/CD pipeline (1 job)

## Maintenance

**Action versions**:
- google-github-actions/auth: `v3` (configurable via `auth-version` input)

To update the auth action version globally, edit `.github/actions/setup-gcp-auth/action.yaml` or use the `auth-version` input.

## Troubleshooting

### Error: "Failed to generate Google Cloud Platform access token"

**Cause**: Workload Identity Federation not configured or incorrect service account permissions.

**Solution**:
1. Verify WIF configuration: `gcloud iam workload-identity-pools describe github-actions-pool --location=global`
2. Check service account bindings: `gcloud iam service-accounts get-iam-policy SERVICE_ACCOUNT_EMAIL`
3. Ensure workflow has `id-token: write` permission

### Error: "Invalid workload identity provider"

**Cause**: Incorrect format or missing provider.

**Solution**: Use full resource name format:
```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
```

### Authentication succeeds but subsequent GCP operations fail

**Cause**: Service account lacks required permissions.

**Solution**: Grant appropriate IAM roles to the service account:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/ROLE_NAME"
```

Common roles:
- `roles/container.developer` - GKE deployments
- `roles/artifactregistry.writer` - Artifact Registry pushes
- `roles/storage.admin` - Cloud Storage access
- `roles/viewer` - Read-only access for drift detection

---

**Last Updated**: 2025-11-24
**Maintained by**: Platform Engineering Team
