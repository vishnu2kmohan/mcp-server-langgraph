"""
Infrastructure Tests: GCP Terraform Module Configuration Validation

Tests validate that GCP Terraform modules have proper defaults to prevent
deployment failures:
- GKE Autopilot cluster configuration (dns_config, networking)
- Cloud SQL PostgreSQL configuration (database flags)
- Memorystore Redis configuration

TDD Approach:
- RED: Tests fail when modules have invalid defaults
- GREEN: Tests pass after implementing proper defaults
- REFACTOR: Improve code quality while maintaining test coverage

Issue Prevention:
- DNS domain must be "cluster.local" not empty string (causes badRequest)
- Database flags must be optional to avoid invalidFlagName errors
"""

import gc
import re
from pathlib import Path

import pytest

# Mark as unit test to ensure it runs in CI (infrastructure validation)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testgkeautopilotmodule")
class TestGKEAutopilotModuleDefaults:
    """
    Test GKE Autopilot module configuration defaults.

    Validates:
    - DNS domain default is "cluster.local" (not empty string)
    - Network configuration has valid defaults
    - Security posture configuration is valid
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def gke_module_path(self) -> Path:
        """Path to GKE Autopilot Terraform module."""
        return Path("terraform/modules/gke-autopilot")

    @pytest.fixture
    def gke_variables_tf(self, gke_module_path: Path) -> str:
        """Read GKE Autopilot variables.tf file."""
        variables_path = gke_module_path / "variables.tf"
        assert variables_path.exists(), f"Missing {variables_path}"
        return variables_path.read_text()

    @pytest.fixture
    def gke_main_tf(self, gke_module_path: Path) -> str:
        """Read GKE Autopilot main.tf file."""
        main_path = gke_module_path / "main.tf"
        assert main_path.exists(), f"Missing {main_path}"
        return main_path.read_text()

    def test_cluster_dns_domain_has_valid_default_when_explicit(self, gke_variables_tf: str):
        """
        Validate cluster_dns_domain has valid default for explicit DNS config.

        Requirement: When enable_explicit_dns_config=true, DNS domain should
        default to "cluster.local" (not empty string).
        Note: For Autopilot clusters, this is typically not used since
        enable_explicit_dns_config defaults to false.
        """
        pattern = r'variable\s+"cluster_dns_domain"\s*{[^}]*default\s*=\s*"([^"]*)"'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'cluster_dns_domain' not found in variables.tf"
        default_value = match.group(1)

        assert default_value == "cluster.local", (
            f"cluster_dns_domain default must be 'cluster.local' (got: '{default_value}'). "
            "When explicit DNS config is enabled, a valid domain is required."
        )

    def test_cluster_dns_provider_default(self, gke_variables_tf: str):
        """
        Validate cluster_dns_provider has valid default.

        Requirement: Must be CLOUD_DNS or PLATFORM_DEFAULT.
        """
        pattern = r'variable\s+"cluster_dns_provider"\s*{[^}]*default\s*=\s*"(\w+)"'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'cluster_dns_provider' not found"
        default_value = match.group(1)

        assert default_value in ["CLOUD_DNS", "PLATFORM_DEFAULT"], (
            f"cluster_dns_provider default must be 'CLOUD_DNS' or 'PLATFORM_DEFAULT' (got: '{default_value}')"
        )

    def test_cluster_dns_scope_default(self, gke_variables_tf: str):
        """
        Validate cluster_dns_scope has valid default.

        Requirement: Must be CLUSTER_SCOPE or VPC_SCOPE.
        """
        pattern = r'variable\s+"cluster_dns_scope"\s*{[^}]*default\s*=\s*"(\w+)"'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'cluster_dns_scope' not found"
        default_value = match.group(1)

        assert default_value in ["CLUSTER_SCOPE", "VPC_SCOPE"], (
            f"cluster_dns_scope default must be 'CLUSTER_SCOPE' or 'VPC_SCOPE' (got: '{default_value}')"
        )

    def test_release_channel_default(self, gke_variables_tf: str):
        """
        Validate release_channel has valid default.

        Requirement: Must be RAPID, REGULAR, STABLE, or UNSPECIFIED.
        """
        pattern = r'variable\s+"release_channel"\s*{[^}]*default\s*=\s*"(\w+)"'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'release_channel' not found"
        default_value = match.group(1)

        valid_channels = ["RAPID", "REGULAR", "STABLE", "UNSPECIFIED"]
        assert default_value in valid_channels, (
            f"release_channel default must be one of {valid_channels} (got: '{default_value}')"
        )

    def test_enable_explicit_dns_config_defaults_to_false(self, gke_variables_tf: str):
        """
        Validate enable_explicit_dns_config defaults to false.

        Requirement: For GKE Autopilot v1.25.9-gke.400+, Cloud DNS is pre-configured.
        Explicit dns_config causes badRequest errors on newer Autopilot clusters.
        Reference: https://cloud.google.com/kubernetes-engine/docs/how-to/cloud-dns
        """
        pattern = r'variable\s+"enable_explicit_dns_config"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_explicit_dns_config' not found"
        default_value = match.group(1)

        assert default_value == "false", (
            f"enable_explicit_dns_config must default to false (got: {default_value}). "
            "GKE Autopilot clusters v1.25.9+ have Cloud DNS pre-configured. "
            "Explicit dns_config causes 'badRequest' API errors."
        )

    def test_dns_config_block_is_conditional_in_main(self, gke_main_tf: str):
        """
        Validate dns_config block is conditional (dynamic) in main.tf.

        Requirement: dns_config should only be applied when enable_explicit_dns_config=true.
        For GKE Autopilot, Cloud DNS is automatically configured.
        """
        assert 'dynamic "dns_config"' in gke_main_tf, (
            "dns_config block must be dynamic (conditional) in GKE Autopilot main.tf. "
            "Explicit dns_config causes errors on Autopilot clusters v1.25.9+."
        )
        assert "enable_explicit_dns_config" in gke_main_tf, (
            "dns_config block must reference enable_explicit_dns_config variable."
        )

    def test_enable_security_posture_defaults_to_false(self, gke_variables_tf: str):
        """
        Validate enable_security_posture defaults to false.

        Requirement: For GKE Autopilot clusters v1.27+, security posture is
        enabled by default and managed automatically. Explicit configuration
        causes API conflicts (Error 400: badRequest).
        Reference: https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-security
        """
        pattern = r'variable\s+"enable_security_posture"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, gke_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_security_posture' not found"
        default_value = match.group(1)

        assert default_value == "false", (
            f"enable_security_posture must default to false (got: {default_value}). "
            "GKE Autopilot clusters v1.27+ have security posture enabled by default. "
            "Explicit security_posture_config causes 'badRequest' API errors."
        )

    def test_security_posture_config_is_conditional_in_main(self, gke_main_tf: str):
        """
        Validate security_posture_config block is conditional (dynamic) in main.tf.

        Requirement: security_posture_config should only be applied when
        enable_security_posture=true. For GKE Autopilot, security posture is
        automatically managed.
        """
        assert 'dynamic "security_posture_config"' in gke_main_tf, (
            "security_posture_config block must be dynamic (conditional) in GKE Autopilot main.tf. "
            "Explicit configuration may conflict with Autopilot's managed security features."
        )
        assert "enable_security_posture" in gke_main_tf, (
            "security_posture_config block must reference enable_security_posture variable."
        )

    def test_monitoring_config_is_in_ignore_changes(self, gke_main_tf: str):
        """
        Validate monitoring_config is in lifecycle ignore_changes.

        Requirement: GKE Autopilot clusters automatically enable many monitoring
        components (STORAGE, HPA, POD, DAEMONSET, DEPLOYMENT, STATEFULSET, etc.).
        Trying to modify these via Terraform causes "badRequest" API errors.
        The module must ignore monitoring_config changes.
        Reference: https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-monitoring
        """
        # Check that ignore_changes block exists and includes monitoring_config
        assert "ignore_changes" in gke_main_tf, "lifecycle ignore_changes block not found in GKE Autopilot main.tf."
        assert "monitoring_config" in gke_main_tf, (
            "monitoring_config must be in lifecycle ignore_changes. "
            "GKE Autopilot automatically manages monitoring components. "
            "Trying to modify them causes 'badRequest' API errors."
        )

    def test_logging_config_is_in_ignore_changes(self, gke_main_tf: str):
        """
        Validate logging_config is in lifecycle ignore_changes.

        Requirement: GKE Autopilot may adjust logging components automatically.
        To prevent Terraform from trying to revert these changes, logging_config
        should be ignored.
        """
        assert "ignore_changes" in gke_main_tf, "lifecycle ignore_changes block not found in GKE Autopilot main.tf."
        assert "logging_config" in gke_main_tf, (
            "logging_config should be in lifecycle ignore_changes. GKE Autopilot may adjust logging settings automatically."
        )

    def test_node_pool_is_in_ignore_changes(self, gke_main_tf: str):
        """
        Validate node_pool is in lifecycle ignore_changes.

        Requirement: GKE Autopilot manages node pools automatically.
        Terraform must not try to manage node pools for Autopilot clusters.
        """
        assert "node_pool" in gke_main_tf, (
            "node_pool must be in lifecycle ignore_changes. GKE Autopilot manages node pools automatically."
        )

    def test_lifecycle_ignore_changes_block_is_comprehensive(self, gke_main_tf: str):
        """
        Validate the lifecycle ignore_changes block includes all Autopilot-managed settings.

        Requirement: GKE Autopilot automatically manages several cluster settings.
        Terraform must ignore changes to these settings to prevent API errors.
        """
        required_ignore_items = [
            "node_pool",  # Autopilot manages node pools
            "initial_node_count",  # Autopilot manages node count
            "monitoring_config",  # Autopilot enables extra monitoring components
            "logging_config",  # Autopilot may adjust logging settings
        ]

        for item in required_ignore_items:
            assert item in gke_main_tf, (
                f"'{item}' must be in lifecycle ignore_changes. GKE Autopilot automatically manages this setting."
            )

    def test_backup_config_uses_all_namespaces_for_wildcard(self, gke_main_tf: str):
        """
        Validate backup configuration handles wildcard namespace correctly.

        Requirement: GKE Backup API doesn't accept '*' as a namespace value.
        When backing up all namespaces, use 'all_namespaces = true' instead.
        Using 'namespace = "*"' causes Error 400: INVALID_FIELD.
        """
        assert "all_namespaces" in gke_main_tf, (
            "backup_config must use 'all_namespaces' for full cluster backups. "
            "GKE Backup API doesn't accept '*' as a namespace value."
        )
        # Ensure the wildcard is handled with conditional logic
        assert 'backup_namespace == "*"' in gke_main_tf or "backup_namespace != " in gke_main_tf, (
            "backup_config must conditionally use all_namespaces vs selected_namespaces. "
            "Using namespace='*' causes API errors."
        )


@pytest.mark.xdist_group(name="testcloudsqlmodule")
class TestCloudSQLModuleDefaults:
    """
    Test Cloud SQL PostgreSQL module configuration defaults.

    Validates:
    - Database flags are optional (enable_default_database_flags)
    - Query insights configuration is valid
    - Security defaults are appropriate
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def cloudsql_module_path(self) -> Path:
        """Path to Cloud SQL Terraform module."""
        return Path("terraform/modules/cloudsql")

    @pytest.fixture
    def cloudsql_variables_tf(self, cloudsql_module_path: Path) -> str:
        """Read Cloud SQL variables.tf file."""
        variables_path = cloudsql_module_path / "variables.tf"
        assert variables_path.exists(), f"Missing {variables_path}"
        return variables_path.read_text()

    @pytest.fixture
    def cloudsql_main_tf(self, cloudsql_module_path: Path) -> str:
        """Read Cloud SQL main.tf file."""
        main_path = cloudsql_module_path / "main.tf"
        assert main_path.exists(), f"Missing {main_path}"
        return main_path.read_text()

    def test_enable_default_database_flags_variable_exists(self, cloudsql_variables_tf: str):
        """
        Validate enable_default_database_flags variable exists.

        Requirement: Database flags should be optional to avoid invalidFlagName errors.
        """
        assert 'variable "enable_default_database_flags"' in cloudsql_variables_tf, (
            "Missing 'enable_default_database_flags' variable. "
            "Required to control whether default database flags are applied. "
            "Some flags may not be supported in all PostgreSQL versions."
        )

    def test_enable_default_database_flags_defaults_to_false(self, cloudsql_variables_tf: str):
        """
        Validate enable_default_database_flags defaults to false.

        Requirement: Default database flags should be disabled by default
        to prevent invalidFlagName errors on instance creation.
        """
        pattern = r'variable\s+"enable_default_database_flags"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, cloudsql_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_default_database_flags' not found with default value"
        default_value = match.group(1)

        assert default_value == "false", (
            f"enable_default_database_flags must default to false (got: {default_value}). "
            "This prevents invalidFlagName errors when creating Cloud SQL instances. "
            "Set to true explicitly if you need logging/performance flags."
        )

    def test_database_flags_are_conditional_in_main(self, cloudsql_main_tf: str):
        """
        Validate database_flags block is conditional in main.tf.

        Requirement: Database flags should only be applied when enabled.
        """
        # Check that the dynamic block uses enable_default_database_flags
        assert "enable_default_database_flags" in cloudsql_main_tf, (
            "main.tf must reference 'enable_default_database_flags' variable. "
            "Database flags should be conditional to prevent invalidFlagName errors."
        )

    def test_postgresql_version_default(self, cloudsql_variables_tf: str):
        """
        Validate PostgreSQL version has valid default.

        Requirement: Must be a supported PostgreSQL version.
        """
        pattern = r'variable\s+"database_version"\s*{[^}]*default\s*=\s*"(POSTGRES_\d+)"'
        match = re.search(pattern, cloudsql_variables_tf, re.DOTALL)

        assert match, "Variable 'database_version' not found with default"
        default_value = match.group(1)

        valid_versions = ["POSTGRES_11", "POSTGRES_12", "POSTGRES_13", "POSTGRES_14", "POSTGRES_15", "POSTGRES_16"]
        assert default_value in valid_versions, (
            f"database_version default must be a valid PostgreSQL version (got: '{default_value}')"
        )

    def test_high_availability_default(self, cloudsql_variables_tf: str):
        """
        Validate high_availability defaults to true for production readiness.

        Requirement: HA should be enabled by default for reliability.
        """
        pattern = r'variable\s+"high_availability"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, cloudsql_variables_tf, re.DOTALL)

        assert match, "Variable 'high_availability' not found"
        default_value = match.group(1)

        assert default_value == "true", (
            f"high_availability should default to true (got: {default_value}). "
            "Production environments require regional HA configuration."
        )


@pytest.mark.xdist_group(name="testmemorystoremodule")
class TestMemorystoreModuleDefaults:
    """
    Test Memorystore Redis module configuration defaults.

    Validates:
    - Transit encryption enabled
    - Auth enabled
    - HA tier default
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def memorystore_module_path(self) -> Path:
        """Path to Memorystore Terraform module."""
        return Path("terraform/modules/memorystore")

    @pytest.fixture
    def memorystore_variables_tf(self, memorystore_module_path: Path) -> str:
        """Read Memorystore variables.tf file."""
        variables_path = memorystore_module_path / "variables.tf"
        if not variables_path.exists():
            pytest.skip(f"Memorystore module not found at {variables_path}")
        return variables_path.read_text()

    def test_enable_transit_encryption_default(self, memorystore_variables_tf: str):
        """
        Validate transit encryption defaults to true.

        Requirement: Data in transit should be encrypted by default.
        """
        pattern = r'variable\s+"enable_transit_encryption"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, memorystore_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_transit_encryption' not found"
        default_value = match.group(1)

        assert default_value == "true", (
            f"enable_transit_encryption should default to true (got: {default_value}). "
            "Transit encryption is required for security compliance."
        )

    def test_enable_auth_default(self, memorystore_variables_tf: str):
        """
        Validate auth defaults to true.

        Requirement: Authentication should be enabled by default.
        """
        pattern = r'variable\s+"enable_auth"\s*{[^}]*default\s*=\s*(\w+)'
        match = re.search(pattern, memorystore_variables_tf, re.DOTALL)

        assert match, "Variable 'enable_auth' not found"
        default_value = match.group(1)

        assert default_value == "true", (
            f"enable_auth should default to true (got: {default_value}). Redis authentication is required for security."
        )


@pytest.mark.xdist_group(name="testgcpvpcmodule")
class TestGCPVPCModuleDefaults:
    """
    Test GCP VPC module configuration defaults.

    Validates:
    - Private service connection configuration
    - Flow logs configuration
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def vpc_module_path(self) -> Path:
        """Path to GCP VPC Terraform module."""
        return Path("terraform/modules/gcp-vpc")

    @pytest.fixture
    def vpc_variables_tf(self, vpc_module_path: Path) -> str:
        """Read VPC variables.tf file."""
        variables_path = vpc_module_path / "variables.tf"
        if not variables_path.exists():
            pytest.skip(f"VPC module not found at {variables_path}")
        return variables_path.read_text()

    def test_enable_private_service_connection_variable_exists(self, vpc_variables_tf: str):
        """
        Validate private service connection variable exists.

        Requirement: Required for Cloud SQL and Memorystore private access.
        """
        assert 'variable "enable_private_service_connection"' in vpc_variables_tf, (
            "Missing 'enable_private_service_connection' variable. "
            "Required for Cloud SQL and Memorystore to connect via private IP."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
