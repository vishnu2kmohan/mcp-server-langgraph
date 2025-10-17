# Run All Validations

Execute comprehensive validation of all deployment configurations and schemas.

## Validation Steps

1. **OpenAPI Schema Validation**
   ```bash
   make validate-openapi
   ```
   Validates:
   - Schema correctness
   - Breaking change detection
   - Endpoint documentation completeness

2. **Deployment Configuration Validation**
   ```bash
   make validate-deployments
   ```
   Validates:
   - Python validation script checks
   - All deployment platform configurations

3. **Docker Compose Validation**
   ```bash
   make validate-docker-compose
   ```
   Validates:
   - YAML syntax
   - Service configuration
   - Network definitions

4. **Helm Chart Validation**
   ```bash
   make validate-helm
   ```
   Validates:
   - Chart linting
   - Template rendering
   - Values schema

5. **Kustomize Overlays Validation**
   ```bash
   make validate-kustomize
   ```
   Validates:
   - Dev overlay
   - Staging overlay
   - Production overlay

## Comprehensive Validation

Run all validations at once:
```bash
make validate-all
```

## Summary

Provide:
- Validation results for each component
- Any errors or warnings found
- File references for issues discovered
- Recommendations for fixes
