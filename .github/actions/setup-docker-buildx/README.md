# Setup Docker Buildx Composite Action

Composite action for setting up Docker Buildx with optional QEMU support for multiplatform builds.

## Features

- ✅ **Flexible QEMU support**: Enable/disable QEMU based on build requirements
- ✅ **Configurable Buildx**: Custom driver options and inline configuration
- ✅ **Version pinning**: Specify exact Buildx version or use latest
- ✅ **Standardized setup**: Consistent Docker Buildx configuration across all workflows

## Usage

### Single-platform builds (Buildx only)

```yaml
- name: Set up Docker Build Environment
  uses: ./.github/actions/setup-docker-buildx
  # No parameters needed - defaults to single-platform setup
```

### Multiplatform builds (QEMU + Buildx)

```yaml
- name: Set up Docker Build Environment
  uses: ./.github/actions/setup-docker-buildx
  with:
    enable-qemu: 'true'  # Enable QEMU for linux/amd64 and linux/arm64
```

### Advanced configuration

```yaml
- name: Set up Docker Build Environment
  uses: ./.github/actions/setup-docker-buildx
  with:
    enable-qemu: 'true'
    buildx-version: 'v0.11.2'  # Pin specific version
    driver-opts: 'network=host'  # Custom driver options
    config-inline: |
      [worker.oci]
        max-parallelism = 4
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `enable-qemu` | Enable QEMU for multiplatform builds | No | `false` |
| `buildx-version` | Docker Buildx version (e.g., v0.11.2, latest) | No | `latest` |
| `driver-opts` | Buildx driver options (e.g., network=host) | No | `''` |
| `config-inline` | Inline Buildx configuration | No | `''` |

## Examples

### CI Workflow (single-platform)

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker
        uses: ./.github/actions/setup-docker-buildx

      - name: Build image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
```

### Release Workflow (multiplatform)

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        platform: [linux/amd64, linux/arm64]
    steps:
      - uses: actions/checkout@v5

      - name: Set up Docker (multiplatform)
        uses: ./.github/actions/setup-docker-buildx
        with:
          enable-qemu: 'true'

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          platforms: ${{ matrix.platform }}
          push: true
```

## Benefits

1. **Reduced duplication**: Consolidates QEMU + Buildx setup from 7+ workflows
2. **Consistent versions**: All workflows use the same action versions
3. **Easier maintenance**: Update once, apply everywhere
4. **Faster workflows**: Reusable caching strategies

## Related Workflows

This composite action is used in:
- `.github/workflows/ci.yaml` - CI/CD pipeline builds
- `.github/workflows/release.yaml` - Release multiplatform builds
- `.github/workflows/deploy-staging-gke.yaml` - Staging deployments
- `.github/workflows/deploy-production-gke.yaml` - Production deployments

## Maintenance

**Action versions**:
- QEMU: `docker/setup-qemu-action@v3.7.0`
- Buildx: `docker/setup-buildx-action@v3.11.1`

To update action versions, edit `.github/actions/setup-docker-buildx/action.yaml`.
