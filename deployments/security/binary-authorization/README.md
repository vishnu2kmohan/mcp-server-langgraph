# Binary Authorization for GKE

Binary Authorization ensures only signed and verified container images run in your GKE clusters.

## Overview

Binary Authorization provides:
- **Image signing**: Cryptographically sign container images
- **Policy enforcement**: Only allow signed images to deploy
- **Attestation tracking**: Audit trail of image approvals
- **Multi-environment support**: Different policies per environment

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        CI/CD Pipeline                         │
│                                                               │
│  1. Build image ────> 2. Push to registry ────> 3. Sign image│
│                                                        │      │
│                                                        ▼      │
│                                          ┌──────────────────┐│
│                                          │  Attestor        ││
│                                          │  + KMS Key       ││
│                                          │  + Note          ││
│                                          └──────────────────┘│
└──────────────────────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        GKE Cluster                            │
│                                                               │
│  Deployment Request ────> Binary Authorization Policy Check  │
│                                         │                     │
│                        ┌────────────────┴────────────────┐   │
│                        ▼                                  ▼   │
│                 Has Attestation?                    Allowed?  │
│                    YES/NO                            YES/NO   │
│                        │                                  │   │
│                        └─────────────┬────────────────────┘   │
│                                      ▼                        │
│                              ADMIT or DENY                    │
└──────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Run Setup Script

```bash
# Production
./deployments/security/binary-authorization/setup-binary-auth.sh PROJECT_ID production

# Staging
./deployments/security/binary-authorization/setup-binary-auth.sh PROJECT_ID staging

# Development
./deployments/security/binary-authorization/setup-binary-auth.sh PROJECT_ID development
```

This creates:
- KMS key ring and signing key
- Container Analysis note
- Binary Authorization attestor
- Policy appropriate for the environment

### 2. Enable in GKE Cluster

Update your Terraform configuration:

```hcl
# terraform/environments/gcp-prod/terraform.tfvars
enable_binary_authorization = true
```

Apply changes:
```bash
cd terraform/environments/gcp-prod
terraform apply
```

## Signing Images

### Manual Signing

```bash
# Sign an image
./deployments/security/binary-authorization/sign-image.sh \
  PROJECT_ID \
  production \
  us-central1-docker.pkg.dev/PROJECT_ID/mcp-production/mcp-server-langgraph:v1.0.0
```

### Automated Signing in CI/CD

Add to your GitHub Actions workflow:

```yaml
- name: Sign container image
  run: |
    gcloud container binauthz attestations sign-and-create \
      --artifact-url=${{ env.ARTIFACT_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }} \
      --attestor=production-attestor \
      --attestor-project=${{ env.GCP_PROJECT_ID }} \
      --keyversion-project=${{ env.GCP_PROJECT_ID }} \
      --keyversion-location=us-central1 \
      --keyversion-keyring=production-binauthz \
      --keyversion-key=attestor-key \
      --keyversion=1
```

## Policy Modes by Environment

### Production (Enforce)

```yaml
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
```

- **Requires attestation**: Images must be signed
- **Blocks unsigned images**: Deployment fails
- **Audit log**: All decisions logged

### Staging (Dry-Run)

```yaml
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: DRYRUN_AUDIT_LOG_ONLY
```

- **Checks attestation**: Validates signature
- **Allows unsigned**: Deployment succeeds (with warning)
- **Audit log**: Violations logged

### Development (Allow All)

```yaml
defaultAdmissionRule:
  evaluationMode: ALWAYS_ALLOW
  enforcementMode: DRYRUN_AUDIT_LOG_ONLY
```

- **No checks**: All images allowed
- **Audit log**: Deployment logged

## Whitelisted Images

These images are allowed without attestation:
- `gcr.io/google_containers/*`
- `gcr.io/google-containers/*`
- `k8s.gcr.io/*`
- `gke.gcr.io/*`

## Verification

### Check Policy

```bash
gcloud container binauthz policy export --project=PROJECT_ID
```

### List Attestations

```bash
gcloud container binauthz attestations list \
  --attestor=production-attestor \
  --project=PROJECT_ID
```

### View Specific Attestation

```bash
gcloud container binauthz attestations list \
  --attestor=production-attestor \
  --project=PROJECT_ID \
  --filter='resourceUri:"IMAGE_URL"'
```

### Test Enforcement

```bash
# Try deploying unsigned image (should fail in production)
kubectl run test-unsigned \
  --image=nginx:latest \
  --namespace=mcp-production

# Should see error:
# Error: admission webhook denied the request:
# image policy webhook backend denied one or more images:
# Denied by default admission rule
```

## Troubleshooting

### Issue: Attestation creation fails

**Error:**
```
ERROR: Permission denied on KMS key
```

**Solution:**
```bash
# Grant yourself KMS signer role
gcloud kms keys add-iam-policy-binding attestor-key \
  --location=us-central1 \
  --keyring=production-binauthz \
  --member="user:YOUR_EMAIL" \
  --role="roles/cloudkms.signerVerifier" \
  --project=PROJECT_ID
```

### Issue: Signed image still blocked

**Error:**
```
Denied by attestor
```

**Solution:**
```bash
# Verify attestation exists
gcloud container binauthz attestations list \
  --attestor=production-attestor \
  --project=PROJECT_ID \
  --filter='resourceUri:"IMAGE_URL"'

# If no attestation found, sign again
./sign-image.sh PROJECT_ID production IMAGE_URL
```

### Issue: Policy not enforcing

**Problem:** Unsigned images are allowed in production

**Solution:**
```bash
# Check policy
gcloud container binauthz policy export --project=PROJECT_ID

# Ensure enforcement mode is ENFORCED_BLOCK_AND_AUDIT_LOG
# Re-import policy if needed
./setup-binary-auth.sh PROJECT_ID production
```

## Best Practices

### 1. Sign All Production Images

Add signing to your release process:
```yaml
# .github/workflows/release.yaml
- name: Sign release image
  if: github.event_name == 'release'
  run: ./deployments/security/binary-authorization/sign-image.sh \
    ${{ env.PROJECT_ID }} \
    production \
    ${{ env.IMAGE_URL }}
```

### 2. Test in Staging First

Enable dry-run mode in staging to catch issues:
```bash
./setup-binary-auth.sh PROJECT_ID staging
```

### 3. Monitor Denials

Set up alerting for denied deployments:
```bash
gcloud logging read \
  'protoPayload.serviceName="binaryauthorization.googleapis.com" AND protoPayload.response.allow=false' \
  --limit=10
```

### 4. Rotate Keys Regularly

Create new key versions annually:
```bash
gcloud kms keys versions create \
  --location=us-central1 \
  --keyring=production-binauthz \
  --key=attestor-key \
  --project=PROJECT_ID
```

### 5. Use Breakglass for Emergencies

Override policy in emergencies:
```bash
# Deploy with breakglass annotation
kubectl run emergency-pod \
  --image=UNSIGNED_IMAGE \
  --overrides='{"metadata":{"annotations":{"alpha.image-policy.k8s.io/break-glass":"true"}}}'
```

**Warning:** Breakglass deployments are audited. Only use in genuine emergencies.

## References

- [Binary Authorization Documentation](https://cloud.google.com/binary-authorization/docs)
- [Attestor Setup Guide](https://cloud.google.com/binary-authorization/docs/creating-attestors-console)
- [Policy Reference](https://cloud.google.com/binary-authorization/docs/policy-yaml-reference)
