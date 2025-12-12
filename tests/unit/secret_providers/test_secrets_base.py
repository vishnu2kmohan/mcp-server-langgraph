"""
Base Secrets Provider Tests

Tests for the secrets provider abstraction layer.
"""

import gc

import pytest

from mcp_server_langgraph.secret_providers.base import (
    SecretNotFoundError,
    SecretsProvider,
    SecretsProviderError,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_secrets_base")
class TestSecretsProviderInterface:
    """Tests for the SecretsProvider abstract base class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cannot_instantiate_abstract_class(self) -> None:
        """GIVEN SecretsProvider abstract class
        WHEN attempting to instantiate directly
        THEN should raise TypeError
        """
        with pytest.raises(TypeError):
            SecretsProvider()  # type: ignore

    def test_has_get_secret_method(self) -> None:
        """GIVEN SecretsProvider interface
        WHEN inspecting abstract methods
        THEN should have get_secret method
        """
        assert hasattr(SecretsProvider, "get_secret")
        assert callable(getattr(SecretsProvider, "get_secret", None))

    def test_has_set_secret_method(self) -> None:
        """GIVEN SecretsProvider interface
        WHEN inspecting abstract methods
        THEN should have set_secret method
        """
        assert hasattr(SecretsProvider, "set_secret")
        assert callable(getattr(SecretsProvider, "set_secret", None))

    def test_has_delete_secret_method(self) -> None:
        """GIVEN SecretsProvider interface
        WHEN inspecting abstract methods
        THEN should have delete_secret method
        """
        assert hasattr(SecretsProvider, "delete_secret")
        assert callable(getattr(SecretsProvider, "delete_secret", None))

    def test_has_list_secrets_method(self) -> None:
        """GIVEN SecretsProvider interface
        WHEN inspecting abstract methods
        THEN should have list_secrets method
        """
        assert hasattr(SecretsProvider, "list_secrets")
        assert callable(getattr(SecretsProvider, "list_secrets", None))

    def test_has_is_available_method(self) -> None:
        """GIVEN SecretsProvider interface
        WHEN inspecting abstract methods
        THEN should have is_available method
        """
        assert hasattr(SecretsProvider, "is_available")
        assert callable(getattr(SecretsProvider, "is_available", None))


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_secrets_base")
class TestSecretNotFoundError:
    """Tests for SecretNotFoundError exception."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_has_secret_name_attribute(self) -> None:
        """GIVEN SecretNotFoundError
        WHEN created with secret name
        THEN should have secret_name attribute
        """
        error = SecretNotFoundError("my-secret")
        assert error.secret_name == "my-secret"

    def test_error_message_includes_secret_name(self) -> None:
        """GIVEN SecretNotFoundError
        WHEN created with secret name
        THEN message should include secret name
        """
        error = SecretNotFoundError("api-key")
        assert "api-key" in str(error)

    def test_inherits_from_secrets_provider_error(self) -> None:
        """GIVEN SecretNotFoundError
        WHEN checking inheritance
        THEN should be subclass of SecretsProviderError
        """
        assert issubclass(SecretNotFoundError, SecretsProviderError)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_secrets_base")
class TestSecretsProviderError:
    """Tests for SecretsProviderError base exception."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inherits_from_exception(self) -> None:
        """GIVEN SecretsProviderError
        WHEN checking inheritance
        THEN should be subclass of Exception
        """
        assert issubclass(SecretsProviderError, Exception)

    def test_can_be_raised_with_message(self) -> None:
        """GIVEN SecretsProviderError
        WHEN raised with message
        THEN should contain message
        """
        with pytest.raises(SecretsProviderError) as exc_info:
            raise SecretsProviderError("Connection failed")
        assert "Connection failed" in str(exc_info.value)
