# Debug Authentication Issues

Comprehensive authentication and authorization debugging workflow.

## Debug Steps

1. **Check Infrastructure Status**
   ```bash
   make health-check
   ```
   Verify:
   - OpenFGA is running (port 8080)
   - Redis is running (port 6379)
   - Keycloak is running (port 8081)
   - PostgreSQL is running (port 5432)

2. **Test OpenFGA Authorization**
   ```bash
   make test-auth
   ```
   Runs example OpenFGA usage script to verify:
   - Connection to OpenFGA
   - Permission checks
   - Tuple writes and reads

3. **Review Authentication Logs**
   ```bash
   docker compose logs -f --tail=100 | grep -i "auth\|jwt\|token"
   ```

4. **Check Session Management**
   - Verify Redis connection
   - Check session store configuration
   - Review session metrics

5. **Validate OpenFGA Configuration**
   - Check OPENFGA_STORE_ID in .env
   - Check OPENFGA_MODEL_ID in .env
   - Verify authorization model is loaded

## Common Issues

### Issue: JWT Token Validation Fails
- Check JWT_SECRET_KEY is set correctly
- Verify token expiration settings
- Check for clock skew between services

### Issue: OpenFGA Permission Denied
- Verify tuples are written correctly
- Check user-role-resource relationships
- Review role mappings in config/role_mappings.yaml

### Issue: Session Not Found
- Check Redis connectivity
- Verify session TTL settings
- Review session store backend configuration

## Interactive Debugging

1. **OpenFGA Playground**: http://localhost:3001
2. **Prometheus Metrics**: http://localhost:9090 (search for auth_* metrics)
3. **Grafana Dashboards**: http://localhost:3000 (Authentication dashboard)

## Summary

Provide:
- Status of all authentication services
- Specific issues identified
- File references for configuration problems
- Step-by-step remediation plan
