# GCP GKE Security Hardening Guide

**Version**: 1.0
**Last Updated**: 2025-11-01
**Compliance**: CIS GKE Benchmark, NIST, SOC 2
**Audience**: Security Engineers, Platform Engineers, Compliance Officers

---

## Overview

This guide provides comprehensive security hardening steps for MCP Server LangGraph on GKE Autopilot, achieving defense-in-depth across infrastructure, network, application, and data layers.

**Security Posture Goals**:
- ✅ Zero critical vulnerabilities
- ✅ CIS GKE Benchmark compliance
- ✅ Data encryption at rest and in transit
- ✅ Zero-trust network architecture
- ✅ Automated security scanning
- ✅ Audit logging for all access

---

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 7: Compliance & Governance                           │
│  - Audit logging, policy enforcement, compliance reports    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: Application Security                              │
│  - Binary Authorization, vulnerability scanning, SBOM       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Identity & Access (Workload Identity)             │
│  - Pod-level service accounts, IAM policies, no keys        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Data Security                                     │
│  - Encryption at rest (CMEK), encryption in transit (TLS)   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Network Security                                  │
│  - Private cluster, network policies, Cloud Armor           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Compute Security (Shielded Nodes)                 │
│  - Secure Boot, vTPM, integrity monitoring                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Infrastructure Security                           │
│  - VPC isolation, IAM boundaries, GKE Security Posture      │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Infrastructure Security

### 1.1 Enable GKE Security Posture Dashboard

**Status**: Configured in Terraform module

**Enable**:
```hcl
# terraform/environments/gcp-prod/terraform.tfvars
enable_security_posture             = true
security_posture_mode               = "ENTERPRISE"  # or "BASIC"
security_posture_vulnerability_mode = "VULNERABILITY_ENTERPRISE"
```

**Apply**:
```bash
terraform apply
```

**View Dashboard**:
```bash
# Get security posture
gcloud container clusters describe mcp-prod-gke \
  --region=us-central1 \
  --format="yaml(securityPostureConfig)"

# Or visit console:
# https://console.cloud.google.com/kubernetes/clusters/details/us-central1/mcp-prod-gke/security?project=PROJECT_ID
```

### 1.2 Enable Audit Logging

**Admin Activity Logs** (enabled by default):
- Cluster creation/deletion
- Configuration changes
- IAM policy changes

**Data Access Logs** (enable for compliance):
```bash
# Enable data access logs for GKE
gcloud projects get-iam-policy PROJECT_ID \
  --format=json > /tmp/policy.json

# Add audit config
jq '.auditConfigs += [{
  "service": "container.googleapis.com",
  "auditLogConfigs": [
    {"logType": "ADMIN_READ"},
    {"logType": "DATA_READ"},
    {"logType": "DATA_WRITE"}
  ]
}]' /tmp/policy.json > /tmp/policy-updated.json

gcloud projects set-iam-policy PROJECT_ID /tmp/policy-updated.json
```

---

## Layer 2: Compute Security (Shielded Nodes)

### 2.1 Shielded GKE Nodes

**Status**: ✅ Automatic in GKE Autopilot

**Features**:
- **Secure Boot**: Ensures only signed software boots
- **vTPM** (Virtual Trusted Platform Module): Hardware-based key storage
- **Integrity Monitoring**: Detects tampering

**Verify**:
```bash
gcloud container clusters describe mcp-prod-gke \
  --region=us-central1 \
  --format="yaml(shieldedNodes)"
```

**Expected Output**:
```yaml
shieldedNodes:
  enabled: true
```

### 2.2 Node Auto-Repair & Auto-Upgrade

**Status**: ✅ Automatic in Autopilot

**Verify**:
```bash
gcloud container clusters describe mcp-prod-gke \
  --region=us-central1 \
  --format="yaml(nodePools[].management)"
```

---

## Layer 3: Network Security

### 3.1 Private Cluster Configuration

**Current**: Private nodes (✅), Public endpoint (❌)

**Maximum Security**: Private nodes + Private endpoint

**Enable Private Endpoint**:
```hcl
# terraform.tfvars
enable_private_endpoint = true
```

**⚠️ Impact**: Control plane only accessible via VPC

**Access Options**:
1. **Cloud Shell** (automatic VPC access)
2. **Bastion Host** in VPC
3. **Cloud VPN** / Interconnect

```bash
# Access via Cloud Shell
gcloud container clusters get-credentials mcp-prod-gke \
  --region=us-central1 \
  --internal-ip
```

### 3.2 Master Authorized Networks

**Restrict who can access control plane**:

```hcl
enable_master_authorized_networks = true
master_authorized_networks_cidrs = [
  {
    cidr_block   = "10.0.0.0/8"      # Internal VPC only
    display_name = "VPC"
  },
  {
    cidr_block   = "203.0.113.0/24"  # Office/VPN IP
    display_name = "Corporate Network"
  }
]
```

### 3.3 Network Policies

**Status**: ✅ Enabled by default in production overlay

**Verify**:
```bash
kubectl get networkpolicies -n mcp-production
```

**Test**:
```bash
# Try to access pod from unauthorized namespace (should fail)
kubectl run test --image=busybox -n default -- \
  wget -qO- http://production-mcp-server-langgraph.mcp-production:8000
```

### 3.4 Cloud Armor (DDoS Protection)

**Enable**:
```hcl
enable_cloud_armor = true
```

**Apply to Load Balancer**:
```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    cloud.google.com/backend-config: '{"default": "cloud-armor-config"}'
```

---

## Layer 4: Data Security

### 4.1 Encryption at Rest

**Google-Managed Keys** (Default):
- ✅ All data encrypted automatically
- ✅ Keys managed by Google
- ✅ Automatic rotation

**Customer-Managed Encryption Keys (CMEK)**:

**Create KMS Key**:
```bash
# Create key ring
gcloud kms keyrings create mcp-encryption \
  --location=us-central1 \
  --project=PROJECT_ID

# Create key
gcloud kms keys create database-encryption \
  --location=us-central1 \
  --keyring=mcp-encryption \
  --purpose=encryption \
  --rotation-period=90d \
  --next-rotation-time=$(date -u -d '90 days' +%Y-%m-%dT%H:%M:%S)Z \
  --project=PROJECT_ID
```

**Enable in Terraform**:
```hcl
# Cloud SQL
kms_key_name = "projects/PROJECT_ID/locations/us-central1/keyRings/mcp-encryption/cryptoKeys/database-encryption"

# Memorystore
customer_managed_key = "projects/PROJECT_ID/locations/us-central1/keyRings/mcp-encryption/cryptoKeys/cache-encryption"
```

**Benefits**:
- Full control over encryption keys
- Key rotation policies
- Audit key usage
- Compliance requirements (HIPAA, PCI-DSS)

### 4.2 Encryption in Transit

**TLS Configuration**:

**Cloud SQL**:
```hcl
require_ssl = true  # ✅ Already configured
```

**Redis**:
```hcl
enable_transit_encryption = true  # ✅ Already configured
```

**Application**:
```yaml
# Enforce HTTPS
- name: REQUIRE_HTTPS
  value: "true"
```

### 4.3 Secret Management

**✅ Current**: External Secrets Operator + Secret Manager

**Best Practices**:
1. **Never commit secrets** to Git
2. **Use Secret Manager** for all sensitive data
3. **Workload Identity** for access (no keys)
4. **Rotate regularly** (90 days)

**Create Secret**:
```bash
# Create secret
echo -n "super-secret-value" | gcloud secrets create SECRET_NAME \
  --data-file=- \
  --replication-policy=automatic \
  --project=PROJECT_ID

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=PROJECT_ID
```

---

## Layer 5: Identity & Access

### 5.1 Workload Identity (✅ Configured)

**Principle of Least Privilege**:

```hcl
service_accounts = {
  "app-sa" = {
    roles = [
      "roles/logging.logWriter",        # Only what's needed
      "roles/monitoring.metricWriter",  # No wildcard permissions
    ]
    cloudsql_access = true  # Specific resource access
  }
}
```

**Verify**:
```bash
# Check service account permissions
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-prod-app-sa@PROJECT_ID.iam.gserviceaccount.com"
```

### 5.2 RBAC (Role-Based Access Control)

**Create custom roles**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: mcp-production
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: mcp-production
subjects:
- kind: User
  name: developer@company.com
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

### 5.3 Disable Service Account Key Creation

**Policy Constraint**:
```bash
# Org policy to prevent SA key creation
gcloud resource-manager org-policies set-policy <(cat <<EOF
constraint: constraints/iam.disableServiceAccountKeyCreation
booleanPolicy:
  enforced: true
EOF
) --project=PROJECT_ID
```

---

## Layer 6: Application Security

### 6.1 Binary Authorization (✅ Configured)

**Enforcement Levels**:

**Production** (enforce):
```yaml
defaultAdmissionRule:
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
```

**Test Enforcement**:
```bash
# Try unsigned image (should block)
kubectl run test --image=nginx:latest -n mcp-production

# Expected error:
# Error: admission webhook denied the request
```

### 6.2 Container Image Scanning

**Vulnerability Scanning**:

**Manual Scan**:
```bash
# Scan image
gcloud container images scan IMAGE_URL

# View results
gcloud container images describe IMAGE_URL \
  --show-package-vulnerability
```

**Automated** (in CI/CD):
```yaml
# .github/workflows/security-scan.yaml
- name: Scan with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}
    severity: CRITICAL,HIGH
    exit-code: '1'
```

### 6.3 Pod Security Standards

**Apply Pod Security** policies:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Restricted Profile**:
- ❌ No privileged containers
- ❌ No host network/PID/IPC
- ❌ No privilege escalation
- ✅ Run as non-root
- ✅ Read-only root filesystem
- ✅ Drop all capabilities

**Verify**:
```bash
kubectl label namespace mcp-production pod-security.kubernetes.io/enforce=restricted
```

---

## Layer 7: Compliance & Governance

### 7.1 VPC Service Controls

**Create Service Perimeter**:

```bash
# 1. Create access policy (one-time, org-level)
gcloud access-context-manager policies create \
  --organization=ORG_ID \
  --title="MCP Production Policy"

# 2. Get policy ID
POLICY_ID=$(gcloud access-context-manager policies list \
  --organization=ORG_ID \
  --format="value(name)")

# 3. Create service perimeter
gcloud access-context-manager perimeters create mcp-production \
  --policy=$POLICY_ID \
  --title="MCP Production Perimeter" \
  --resources=projects/PROJECT_NUMBER \
  --restricted-services=container.googleapis.com,sqladmin.googleapis.com,redis.googleapis.com \
  --enable-vpc-accessible-services \
  --vpc-allowed-services=container.googleapis.com,sqladmin.googleapis.com
```

**Benefits**:
- Prevents data exfiltration
- Blocks unauthorized access
- Enforces network boundaries

### 7.2 Policy as Code (OPA/Gatekeeper)

**Install Gatekeeper**:
```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
```

**Example Policy** (require labels):
```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg, "details": {"missing_labels": missing}}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing required labels: %v", [missing])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-production-labels
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
    namespaces: ["mcp-production"]
  parameters:
    labels: ["environment", "team", "application"]
```

### 7.3 Continuous Compliance Scanning

**Policy Controller** (GKE Enterprise):
```bash
# Enable Policy Controller
gcloud container fleet policycontroller enable \
  --memberships=mcp-prod-gke-membership \
  --project=PROJECT_ID

# Apply policy bundles
kubectl apply -f https://github.com/GoogleCloudPlatform/gke-policy-library/releases/latest/download/all-policies.yaml
```

---

## Security Checklist

### Infrastructure ✅

- [x] GKE Security Posture enabled
- [x] Audit logging enabled
- [x] Shielded nodes (automatic in Autopilot)
- [x] Workload Identity enabled
- [ ] VPC Service Controls (optional, for high-security)

### Network ✅

- [x] Private nodes (no public IPs)
- [x] VPC-native networking
- [x] Network policies enforced
- [x] Cloud NAT for egress
- [ ] Private endpoint (optional, for maximum security)
- [ ] Cloud Armor (enabled via variable)

### Application ✅

- [x] Binary Authorization (ready to enable)
- [x] Container scanning (Trivy in CI/CD)
- [x] Pod security standards (restricted)
- [x] Non-root containers
- [x] Read-only root filesystem (where applicable)
- [x] Dropped capabilities (ALL)

### Data ✅

- [x] Encryption at rest (Google-managed)
- [ ] CMEK (optional, for compliance)
- [x] Encryption in transit (TLS)
- [x] Secrets in Secret Manager
- [x] No secrets in Git
- [x] No service account keys

### Identity ✅

- [x] Workload Identity (no SA keys)
- [x] IAM least privilege
- [x] Per-workload service accounts
- [x] RBAC policies
- [ ] Service account key creation disabled (via org policy)

### Compliance ✅

- [ ] VPC Service Controls (optional)
- [ ] Policy Controller (optional)
- [x] Audit logs retention (30 days default)
- [ ] OPA/Gatekeeper (optional)

---

## Security Testing

### Penetration Testing

**Automated Security Scans**:
```bash
# 1. Scan infrastructure
trivy config terraform/

# 2. Scan Kubernetes manifests
trivy config deployments/overlays/production-gke/

# 3. Scan container images
trivy image IMAGE_URL

# 4. Check for exposed secrets
gitleaks detect --source=.
```

### Compliance Validation

**CIS GKE Benchmark**:
```bash
# Use kube-bench for CIS compliance
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-gke.yaml

# View results
kubectl logs -l app=kube-bench
```

---

## Incident Response

### Security Incident Runbook

**1. Detection**:
- Security alert fires
- Unusual activity in audit logs
- Binary Authorization denial surge

**2. Containment**:
```bash
# Isolate affected pods
kubectl label pod SUSPICIOUS_POD quarantine=true -n mcp-production

# Network policy to isolate
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-suspicious-pod
  namespace: mcp-production
spec:
  podSelector:
    matchLabels:
      quarantine: "true"
  policyTypes:
  - Ingress
  - Egress
  # No ingress/egress rules = complete isolation
EOF
```

**3. Investigation**:
```bash
# Export pod logs
kubectl logs POD_NAME -n mcp-production --all-containers > incident-logs.txt

# Check audit logs
gcloud logging read \
  'resource.type="k8s_cluster" AND protoPayload.resourceName=~"pods/SUSPICIOUS_POD"' \
  --limit=100 \
  --format=json \
  --project=PROJECT_ID > audit-trail.json
```

**4. Remediation**:
- Delete compromised pods
- Rotate all secrets
- Review and tighten IAM policies
- Deploy patched version

**5. Post-Incident**:
- Document root cause
- Update security policies
- Add preventive controls

---

## Security Monitoring

### Critical Metrics to Monitor

1. **Unauthorized Access Attempts**:
   ```bash
   gcloud logging read \
     'protoPayload.status.code!=0 AND protoPayload.authenticationInfo.principalEmail!=""' \
     --project=PROJECT_ID
   ```

2. **Binary Authorization Denials**:
   ```bash
   gcloud logging read \
     'protoPayload.serviceName="binaryauthorization.googleapis.com" AND protoPayload.response.allow=false' \
     --project=PROJECT_ID
   ```

3. **Privileged Pod Attempts**:
   ```bash
   kubectl get pods -A -o json \
     | jq '[.items[] | select(.spec.containers[].securityContext.privileged==true)] | length'
   ```

4. **Network Policy Violations**:
   ```bash
   gcloud logging read \
     'resource.type="k8s_pod" AND protoPayload.request.spec.containers[].securityContext.privileged=true' \
     --project=PROJECT_ID
   ```

---

## Compliance Frameworks

### CIS GKE Benchmark

**Key Controls** (Auto-compliant in Autopilot):
- ✅ 4.1.1 Ensure Workload Identity is enabled
- ✅ 4.1.2 Ensure legacy ABAC is disabled
- ✅ 4.2.1 Ensure Network Policy is enabled
- ✅ 4.3.1 Ensure private cluster is enabled
- ✅ 4.4.1 Ensure Binary Authorization is enabled (when configured)
- ✅ 4.5.1 Ensure GKE Audit Logging is enabled
- ✅ 5.1.1 Ensure Shielded GKE Nodes are enabled

### SOC 2 Compliance

**Type II Controls**:
- ✅ Access control (Workload Identity + RBAC)
- ✅ Encryption (at rest + in transit)
- ✅ Audit logging (all access logged)
- ✅ Change management (Terraform + GitOps)
- ✅ Monitoring & alerting (Cloud Operations)
- ✅ Incident response (runbooks documented)

### HIPAA Compliance (if applicable)

**Requirements**:
- ✅ Encryption at rest (CMEK recommended)
- ✅ Encryption in transit (TLS required)
- ✅ Audit logs (retained 6+ years)
- ✅ Access controls (IAM + RBAC)
- ✅ Business Associate Agreement (with Google)

**Additional Steps**:
1. Enable CMEK for all data
2. Configure audit log retention to 7 years
3. Sign BAA with Google Cloud

---

## Security Best Practices Summary

### Top 10 Must-Do Items

1. ✅ **Enable Workload Identity** (no service account keys)
2. ✅ **Use Private Nodes** (no public node IPs)
3. ✅ **Enforce Network Policies** (zero-trust networking)
4. ✅ **Enable Binary Authorization** (signed images only)
5. ✅ **Encrypt in Transit** (TLS for all connections)
6. ✅ **Use Secret Manager** (no secrets in Git/ConfigMaps)
7. ✅ **Enable Security Posture** (automated vuln scanning)
8. ✅ **Restrict Control Plane Access** (master authorized networks)
9. ✅ **Enable Audit Logging** (track all access)
10. ✅ **Regular Security Scans** (Trivy, kube-bench)

### Automation Opportunities

1. **Automated Security Scans** (daily):
   - Container image scanning
   - Infrastructure scanning
   - Kubernetes manifest validation

2. **Automated Remediation**:
   - Patch vulnerable images
   - Rotate expiring secrets
   - Update firewall rules

3. **Continuous Compliance**:
   - Policy Controller for real-time enforcement
   - Automated compliance reports
   - Drift detection and correction

---

**End of Security Hardening Guide**

**Related Documents**:
- [Binary Authorization Setup](./deployments/security/binary-authorization/README.md)
- [Operational Runbooks](./deployments/GKE_OPERATIONAL_RUNBOOKS.md)
- [Deployment Guide](./deployments/GKE_DEPLOYMENT_GUIDE.md)
