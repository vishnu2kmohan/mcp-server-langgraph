# Complete Environment Setup

Execute the complete development environment setup from scratch.

## Setup Steps

1. **Install Dependencies**
   ```bash
   make install-dev
   ```
   Installs:
   - Python dependencies via uv
   - Development tools
   - Test dependencies

2. **Start Infrastructure**
   ```bash
   make setup-infra
   ```
   Starts Docker Compose services:
   - OpenFGA (authorization)
   - PostgreSQL (OpenFGA storage)
   - Keycloak (SSO/authentication)
   - Redis (session storage)
   - Jaeger (distributed tracing)
   - Prometheus (metrics)
   - Grafana (visualization)
   - Qdrant (vector database)

3. **Configure OpenFGA**
   ```bash
   make setup-openfga
   ```
   Sets up:
   - Creates OpenFGA store
   - Loads authorization model
   - Displays OPENFGA_STORE_ID and OPENFGA_MODEL_ID

4. **Configure Keycloak**
   ```bash
   make setup-keycloak
   ```
   Sets up:
   - Creates realm and clients
   - Configures users and roles
   - Displays KEYCLOAK_CLIENT_SECRET

5. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```
   Then manually update .env with:
   - OPENFGA_STORE_ID (from step 3)
   - OPENFGA_MODEL_ID (from step 3)
   - KEYCLOAK_CLIENT_SECRET (from step 4)
   - GOOGLE_API_KEY (from https://aistudio.google.com/apikey)
   - Optional: ANTHROPIC_API_KEY, OPENAI_API_KEY

6. **Restart Services**
   ```bash
   docker-compose restart agent
   ```

7. **Verify Setup**
   ```bash
   make health-check
   make test-unit
   ```

## Quick Start Alternative

For a faster automated setup:
```bash
make dev-setup
```

This runs steps 1-4 automatically, but you'll still need to:
- Update .env with IDs/secrets
- Restart agent service

## Post-Setup Verification

1. **Check Services**
   - OpenFGA: http://localhost:8080
   - OpenFGA Playground: http://localhost:3001
   - Keycloak: http://localhost:8081 (admin/admin)
   - Jaeger: http://localhost:16686
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

2. **Run Tests**
   ```bash
   make test-unit
   ```

3. **Start Server**
   ```bash
   make run-streamable
   ```

## Troubleshooting

### Issue: Services Not Starting
- Check Docker is running
- Check port conflicts (8080, 5432, 8081, 6379, 16686, 9090, 3000, 6333)
- Review logs: `docker compose logs`

### Issue: OpenFGA Setup Fails
- Ensure PostgreSQL is healthy first
- Check OPENFGA_API_URL is correct
- Verify network connectivity

### Issue: Tests Failing
- Ensure .env is properly configured
- Check infrastructure is running
- Review test output for specific errors

## Summary

Provide:
- Status of each setup step
- All service URLs and credentials
- Environment variables that need manual configuration
- Next steps for getting started with development
