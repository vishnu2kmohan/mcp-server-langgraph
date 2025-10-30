# 37. Identity Federation Architecture

Date: 2025-01-28

## Status

Accepted

## Context

Enterprise users exist in multiple identity systems (Active Directory, Azure AD, Google Workspace, Okta, GitHub) and forcing migration to Keycloak-only creates adoption barriers. Need to support:
- LDAP/Active Directory (10,000+ user enterprises)
- SAML providers (ADFS, Azure AD, Ping Identity)
- OIDC providers (Google, Microsoft, GitHub, Okta, OneLogin)
- Maintain single JWT output for consistent authorization

Current system: Keycloak with local users only, no federation configured.

## Decision

Implement **Identity Federation via Keycloak** as identity broker, federating all external identity providers while normalizing to consistent JWT output.

### Architecture

```
External IdPs (LDAP, SAML, OIDC) → Keycloak (Broker + Normalizer)
  → Keycloak-issued JWT → Kong → MCP Server → OpenFGA
```

### Federation Strategies

#### 1. LDAP/Active Directory (User Storage Provider)
**Use Case**: Corporate directory with 1,000-100,000 users

**Configuration**:
```python
{
  "providerId": "ldap",
  "config": {
    "connectionUrl": "ldap://ad.example.com:389",
    "usersDn": "OU=Users,DC=example,DC=com",
    "usernameLDAPAttribute": "sAMAccountName",
    "editMode": "READ_ONLY",
    "syncRegistrations": "false",
    "vendor": "ad"
  }
}
```

**Flow**: User logs in → Keycloak binds to LDAP → LDAP validates → Keycloak issues JWT

#### 2. SAML 2.0 (Identity Broker)
**Use Case**: Enterprise SSO (ADFS, Azure AD, Ping)

**Configuration**:
```python
{
  "alias": "adfs",
  "providerId": "saml",
  "config": {
    "singleSignOnServiceUrl": "https://adfs.example.com/adfs/ls/",
    "nameIDPolicyFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    "validateSignature": "true"
  }
}
```

**Flow**: User → Keycloak → Redirect to ADFS → SAML assertion → Keycloak → JWT

#### 3. OIDC (Identity Broker)
**Use Case**: Social login, cloud providers

**Providers**: Google, Microsoft, GitHub, Okta, OneLogin

**Configuration**:
```python
{
  "alias": "google",
  "providerId": "google",
  "config": {
    "clientId": "<google-client-id>",
    "clientSecret": "<secret>",
    "defaultScope": "openid profile email",
    "hostedDomain": "example.com"
  }
}
```

**Flow**: User → Keycloak → Redirect to Google → OIDC auth → Keycloak → JWT

### Attribute Mapping

**LDAP → Keycloak**:
```python
[
  {"ldap": "mail", "keycloak": "email"},
  {"ldap": "givenName", "keycloak": "firstName"},
  {"ldap": "sn", "keycloak": "lastName"},
  {"ldap": "department", "keycloak": "department"}
]
```

**SAML → Keycloak**:
```python
[
  {"saml": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
   "keycloak": "email"},
  {"saml": "http://schemas.xmlsoap.org/claims/Group",
   "keycloak": "groups"}
]
```

**OIDC → Keycloak**:
```python
[
  {"oidc": "email", "keycloak": "email"},
  {"oidc": "given_name", "keycloak": "firstName"},
  {"oidc": "family_name", "keycloak": "lastName"}
]
```

### Configuration

```bash
# Federation Enabled
KEYCLOAK_FEDERATION_ENABLED=true
KEYCLOAK_LDAP_ENABLED=true
KEYCLOAK_LDAP_URL=ldap://ad.example.com:389
KEYCLOAK_LDAP_BIND_DN=CN=svc_keycloak,OU=Service Accounts,DC=example,DC=com

# SAML Providers
KEYCLOAK_SAML_PROVIDERS=adfs,azure-ad
KEYCLOAK_SAML_ADFS_URL=https://adfs.example.com/adfs/ls/

# OIDC Providers
KEYCLOAK_OIDC_PROVIDERS=google,microsoft,github,okta
KEYCLOAK_OIDC_GOOGLE_CLIENT_ID=<client-id>
KEYCLOAK_OIDC_GOOGLE_DOMAIN=example.com  # Restrict to domain
```

## Consequences

### Positive Consequences
- Enterprise adoption (no forced migration)
- Consistent JWT output (all providers → same format)
- Centralized user view (federated users in Keycloak)
- Attribute normalization (consistent schema)
- Single authorization model (OpenFGA uses Keycloak JWTs)

### Negative Consequences
- Configuration complexity (multiple providers)
- LDAP/SAML expertise required
- Attribute mapping maintenance
- Performance (additional network hop)
- Provider outages impact authentication

### Mitigation Strategies
- Automated setup scripts for common providers
- Monitoring provider availability
- Fallback to local Keycloak users if provider down
- Connection pooling to LDAP/SAML endpoints

## Alternatives Considered

1. **Direct Integration**: Rejected - each app integrates with N providers (complexity)
2. **No Federation**: Rejected - forces user migration, adoption barrier
3. **Multiple Keycloak Realms**: Rejected - inconsistent tokens, complex management

## Implementation

**Setup Scripts**:
- `scripts/setup/setup_ldap_federation.py` - Configure LDAP
- `scripts/setup/setup_saml_idp.py` - Configure SAML providers
- `scripts/setup/setup_oidc_idp.py` - Configure OIDC providers

**Configuration Files**:
- `config/ldap_mappers.yaml` - LDAP attribute mapping
- `config/saml_mappers.yaml` - SAML claim mapping
- `config/oidc_providers.yaml` - OIDC provider configs

**Sync to OpenFGA**: Existing `sync_user_to_openfga()` handles federated users automatically (extracts roles from Keycloak JWT regardless of source).

## References

- Related ADRs: [ADR-0031](adr-0031-keycloak-authoritative-identity.md), [ADR-0032](adr-0032-jwt-standardization.md)
- External: [SAML 2.0](https://docs.oasis-open.org/security/saml/v2.0/), [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html), [LDAP RFC 4511](https://datatracker.ietf.org/doc/html/rfc4511)
