# Docker Configuration

Docker and container-related configuration files.

## Files

### Development & Testing
- `docker-compose.dev.yml` - Development-specific Docker Compose overrides
- `docker-compose.test.yml` - Integration test infrastructure (PostgreSQL, OpenFGA, Redis, etc.)

### Main Files (in root)
The primary Docker files remain in the root directory following standard conventions:
- `../Dockerfile` - Main container build configuration
- `../docker-compose.yml` - Standard Docker Compose setup with all services
- `../.dockerignore` - Files to exclude from Docker build context

## Usage

### Development Environment
```bash
# Start development stack
docker-compose -f docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

### Production Environment
```bash
# Start production stack
docker-compose up -d
```

---

See also:
- [Deployment Guide](../docs/deployment/) - Complete deployment documentation
- [Makefile](../Makefile) - Docker command shortcuts (`make build`, `make up`, etc.)
