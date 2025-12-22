# VAPID Key Rotation Runbook

## Overview

This runbook covers operational procedures for VAPID (Voluntary Application Server Identification) key rotation used in Web Push notifications.

**Last Updated**: 2025-12-21
**Owner**: Platform Team
**Reference**: ADR-0026 - Comprehensive Client Resilience Patterns

---

## Table of Contents

1. [Background](#background)
2. [Prerequisites](#prerequisites)
3. [Routine Rotation](#routine-rotation)
4. [Emergency Rotation](#emergency-rotation)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Background

VAPID keys are ECDSA P-256 key pairs used to authenticate the application server with push notification services (Google FCM, Apple APNs via web push, Mozilla Autopush).

### Key Components
- **Public Key**: Shared with browsers during push subscription
- **Private Key**: Used to sign push messages (kept secret)
- **Claims**: Contact email for push service operators

### Key Locations
- Environment: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL`
- Database: `vapid_keys` table (for versioned key management)
- Code: `src/mcp_server_langgraph/notifications/vapid_rotation.py`

---

## Prerequisites

### Required Access
- [ ] Kubernetes cluster admin or deployment permissions
- [ ] Database write access to `vapid_keys` table
- [ ] Access to secrets management (Vault/Infisical)

### Tools Required
```bash
# Install web-push CLI for key generation
npm install -g web-push

# Verify installation
web-push --version
```

---

## Routine Rotation

Recommended rotation interval: **90 days**

### Step 1: Generate New Key Pair

```bash
# Generate new VAPID keys
web-push generate-vapid-keys --json > new-vapid-keys.json

# View the keys (DO NOT LOG IN PRODUCTION)
cat new-vapid-keys.json
```

Output:
```json
{
  "publicKey": "BL7z...",
  "privateKey": "dGhp..."
}
```

### Step 2: Create Key in Database (Overlap Period)

```python
# Using the VAPIDKeyRotationService
from mcp_server_langgraph.notifications.vapid_rotation import (
    VAPIDKeyRotationService,
    PostgresVAPIDKeyRepository,
)

# Initialize service
repo = PostgresVAPIDKeyRepository(pool)
service = VAPIDKeyRotationService(repo, overlap_hours=24)

# Rotate to new key (old key remains active for overlap period)
await service.rotate_keys()
```

### Step 3: Update Environment Variables

```bash
# Update in Kubernetes secret
kubectl create secret generic vapid-keys \
  --from-literal=VAPID_PUBLIC_KEY="BL7z..." \
  --from-literal=VAPID_PRIVATE_KEY="dGhp..." \
  --from-literal=VAPID_CLAIMS_EMAIL="admin@yourdomain.com" \
  --dry-run=client -o yaml | kubectl apply -f -

# Trigger rolling restart
kubectl rollout restart deployment/mcp-server-langgraph
```

### Step 4: Verify Rotation

```bash
# Check active key in API
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/api/v1/notifications/push/vapid-public-key

# Verify push notifications still work
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Key rotation test"}' \
  https://api.example.com/api/v1/notifications/push/test
```

### Step 5: Cleanup Expired Keys (After Overlap)

```python
# After 24 hours, cleanup expired keys
deleted = await service.cleanup_expired_keys()
print(f"Cleaned up {deleted} expired keys")
```

---

## Emergency Rotation

Use this procedure if a key has been compromised.

### Immediate Actions

1. **Revoke Compromised Key Immediately**
   ```python
   await service.emergency_revoke(compromised_key_id)
   ```

2. **Generate and Activate New Key**
   ```python
   await service.rotate_keys(overlap_hours=0)  # No overlap
   ```

3. **Force Re-subscription**
   - Users with the old public key must re-subscribe
   - Push a notification to all users requesting permission refresh

   ```python
   # Broadcast re-subscription request
   await broadcaster.send_to_all(
       PushMessage(
           title="Security Update",
           body="Please re-enable notifications",
           data={"action": "resubscribe"}
       )
   )
   ```

4. **Invalidate Old Subscriptions**
   ```sql
   -- Mark all subscriptions using old key as invalid
   UPDATE push_subscriptions
   SET is_valid = false
   WHERE vapid_key_id = 'compromised-key-id';
   ```

### Post-Incident

- [ ] Create incident report
- [ ] Review access logs for key exposure
- [ ] Update secrets rotation schedule if needed

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold | Description |
|--------|-----------------|-------------|
| `vapid_key_age_days` | > 90 | Key needs rotation |
| `push_subscriptions_invalid` | > 1000 | Subscriptions using old key |
| `push_notifications_auth_failures` | > 10/min | VAPID signature rejections |

### Grafana Dashboard

Navigate to: **Infrastructure > Resilience Patterns > Push Notification Resilience**

Key panels:
- Push Notification Send Rate (watch for auth failures)
- Subscription Lifecycle Events (watch for expiry spikes)

### Alerts

```yaml
# Example Alertmanager rule
- alert: VAPIDKeyNeedsRotation
  expr: vapid_key_age_days > 90
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: VAPID key is due for rotation
    runbook_url: /docs-internal/runbooks/VAPID_KEY_ROTATION.md
```

---

## Troubleshooting

### Push Notifications Failing After Rotation

**Symptoms**: 401/403 errors from push services

**Causes**:
1. Old private key still in use
2. Public key mismatch with subscriptions

**Resolution**:
```bash
# Verify environment has new keys
kubectl exec -it deploy/mcp-server-langgraph -- printenv | grep VAPID

# Force pod restart if cached
kubectl rollout restart deployment/mcp-server-langgraph
```

### Subscriptions Not Working

**Symptoms**: Push notifications not delivered, no errors

**Causes**:
1. Subscriptions created with old public key
2. Browser needs to re-subscribe

**Resolution**:
```sql
-- Count subscriptions by key version
SELECT vapid_key_id, COUNT(*)
FROM push_subscriptions
GROUP BY vapid_key_id;

-- Check for stale subscriptions
SELECT COUNT(*)
FROM push_subscriptions
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Key Generation Fails

**Symptoms**: `web-push generate-vapid-keys` fails

**Resolution**:
```bash
# Alternative: Use Python cryptography
python -c "
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64

private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()

# Export in DER format, then base64
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

pub = base64.urlsafe_b64encode(
    public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
).decode()
priv = base64.urlsafe_b64encode(
    private_key.private_bytes(
        Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
    )
).decode()

print(f'Public: {pub}')
print(f'Private: {priv}')
"
```

---

## Key Rotation Checklist

### Before Rotation
- [ ] Verify current key age and status
- [ ] Confirm backup of current keys
- [ ] Schedule during low-traffic period
- [ ] Notify on-call team

### During Rotation
- [ ] Generate new key pair
- [ ] Update database with overlap period
- [ ] Update environment variables
- [ ] Restart services
- [ ] Test push delivery

### After Rotation
- [ ] Monitor push success rate
- [ ] Verify new subscriptions use new key
- [ ] Cleanup expired keys after overlap
- [ ] Update documentation if process changed

---

## References

- [RFC 8292 - VAPID](https://datatracker.ietf.org/doc/html/rfc8292)
- [Web Push Protocol](https://datatracker.ietf.org/doc/html/rfc8030)
- [ADR-0026 - Client Resilience Patterns](../ADR-0026-RESILIENCE-PATTERNS.md)
- [Push Notifications Guide](../../docs/guides/push-notifications.mdx)
