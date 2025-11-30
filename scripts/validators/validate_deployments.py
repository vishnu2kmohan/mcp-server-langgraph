#!/usr/bin/env python3
"""
Deployment Configuration Validation Script

Validates all deployment configurations (Docker Compose, Kubernetes, Helm) to ensure:
- YAML syntax correctness
- Required fields are present
- Configuration consistency across platforms
- Secret references are valid
- Resource limits are set
- Health checks are configured
"""

import sys
from pathlib import Path
from typing import Any

import yaml


class DeploymentValidator:
    """Validates deployment configurations across multiple platforms."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating deployment configurations...\n")

        # Validate YAML syntax
        self.validate_yaml_syntax()

        # Validate Kubernetes manifests
        self.validate_kubernetes_manifests()

        # Validate Docker Compose
        self.validate_docker_compose()

        # Validate Helm chart
        self.validate_helm_chart()
        self.validate_helm_lint()

        # Validate Kustomize overlays
        self.validate_kustomize_build()

        # Validate configuration consistency
        self.validate_config_consistency()

        # Validate CORS security
        self.validate_cors_security()

        # Print results
        self.print_results()

        return len(self.errors) == 0

    def validate_helm_lint(self):
        """Run helm lint."""
        print("\n⎈  Running Helm lint...")
        import shutil
        import subprocess

        if not shutil.which("helm"):
            print("  ⚠️  Helm not installed, skipping lint")
            return

        chart_path = self.project_root / "deployments/helm/mcp-server-langgraph"
        try:
            subprocess.run(["helm", "lint", str(chart_path)], capture_output=True, text=True, check=True)
            print("  ✓ Helm lint passed")
        except subprocess.CalledProcessError as e:
            # Filter out common non-critical warnings if needed, or just report error
            # The shell script grep'd out "bad character", let's report output on failure
            self.errors.append(f"Helm lint failed:\n{e.stdout}\n{e.stderr}")

    def validate_kustomize_build(self):
        """Run kustomize build on overlays."""
        print("\n🔧 Validating Kustomize overlays...")
        import shutil
        import subprocess

        # Prefer kustomize, fall back to kubectl kustomize
        cmd = []
        if shutil.which("kustomize"):
            cmd = ["kustomize", "build"]
        elif shutil.which("kubectl"):
            cmd = ["kubectl", "kustomize"]
        else:
            print("  ⚠️  Kustomize/kubectl not installed, skipping build")
            return

        overlays_dir = self.project_root / "deployments/overlays"
        if not overlays_dir.exists():
            return

        for overlay in overlays_dir.iterdir():
            if overlay.is_dir() and (overlay / "kustomization.yaml").exists():
                try:
                    subprocess.run(cmd + [str(overlay)], capture_output=True, check=True)
                    print(f"  ✓ Overlay {overlay.name} OK")
                except subprocess.CalledProcessError:
                    self.errors.append(f"Kustomize build failed for overlay: {overlay.name}")

    def validate_cors_security(self):
        """Validate CORS security in Kong config."""
        print("\n🔒 Validating CORS security...")
        kong_config = self.project_root / "deployments/kong/kong.yaml"
        if not kong_config.exists():
            return

        try:
            content = kong_config.read_text()
            # Check for insecure CORS: credentials=true AND origins="*"
            # Simple string check (regex could be better but this matches shell script intent)
            if "credentials: true" in content and ('"*"' in content or "'*'" in content):
                # Need to check if they are in the same context/plugin config
                # But for now, replicate shell script logic which grep'd globally
                # "Kong: wildcard CORS with credentials"
                # Refined check: Check if both exist in file (broad check like shell script)
                self.errors.append("Kong: wildcard CORS with credentials detected (insecure)")
            else:
                print("  ✓ CORS configuration secure")
        except Exception as e:
            self.errors.append(f"Failed to check CORS security: {e}")

    def validate_yaml_syntax(self):
        """Validate YAML syntax for all deployment files."""
        print("📄 Validating YAML syntax...")

        # Required files (must exist)
        required_files = [
            # Docker Compose
            "docker/docker-compose.yml",
            "docker/docker-compose.dev.yml",
            # Helm
            "deployments/helm/mcp-server-langgraph/Chart.yaml",
            "deployments/helm/mcp-server-langgraph/values.yaml",
        ]

        # Optional files (Kubernetes base - project uses Helm/Kustomize overlays)
        optional_files = [
            "deployments/kubernetes/base/deployment.yaml",
            "deployments/kubernetes/base/service.yaml",
            "deployments/kubernetes/base/configmap.yaml",
            "deployments/kubernetes/base/secret.yaml",
            "deployments/kubernetes/base/keycloak-deployment.yaml",
            "deployments/kubernetes/base/keycloak-service.yaml",
            "deployments/kubernetes/base/redis-session-deployment.yaml",
            "deployments/kubernetes/base/redis-session-service.yaml",
            "deployments/kustomize/base/kustomization.yaml",
        ]

        # Validate required files
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.errors.append(f"Required file not found: {file_path}")
                continue

            try:
                with open(full_path) as f:
                    # Handle multi-document YAML files
                    list(yaml.safe_load_all(f))
                print(f"  ✓ {file_path}")
            except yaml.YAMLError as e:
                self.errors.append(f"Invalid YAML in {file_path}: {e}")

        # Validate optional files (only if they exist)
        for file_path in optional_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                # Skip silently - these are optional
                continue

            try:
                with open(full_path) as f:
                    # Handle multi-document YAML files
                    list(yaml.safe_load_all(f))
                print(f"  ✓ {file_path}")
            except yaml.YAMLError as e:
                self.errors.append(f"Invalid YAML in {file_path}: {e}")

    def validate_kubernetes_manifests(self):
        """Validate Kubernetes manifest configurations."""
        print("\n☸️  Validating Kubernetes manifests...")

        # Check if base directory exists
        base_dir = self.project_root / "deployments/kubernetes/base"
        if not base_dir.exists():
            print("  ℹ️  Kubernetes base manifests not found (project uses Helm/Kustomize overlays)")
            return

        # Validate main deployment
        deployment = self._load_yaml_optional("deployments/kubernetes/base/deployment.yaml")
        if deployment:
            self._check_deployment(deployment)

        # Validate ConfigMap
        configmap = self._load_yaml_optional("deployments/kubernetes/base/configmap.yaml")
        if configmap:
            self._check_configmap(configmap)

        # Validate Secret
        secret = self._load_yaml_optional("deployments/kubernetes/base/secret.yaml")
        if secret:
            self._check_secret(secret)

        # Validate Keycloak deployment
        keycloak_deploy = self._load_yaml_optional("deployments/kubernetes/base/keycloak-deployment.yaml")
        if keycloak_deploy:
            self._check_keycloak_deployment(keycloak_deploy)

        # Validate Redis deployment
        redis_docs = self._load_yaml_all_optional("deployments/kubernetes/base/redis-session-deployment.yaml")
        if redis_docs:
            self._check_redis_deployment(redis_docs)

    def _check_deployment(self, deployment: dict[str, Any]):
        """Check main application deployment."""
        spec = deployment.get("spec", {})
        template = spec.get("template", {})
        containers = template.get("spec", {}).get("containers", [])

        if not containers:
            self.errors.append("Main deployment has no containers defined")
            return

        container = containers[0]

        # Check resource limits
        resources = container.get("resources", {})
        if not resources.get("limits"):
            self.warnings.append("Main deployment: No resource limits set")

        # Check health probes
        if not container.get("livenessProbe"):
            self.errors.append("Main deployment: No liveness probe configured")
        if not container.get("readinessProbe"):
            self.errors.append("Main deployment: No readiness probe configured")
        if not container.get("startupProbe"):
            self.warnings.append("Main deployment: No startup probe configured")

        # Check environment variables
        env_vars = {env.get("name") for env in container.get("env", [])}
        required_env = {
            "AUTH_PROVIDER",
            "AUTH_MODE",
            "KEYCLOAK_SERVER_URL",
            "SESSION_BACKEND",
            "REDIS_URL",
        }
        missing_env = required_env - env_vars
        if missing_env:
            self.warnings.append(f"Main deployment: Missing environment variables: {missing_env}")

        print("  ✓ Main deployment validated")

    def _check_configmap(self, configmap: dict[str, Any]):
        """Check ConfigMap configuration."""
        data = configmap.get("data", {})

        required_keys = {
            "auth_provider",
            "auth_mode",
            "keycloak_server_url",
            "session_backend",
            "redis_url",
            "llm_provider",
            "model_name",
        }

        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            self.errors.append(f"ConfigMap missing keys: {missing_keys}")
        else:
            print(f"  ✓ ConfigMap validated ({len(data)} keys)")

    def _check_secret(self, secret: dict[str, Any]):
        """Check Secret template."""
        string_data = secret.get("stringData", {})

        required_secrets = {
            "anthropic-api-key",
            "jwt-secret-key",
            "keycloak-client-secret",
            "redis-password",
            "postgres-password",
        }

        missing_secrets = required_secrets - set(string_data.keys())
        if missing_secrets:
            self.errors.append(f"Secret template missing keys: {missing_secrets}")
        else:
            print(f"  ✓ Secret template validated ({len(string_data)} keys)")

    def _check_keycloak_deployment(self, deployment: dict[str, Any]):
        """Check Keycloak deployment configuration."""
        spec = deployment.get("spec", {})

        # Check replicas for HA
        replicas = spec.get("replicas", 1)
        if replicas < 2:
            self.warnings.append("Keycloak deployment: Less than 2 replicas (HA recommended)")

        # Check init containers
        init_containers = spec.get("template", {}).get("spec", {}).get("initContainers", [])
        if not init_containers:
            self.warnings.append("Keycloak deployment: No init containers for PostgreSQL wait")

        print("  ✓ Keycloak deployment validated")

    def _check_redis_deployment(self, docs: list[dict[str, Any]]):
        """Check Redis deployment configuration."""
        # Find the Deployment document
        deployment = next((d for d in docs if d.get("kind") == "Deployment"), None)
        if not deployment:
            self.errors.append("Redis: No Deployment found in manifests")
            return

        spec = deployment.get("spec", {})
        containers = spec.get("template", {}).get("spec", {}).get("containers", [])

        if containers:
            container = containers[0]
            # Check password configuration
            env_vars = {env.get("name") for env in container.get("env", [])}
            if "REDIS_PASSWORD" not in env_vars:
                self.warnings.append("Redis: No password configured")

        print("  ✓ Redis deployment validated")

    def validate_docker_compose(self):
        """Validate Docker Compose configuration."""
        print("\n🐳 Validating Docker Compose...")

        compose = self._load_yaml("docker/docker-compose.yml")
        if not compose:
            return

        services = compose.get("services", {})

        # Check required infrastructure services
        # Note: "agent" service is deployed separately via Kubernetes/Helm
        required_services = {"keycloak", "redis", "openfga", "postgres"}
        missing_services = required_services - set(services.keys())
        if missing_services:
            self.errors.append(f"Docker Compose missing services: {missing_services}")
        else:
            print(f"  ✓ All required infrastructure services present ({len(services)} total)")

        # Check agent service
        agent = services.get("agent", {})
        if agent:
            # Check volume mounts
            volumes = agent.get("volumes", [])
            if not any("src/mcp_server_langgraph" in str(v) for v in volumes):
                self.errors.append("Docker Compose agent: Source code not mounted correctly")
            else:
                print("  ✓ Agent service volume mounts correct")

    def validate_helm_chart(self):
        """Validate Helm chart configuration."""
        print("\n⎈  Validating Helm chart...")

        chart = self._load_yaml("deployments/helm/mcp-server-langgraph/Chart.yaml")
        values = self._load_yaml("deployments/helm/mcp-server-langgraph/values.yaml")

        if not chart or not values:
            return

        # Check dependencies
        dependencies = chart.get("dependencies", [])
        required_deps = {"openfga", "postgresql", "redis", "keycloak"}
        dep_names = {dep.get("name") for dep in dependencies}

        missing_deps = required_deps - dep_names
        if missing_deps:
            self.errors.append(f"Helm chart missing dependencies: {missing_deps}")
        else:
            print(f"  ✓ All dependencies defined ({len(dependencies)} total)")

        # Check values
        config = values.get("config", {})
        if not config:
            self.errors.append("Helm values: No config section found")
        else:
            required_config = {
                "authProvider",
                "authMode",
                "keycloakServerUrl",
                "sessionBackend",
            }
            missing_config = required_config - set(config.keys())
            if missing_config:
                self.warnings.append(f"Helm values: Missing config keys: {missing_config}")
            else:
                print("  ✓ Helm values validated")

    def validate_config_consistency(self):
        """Validate configuration consistency across platforms."""
        print("\n🔗 Validating configuration consistency...")

        # Load configurations
        k8s_configmap = self._load_yaml_optional("deployments/kubernetes/base/configmap.yaml")
        helm_values = self._load_yaml("deployments/helm/mcp-server-langgraph/values.yaml")

        if not k8s_configmap or not helm_values:
            print("  ℹ️  Skipping consistency check (Kubernetes base manifests not used)")
            return

        k8s_data = k8s_configmap.get("data", {})
        helm_config = helm_values.get("config", {})

        # Check key consistency (converting camelCase to snake_case for Helm)
        helm_keys = {self._camel_to_snake(k) for k in helm_config.keys()}
        k8s_keys = set(k8s_data.keys())

        # Core keys that should be in both
        core_keys = {
            "auth_provider",
            "auth_mode",
            "session_backend",
            "llm_provider",
            "model_name",
        }

        k8s_missing = core_keys - k8s_keys
        helm_missing = core_keys - helm_keys

        if k8s_missing:
            self.warnings.append(f"K8s ConfigMap missing core keys: {k8s_missing}")
        if helm_missing:
            self.warnings.append(f"Helm values missing core keys (as camelCase): {helm_missing}")

        if not k8s_missing and not helm_missing:
            print("  ✓ Configuration consistency validated")

    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def _load_yaml(self, relative_path: str) -> dict[str, Any] | None:
        """Load a single-document YAML file."""
        try:
            with open(self.project_root / relative_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load {relative_path}: {e}")
            return None

    def _load_yaml_all(self, relative_path: str) -> list[dict[str, Any]] | None:
        """Load a multi-document YAML file."""
        try:
            with open(self.project_root / relative_path) as f:
                return list(yaml.safe_load_all(f))
        except Exception as e:
            self.errors.append(f"Failed to load {relative_path}: {e}")
            return None

    def _load_yaml_optional(self, relative_path: str) -> dict[str, Any] | None:
        """Load a single-document YAML file (optional - no error if missing)."""
        full_path = self.project_root / relative_path
        if not full_path.exists():
            return None
        try:
            with open(full_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load {relative_path}: {e}")
            return None

    def _load_yaml_all_optional(self, relative_path: str) -> list[dict[str, Any]] | None:
        """Load a multi-document YAML file (optional - no error if missing)."""
        full_path = self.project_root / relative_path
        if not full_path.exists():
            return None
        try:
            with open(full_path) as f:
                return list(yaml.safe_load_all(f))
        except Exception as e:
            self.errors.append(f"Failed to load {relative_path}: {e}")
            return None

    def print_results(self):
        """Print validation results."""
        print("\n" + "=" * 70)
        print("VALIDATION RESULTS")
        print("=" * 70)

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ All validation checks passed!")

        print("=" * 70)


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent

    validator = DeploymentValidator(project_root)
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
