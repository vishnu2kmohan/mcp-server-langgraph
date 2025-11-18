"""
LiteLLM Factory for Multi-Provider LLM Support

Supports: Anthropic, OpenAI, Google (Gemini), Azure OpenAI, AWS Bedrock,
Ollama (Llama, Qwen, Mistral, etc.)

Enhanced with resilience patterns (ADR-0026):
- Circuit breaker for provider failures
- Retry logic with exponential backoff
- Timeout enforcement
- Bulkhead isolation (10 concurrent LLM calls max)
"""

import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from litellm import acompletion, completion
from litellm.utils import ModelResponse

from mcp_server_langgraph.core.exceptions import LLMModelNotFoundError, LLMProviderError, LLMRateLimitError, LLMTimeoutError
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.resilience import circuit_breaker, retry_with_backoff, with_bulkhead, with_timeout


class LLMFactory:
    """
    Factory for creating and managing LLM connections via LiteLLM

    Supports multiple providers with automatic fallback and retry logic.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        provider: str = "anthropic",
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        enable_fallback: bool = True,
        fallback_models: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize LLM Factory

        Args:
            provider: LLM provider (anthropic, openai, google, azure, bedrock, ollama)
            model_name: Model identifier
            api_key: API key for the provider
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            enable_fallback: Enable fallback to alternative models
            fallback_models: List of fallback model names
            **kwargs: Additional provider-specific parameters
        """
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.enable_fallback = enable_fallback
        self.fallback_models = fallback_models or []
        self.kwargs = kwargs

        # Note: _setup_environment is now called by factory functions with config
        # This allows multi-provider credential setup for fallbacks

        logger.info(
            "LLM Factory initialized",
            extra={
                "provider": provider,
                "model": model_name,
                "fallback_enabled": enable_fallback,
                "fallback_count": len(fallback_models) if fallback_models else 0,
            },
        )

    def _get_provider_from_model(self, model_name: str) -> str:
        """
        Extract provider from model name.

        Args:
            model_name: Model identifier (e.g., "gpt-5", "claude-sonnet-4-5", "gemini-2.5-flash")

        Returns:
            Provider name (e.g., "openai", "anthropic", "google")
        """
        model_lower = model_name.lower()

        # Check provider prefixes FIRST (azure/gpt-4 should be azure, not openai)
        # Azure (prefixed models)
        if model_lower.startswith("azure/"):
            return "azure"

        # Bedrock (prefixed models)
        if model_lower.startswith("bedrock/"):
            return "bedrock"

        # Ollama (local models)
        if model_lower.startswith("ollama/"):
            return "ollama"

        # Then check model name patterns
        # Anthropic models
        if any(x in model_lower for x in ["claude", "anthropic"]):
            return "anthropic"

        # OpenAI models
        if any(x in model_lower for x in ["gpt-", "o1-", "davinci", "curie", "babbage"]):
            return "openai"

        # Google models
        if any(x in model_lower for x in ["gemini", "palm", "text-bison", "chat-bison"]):
            return "google"

        # Default to current provider
        return self.provider

    def _get_provider_kwargs(self, model_name: str) -> dict[str, Any]:
        """
        Get provider-specific kwargs for a given model.

        BUGFIX: Filters out provider-specific parameters that don't apply to the target provider.
        For example, Azure-specific params (azure_endpoint, azure_deployment) are removed
        when calling Anthropic or OpenAI fallback models.

        Args:
            model_name: Model identifier to get kwargs for

        Returns:
            dict: Filtered kwargs appropriate for the model's provider
        """
        provider = self._get_provider_from_model(model_name)

        # Define provider-specific parameter prefixes
        provider_specific_prefixes = {
            "azure": ["azure_", "api_version"],
            "bedrock": ["aws_", "bedrock_"],
            "vertex": ["vertex_", "gcp_"],
        }

        # If this is the same provider as the primary model, return all kwargs
        if provider == self.provider:
            return self.kwargs

        # Filter out parameters specific to other providers
        filtered_kwargs = {}
        for key, value in self.kwargs.items():
            # Check if this parameter belongs to a different provider
            is_provider_specific = False
            for other_provider, prefixes in provider_specific_prefixes.items():
                if other_provider != provider and any(key.startswith(prefix) for prefix in prefixes):
                    is_provider_specific = True
                    break

            # Include parameter if it's not specific to another provider
            if not is_provider_specific:
                filtered_kwargs[key] = value

        logger.debug(
            "Filtered kwargs for fallback model",
            extra={
                "model": model_name,
                "provider": provider,
                "original_kwargs": list(self.kwargs.keys()),
                "filtered_kwargs": list(filtered_kwargs.keys()),
            },
        )

        return filtered_kwargs

    def _setup_environment(self, config=None) -> None:  # type: ignore[no-untyped-def]
        """
        Set up environment variables for LiteLLM.

        Configures credentials for primary provider AND all fallback providers
        to enable seamless multi-provider fallback.

        Args:
            config: Settings object with API keys for all providers (optional)
        """
        # Collect all providers needed (primary + fallbacks)
        providers_needed = {self.provider}

        # Add providers for each fallback model
        for fallback_model in self.fallback_models:
            provider = self._get_provider_from_model(fallback_model)
            providers_needed.add(provider)

        # Map provider to environment variable and config attribute
        # Provider-specific credential mapping (some providers need multiple env vars)
        provider_config_map = {
            "anthropic": [("ANTHROPIC_API_KEY", "anthropic_api_key")],
            "openai": [("OPENAI_API_KEY", "openai_api_key")],
            "google": [("GOOGLE_API_KEY", "google_api_key")],
            "gemini": [("GOOGLE_API_KEY", "google_api_key")],
            "azure": [
                ("AZURE_API_KEY", "azure_api_key"),
                ("AZURE_API_BASE", "azure_api_base"),
                ("AZURE_API_VERSION", "azure_api_version"),
                ("AZURE_DEPLOYMENT_NAME", "azure_deployment_name"),
            ],
            "bedrock": [
                ("AWS_ACCESS_KEY_ID", "aws_access_key_id"),
                ("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key"),
                ("AWS_REGION", "aws_region"),
            ],
        }

        # Set up credentials for each needed provider
        for provider in providers_needed:
            if provider not in provider_config_map:
                continue  # Skip unknown providers (e.g., ollama doesn't need API key)

            credential_pairs = provider_config_map[provider]

            for env_var, config_attr in credential_pairs:
                # Get value from config
                if config and hasattr(config, config_attr):
                    value = getattr(config, config_attr)
                else:
                    value = None

                # For primary provider, use self.api_key as fallback for API key fields
                if value is None and provider == self.provider and "api_key" in config_attr.lower():
                    value = self.api_key

                # Set environment variable if we have a value
                if value and env_var:
                    os.environ[env_var] = str(value)
                    logger.debug(
                        f"Configured credential for provider: {provider}", extra={"provider": provider, "env_var": env_var}
                    )

    def _format_messages(self, messages: list[BaseMessage]) -> list[dict[str, str]]:
        """
        Convert LangChain messages to LiteLLM format

        Args:
            messages: List of LangChain BaseMessage objects or dicts

        Returns:
            List of dictionaries in LiteLLM format
        """
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                formatted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, dict):
                # Handle dict messages (already in correct format or need conversion)
                # Note: Technically unreachable since msg is BaseMessage, but kept for defensive programming
                if "role" in msg and "content" in msg:
                    # Already formatted dict
                    formatted.append(msg)
                elif "content" in msg:
                    # Dict with content but no role
                    formatted.append({"role": "user", "content": str(msg["content"])})
                else:
                    # Malformed dict, convert to string
                    formatted.append({"role": "user", "content": str(msg)})
            else:
                # Fallback for other types - check if it has content attribute
                if hasattr(msg, "content"):
                    formatted.append({"role": "user", "content": str(msg.content)})
                else:
                    # Last resort: convert entire object to string
                    formatted.append({"role": "user", "content": str(msg)})

        return formatted

    def invoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:  # type: ignore[no-untyped-def]
        """
        Synchronous LLM invocation

        Args:
            messages: List of messages
            **kwargs: Additional parameters for the model

        Returns:
            AIMessage with the response
        """
        with tracer.start_as_current_span("llm.invoke") as span:
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("llm.model", self.model_name)

            formatted_messages = self._format_messages(messages)

            # Merge kwargs with defaults
            params = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "timeout": kwargs.get("timeout", self.timeout),
                **self.kwargs,
            }

            try:
                response: ModelResponse = completion(**params)

                content = response.choices[0].message.content

                # Track metrics
                metrics.successful_calls.add(1, {"operation": "llm.invoke", "model": self.model_name})

                logger.info(
                    "LLM invocation successful",
                    extra={
                        "model": self.model_name,
                        "tokens": response.usage.total_tokens if response.usage else 0,
                    },
                )

                return AIMessage(content=content)

            except Exception as e:
                logger.error(
                    f"LLM invocation failed: {e}", extra={"model": self.model_name, "provider": self.provider}, exc_info=True
                )

                metrics.failed_calls.add(1, {"operation": "llm.invoke", "model": self.model_name})
                span.record_exception(e)

                # Try fallback if enabled
                if self.enable_fallback and self.fallback_models:
                    return self._try_fallback(messages, **kwargs)

                raise

    @circuit_breaker(name="llm", fail_max=5, timeout=60)
    @retry_with_backoff(max_attempts=3, exponential_base=2)
    @with_timeout(operation_type="llm")
    @with_bulkhead(resource_type="llm")
    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:  # type: ignore[no-untyped-def]
        """
        Asynchronous LLM invocation with full resilience protection.

        Protected by:
        - Circuit breaker: Fail fast if LLM provider is down (5 failures → open, 60s timeout)
        - Retry logic: Up to 3 attempts with exponential backoff (1s, 2s, 4s)
        - Timeout: 60s timeout for LLM operations
        - Bulkhead: Limit to 10 concurrent LLM calls

        Args:
            messages: List of messages
            **kwargs: Additional parameters for the model

        Returns:
            AIMessage with the response

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            RetryExhaustedError: If all retry attempts failed
            TimeoutError: If operation exceeds 60s timeout
            BulkheadRejectedError: If too many concurrent LLM calls
            LLMProviderError: For other LLM provider errors
        """
        with tracer.start_as_current_span("llm.ainvoke") as span:
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("llm.model", self.model_name)

            formatted_messages = self._format_messages(messages)

            params = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "timeout": kwargs.get("timeout", self.timeout),
                **self.kwargs,
            }

            try:
                response: ModelResponse = await acompletion(**params)

                content = response.choices[0].message.content

                metrics.successful_calls.add(1, {"operation": "llm.ainvoke", "model": self.model_name})

                logger.info(
                    "Async LLM invocation successful",
                    extra={
                        "model": self.model_name,
                        "tokens": response.usage.total_tokens if response.usage else 0,
                    },
                )

                return AIMessage(content=content)

            except Exception as e:
                # Convert to custom exceptions for better error handling
                error_msg = str(e).lower()

                if "rate limit" in error_msg or "429" in error_msg:
                    raise LLMRateLimitError(
                        message=f"LLM provider rate limit exceeded: {e}",
                        metadata={"model": self.model_name, "provider": self.provider},
                        cause=e,
                    ) from e
                if "timeout" in error_msg or "timed out" in error_msg:
                    raise LLMTimeoutError(
                        message=f"LLM request timed out: {e}",
                        metadata={"model": self.model_name, "provider": self.provider, "timeout": self.timeout},
                        cause=e,
                    ) from e
                if "model not found" in error_msg or "404" in error_msg:
                    raise LLMModelNotFoundError(
                        message=f"LLM model not found: {e}",
                        metadata={"model": self.model_name, "provider": self.provider},
                        cause=e,
                    ) from e
                logger.error(
                    f"Async LLM invocation failed: {e}",
                    extra={"model": self.model_name, "provider": self.provider},
                    exc_info=True,
                )

                metrics.failed_calls.add(1, {"operation": "llm.ainvoke", "model": self.model_name})
                span.record_exception(e)

                # Try fallback if enabled
                if self.enable_fallback and self.fallback_models:
                    return await self._try_fallback_async(messages, **kwargs)

                raise LLMProviderError(
                    message=f"LLM provider error: {e}",
                    metadata={"model": self.model_name, "provider": self.provider},
                    cause=e,
                ) from e

    def _try_fallback(self, messages: list[BaseMessage], **kwargs) -> AIMessage:  # type: ignore[no-untyped-def]
        """Try fallback models if primary fails"""
        for fallback_model in self.fallback_models:
            if fallback_model == self.model_name:
                continue  # Skip if it's the same model

            logger.warning(f"Trying fallback model: {fallback_model}", extra={"primary_model": self.model_name})

            try:
                formatted_messages = self._format_messages(messages)
                # BUGFIX: Use provider-specific kwargs to avoid cross-provider parameter errors
                provider_kwargs = self._get_provider_kwargs(fallback_model)
                response = completion(
                    model=fallback_model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                    **provider_kwargs,  # Forward provider-specific kwargs only
                )

                content = response.choices[0].message.content

                logger.info("Fallback successful", extra={"fallback_model": fallback_model})

                metrics.successful_calls.add(1, {"operation": "llm.fallback", "model": fallback_model})

                return AIMessage(content=content)

            except Exception as e:
                logger.error(f"Fallback model {fallback_model} failed: {e}", exc_info=True)
                continue

        raise RuntimeError("All models failed including fallbacks")

    async def _try_fallback_async(self, messages: list[BaseMessage], **kwargs) -> AIMessage:  # type: ignore[no-untyped-def]
        """Try fallback models asynchronously"""
        for fallback_model in self.fallback_models:
            if fallback_model == self.model_name:
                continue

            logger.warning(f"Trying fallback model: {fallback_model}", extra={"primary_model": self.model_name})

            try:
                formatted_messages = self._format_messages(messages)
                # BUGFIX: Use provider-specific kwargs to avoid cross-provider parameter errors
                provider_kwargs = self._get_provider_kwargs(fallback_model)
                response = await acompletion(
                    model=fallback_model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                    **provider_kwargs,  # Forward provider-specific kwargs only
                )

                content = response.choices[0].message.content

                logger.info("Async fallback successful", extra={"fallback_model": fallback_model})

                metrics.successful_calls.add(1, {"operation": "llm.fallback_async", "model": fallback_model})

                return AIMessage(content=content)

            except Exception as e:
                logger.error(f"Async fallback model {fallback_model} failed: {e}", exc_info=True)
                continue

        raise RuntimeError("All async models failed including fallbacks")


def create_llm_from_config(config) -> LLMFactory:  # type: ignore[no-untyped-def]
    """
    Create primary LLM instance from configuration

    Args:
        config: Settings object with LLM configuration

    Returns:
        Configured LLMFactory instance for primary chat operations
    """
    # Determine API key based on provider
    api_key_map = {
        "anthropic": config.anthropic_api_key,
        "openai": config.openai_api_key,
        "google": config.google_api_key,
        "gemini": config.google_api_key,
        "vertex_ai": None,  # Vertex AI uses Workload Identity or GOOGLE_APPLICATION_CREDENTIALS
        "azure": config.azure_api_key,
        "bedrock": config.aws_access_key_id,
    }

    api_key = api_key_map.get(config.llm_provider)

    # Provider-specific kwargs
    provider_kwargs = {}

    if config.llm_provider == "azure":
        provider_kwargs.update(
            {
                "api_base": config.azure_api_base,
                "api_version": config.azure_api_version,
            }
        )
    elif config.llm_provider == "bedrock":
        provider_kwargs.update(
            {
                "aws_secret_access_key": config.aws_secret_access_key,
                "aws_region_name": config.aws_region,
            }
        )
    elif config.llm_provider == "ollama":
        provider_kwargs.update(
            {
                "api_base": config.ollama_base_url,
            }
        )
    elif config.llm_provider in ["vertex_ai", "google"]:
        # Vertex AI configuration
        # LiteLLM requires vertex_project and vertex_location for Vertex AI models
        # If using Workload Identity on GKE, authentication is automatic
        vertex_project = config.vertex_project or config.google_project_id
        if vertex_project:
            provider_kwargs.update(
                {
                    "vertex_project": vertex_project,
                    "vertex_location": config.vertex_location,
                }
            )

    factory = LLMFactory(
        provider=config.llm_provider,
        model_name=config.model_name,
        api_key=api_key,
        temperature=config.model_temperature,
        max_tokens=config.model_max_tokens,
        timeout=config.model_timeout,
        enable_fallback=config.enable_fallback,
        fallback_models=config.fallback_models,
        **provider_kwargs,
    )

    # Set up credentials for primary + all fallback providers
    factory._setup_environment(config=config)

    return factory


def create_summarization_model(config) -> LLMFactory:  # type: ignore[no-untyped-def]
    """
    Create dedicated LLM instance for summarization (cost-optimized).

    Uses lighter/cheaper model for context compaction to reduce costs.
    Falls back to primary model if dedicated model not configured.

    Args:
        config: Settings object with LLM configuration

    Returns:
        Configured LLMFactory instance for summarization
    """
    # If dedicated summarization model not enabled, use primary model
    if not getattr(config, "use_dedicated_summarization_model", False):
        return create_llm_from_config(config)

    # Determine provider and API key
    provider = config.summarization_model_provider or config.llm_provider

    api_key_map = {
        "anthropic": config.anthropic_api_key,
        "openai": config.openai_api_key,
        "google": config.google_api_key,
        "gemini": config.google_api_key,
        "vertex_ai": None,  # Vertex AI uses Workload Identity or GOOGLE_APPLICATION_CREDENTIALS
        "azure": config.azure_api_key,
        "bedrock": config.aws_access_key_id,
    }

    api_key = api_key_map.get(provider)

    # Provider-specific kwargs
    provider_kwargs = {}
    if provider == "azure":
        provider_kwargs.update({"api_base": config.azure_api_base, "api_version": config.azure_api_version})
    elif provider == "bedrock":
        provider_kwargs.update({"aws_secret_access_key": config.aws_secret_access_key, "aws_region_name": config.aws_region})
    elif provider == "ollama":
        provider_kwargs.update({"api_base": config.ollama_base_url})
    elif provider in ["vertex_ai", "google"]:
        vertex_project = config.vertex_project or config.google_project_id
        if vertex_project:
            provider_kwargs.update({"vertex_project": vertex_project, "vertex_location": config.vertex_location})

    factory = LLMFactory(
        provider=provider,
        model_name=config.summarization_model_name or config.model_name,
        api_key=api_key,
        temperature=config.summarization_model_temperature,
        max_tokens=config.summarization_model_max_tokens,
        timeout=config.model_timeout,
        enable_fallback=config.enable_fallback,
        fallback_models=config.fallback_models,
        **provider_kwargs,
    )

    # Set up credentials for all providers
    factory._setup_environment(config=config)

    return factory


def create_verification_model(config) -> LLMFactory:  # type: ignore[no-untyped-def]
    """
    Create dedicated LLM instance for verification (LLM-as-judge).

    Uses potentially different model for output verification to balance
    cost and quality. Falls back to primary model if not configured.

    Args:
        config: Settings object with LLM configuration

    Returns:
        Configured LLMFactory instance for verification
    """
    # If dedicated verification model not enabled, use primary model
    if not getattr(config, "use_dedicated_verification_model", False):
        return create_llm_from_config(config)

    # Determine provider and API key
    provider = config.verification_model_provider or config.llm_provider

    api_key_map = {
        "anthropic": config.anthropic_api_key,
        "openai": config.openai_api_key,
        "google": config.google_api_key,
        "gemini": config.google_api_key,
        "vertex_ai": None,  # Vertex AI uses Workload Identity or GOOGLE_APPLICATION_CREDENTIALS
        "azure": config.azure_api_key,
        "bedrock": config.aws_access_key_id,
    }

    api_key = api_key_map.get(provider)

    # Provider-specific kwargs
    provider_kwargs = {}
    if provider == "azure":
        provider_kwargs.update({"api_base": config.azure_api_base, "api_version": config.azure_api_version})
    elif provider == "bedrock":
        provider_kwargs.update({"aws_secret_access_key": config.aws_secret_access_key, "aws_region_name": config.aws_region})
    elif provider == "ollama":
        provider_kwargs.update({"api_base": config.ollama_base_url})
    elif provider in ["vertex_ai", "google"]:
        vertex_project = config.vertex_project or config.google_project_id
        if vertex_project:
            provider_kwargs.update({"vertex_project": vertex_project, "vertex_location": config.vertex_location})

    factory = LLMFactory(
        provider=provider,
        model_name=config.verification_model_name or config.model_name,
        api_key=api_key,
        temperature=config.verification_model_temperature,
        max_tokens=config.verification_model_max_tokens,
        timeout=config.model_timeout,
        enable_fallback=config.enable_fallback,
        fallback_models=config.fallback_models,
        **provider_kwargs,
    )

    # Set up credentials for all providers
    factory._setup_environment(config=config)

    return factory
