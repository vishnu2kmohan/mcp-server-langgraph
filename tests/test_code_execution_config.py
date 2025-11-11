"""
Unit tests for code execution configuration settings

Tests Settings class code execution configuration following TDD best practices.
These tests should FAIL until config.py is updated with execution settings.
"""

import pytest

# This import will work but settings won't have execution fields yet
from mcp_server_langgraph.core.config import Settings


@pytest.mark.unit
class TestCodeExecutionSettings:
    """Test code execution configuration settings"""

    def test_code_execution_disabled_by_default(self):
        """Test that code execution is disabled by default (security)"""
        settings = Settings()
        assert hasattr(settings, "enable_code_execution")
        assert settings.enable_code_execution is False

    def test_code_execution_backend_default(self):
        """Test default code execution backend"""
        settings = Settings()
        assert hasattr(settings, "code_execution_backend")
        # Should auto-detect or default to docker-engine
        assert settings.code_execution_backend in ["docker-engine", "kubernetes", "process"]

    def test_code_execution_timeout_default(self):
        """Test default code execution timeout"""
        settings = Settings()
        assert hasattr(settings, "code_execution_timeout")
        assert settings.code_execution_timeout == 30  # 30 seconds default

    def test_code_execution_memory_limit_default(self):
        """Test default memory limit"""
        settings = Settings()
        assert hasattr(settings, "code_execution_memory_limit_mb")
        assert settings.code_execution_memory_limit_mb == 512  # 512MB default

    def test_code_execution_cpu_quota_default(self):
        """Test default CPU quota"""
        settings = Settings()
        assert hasattr(settings, "code_execution_cpu_quota")
        assert settings.code_execution_cpu_quota == 1.0  # 1 CPU default

    def test_code_execution_disk_quota_default(self):
        """Test default disk quota"""
        settings = Settings()
        assert hasattr(settings, "code_execution_disk_quota_mb")
        assert settings.code_execution_disk_quota_mb == 100  # 100MB default

    def test_code_execution_max_processes_default(self):
        """Test default max processes"""
        settings = Settings()
        assert hasattr(settings, "code_execution_max_processes")
        assert settings.code_execution_max_processes == 1  # 1 process default

    def test_code_execution_network_mode_default(self):
        """Test default network mode"""
        settings = Settings()
        assert hasattr(settings, "code_execution_network_mode")
        assert settings.code_execution_network_mode == "none"  # Maximum isolation by default (security-first)

    def test_code_execution_allowed_domains_default(self):
        """Test default allowed domains"""
        settings = Settings()
        assert hasattr(settings, "code_execution_allowed_domains")
        assert isinstance(settings.code_execution_allowed_domains, list)
        # Empty by default (no network access)
        assert len(settings.code_execution_allowed_domains) == 0

    def test_code_execution_allowed_imports_default(self):
        """Test default allowed imports"""
        settings = Settings()
        assert hasattr(settings, "code_execution_allowed_imports")
        assert isinstance(settings.code_execution_allowed_imports, list)
        # Should have safe defaults
        assert "json" in settings.code_execution_allowed_imports
        assert "math" in settings.code_execution_allowed_imports
        # Should not have dangerous modules
        assert "os" not in settings.code_execution_allowed_imports
        assert "subprocess" not in settings.code_execution_allowed_imports

    def test_docker_image_default(self):
        """Test default Docker image"""
        settings = Settings()
        assert hasattr(settings, "code_execution_docker_image")
        assert "python" in settings.code_execution_docker_image.lower()
        # Should use a specific Python version
        assert "3.12" in settings.code_execution_docker_image or "3.11" in settings.code_execution_docker_image

    def test_docker_socket_path_default(self):
        """Test default Docker socket path"""
        settings = Settings()
        assert hasattr(settings, "code_execution_docker_socket")
        assert settings.code_execution_docker_socket == "/var/run/docker.sock"

    def test_kubernetes_namespace_default(self):
        """Test default Kubernetes namespace"""
        settings = Settings()
        assert hasattr(settings, "code_execution_k8s_namespace")
        assert settings.code_execution_k8s_namespace == "default"

    def test_kubernetes_job_ttl_default(self):
        """Test default Kubernetes job TTL"""
        settings = Settings()
        assert hasattr(settings, "code_execution_k8s_job_ttl")
        assert settings.code_execution_k8s_job_ttl == 300  # 5 minutes


@pytest.mark.unit
class TestCodeExecutionSettingsFromEnv:
    """Test code execution settings from environment variables"""

    def test_enable_code_execution_from_env(self, monkeypatch):
        """Test enabling code execution via environment"""
        monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")
        settings = Settings()
        assert settings.enable_code_execution is True

    def test_code_execution_backend_from_env(self, monkeypatch):
        """Test setting backend via environment"""
        monkeypatch.setenv("CODE_EXECUTION_BACKEND", "kubernetes")
        settings = Settings()
        assert settings.code_execution_backend == "kubernetes"

    def test_code_execution_timeout_from_env(self, monkeypatch):
        """Test setting timeout via environment"""
        monkeypatch.setenv("CODE_EXECUTION_TIMEOUT", "60")
        settings = Settings()
        assert settings.code_execution_timeout == 60

    def test_code_execution_memory_limit_from_env(self, monkeypatch):
        """Test setting memory limit via environment"""
        monkeypatch.setenv("CODE_EXECUTION_MEMORY_LIMIT_MB", "1024")
        settings = Settings()
        assert settings.code_execution_memory_limit_mb == 1024

    def test_code_execution_allowed_domains_from_env(self, monkeypatch):
        """Test setting allowed domains via environment (JSON format)"""
        # Pydantic Settings v2 expects JSON format for list environment variables
        monkeypatch.setenv("CODE_EXECUTION_ALLOWED_DOMAINS", '["api.example.com", "data.example.com"]')
        settings = Settings()
        assert "api.example.com" in settings.code_execution_allowed_domains
        assert "data.example.com" in settings.code_execution_allowed_domains

    def test_code_execution_allowed_imports_from_env(self, monkeypatch):
        """Test setting allowed imports via environment (JSON format)"""
        # Pydantic Settings v2 expects JSON format for list environment variables
        monkeypatch.setenv("CODE_EXECUTION_ALLOWED_IMPORTS", '["pandas", "numpy", "json", "datetime"]')
        settings = Settings()
        assert "pandas" in settings.code_execution_allowed_imports
        assert "numpy" in settings.code_execution_allowed_imports


@pytest.mark.unit
class TestCodeExecutionSettingsValidation:
    """Test code execution settings validation"""

    def test_network_mode_validation(self):
        """Test network mode must be valid value"""
        # Valid modes should work
        for mode in ["none", "allowlist", "unrestricted"]:
            settings = Settings(code_execution_network_mode=mode)
            assert settings.code_execution_network_mode == mode

    def test_backend_validation(self):
        """Test backend must be valid value"""
        # Valid backends should work
        for backend in ["docker-engine", "kubernetes", "process"]:
            settings = Settings(code_execution_backend=backend)
            assert settings.code_execution_backend == backend

    def test_timeout_must_be_positive(self):
        """Test timeout validation"""
        # Positive timeouts should work
        settings = Settings(code_execution_timeout=30)
        assert settings.code_execution_timeout == 30

    def test_memory_limit_must_be_positive(self):
        """Test memory limit validation"""
        # Positive memory limits should work
        settings = Settings(code_execution_memory_limit_mb=512)
        assert settings.code_execution_memory_limit_mb == 512


@pytest.mark.unit
class TestCodeExecutionSettingsIntegration:
    """Test code execution settings integration with ResourceLimits"""

    def test_settings_compatible_with_resource_limits(self):
        """Test that settings can be used to create ResourceLimits"""
        from mcp_server_langgraph.execution.resource_limits import ResourceLimits

        settings = Settings(
            code_execution_timeout=45,
            code_execution_memory_limit_mb=768,
            code_execution_cpu_quota=1.5,
            code_execution_network_mode="allowlist",
            code_execution_allowed_domains=["api.example.com"],
        )

        # Should be able to create ResourceLimits from settings
        limits = ResourceLimits(
            timeout_seconds=settings.code_execution_timeout,
            memory_limit_mb=settings.code_execution_memory_limit_mb,
            cpu_quota=settings.code_execution_cpu_quota,
            network_mode=settings.code_execution_network_mode,
            allowed_domains=tuple(settings.code_execution_allowed_domains),
        )

        assert limits.timeout_seconds == 45
        assert limits.memory_limit_mb == 768
        assert limits.cpu_quota == 1.5

    def test_settings_compatible_with_code_validator(self):
        """Test that settings can be used to create CodeValidator"""
        from mcp_server_langgraph.execution.code_validator import CodeValidator

        settings = Settings(code_execution_allowed_imports=["json", "math", "pandas", "numpy"])

        # Should be able to create CodeValidator from settings
        validator = CodeValidator(allowed_imports=settings.code_execution_allowed_imports)

        assert "json" in validator.allowed_imports
        assert "math" in validator.allowed_imports
        assert "pandas" in validator.allowed_imports


@pytest.mark.unit
class TestCodeExecutionSettingsDefaults:
    """Test code execution default settings for different environments"""

    def test_development_defaults(self, monkeypatch):
        """Test development environment defaults"""
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()

        # Development might have more relaxed defaults
        # But code execution should still be disabled by default
        assert settings.enable_code_execution is False

    def test_production_defaults(self, monkeypatch):
        """Test production environment defaults"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("AUTH_PROVIDER", "keycloak")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")
        settings = Settings()

        # Production must have code execution disabled by default
        assert settings.enable_code_execution is False
        # Network should be restrictive
        assert settings.code_execution_network_mode in ["none", "allowlist"]

    def test_test_defaults(self, monkeypatch):
        """Test testing environment defaults"""
        monkeypatch.setenv("ENVIRONMENT", "test")
        settings = Settings()

        # Test environment defaults
        assert settings.enable_code_execution is False
