"""
LiteLLM Factory for Multi-Provider LLM Support

Supports: Anthropic, OpenAI, Google (Gemini), Azure OpenAI, AWS Bedrock,
Ollama (Llama, Qwen, Mistral, etc.)
"""

import os
from typing import Dict, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from litellm import acompletion, completion
from litellm.utils import ModelResponse

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class LLMFactory:
    """
    Factory for creating and managing LLM connections via LiteLLM

    Supports multiple providers with automatic fallback and retry logic.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        enable_fallback: bool = True,
        fallback_models: Optional[list[str]] = None,
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

        # Set up environment variables for LiteLLM
        self._setup_environment()

        logger.info(
            "LLM Factory initialized", extra={"provider": provider, "model": model_name, "fallback_enabled": enable_fallback}
        )

    def _setup_environment(self):
        """Set up environment variables for LiteLLM"""
        if self.api_key:
            # Map provider to environment variable
            env_var_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "google": "GOOGLE_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "azure": "AZURE_API_KEY",
                "bedrock": "AWS_ACCESS_KEY_ID",
            }

            env_var = env_var_map.get(self.provider)
            if env_var:
                os.environ[env_var] = self.api_key

    def _format_messages(self, messages: list[BaseMessage]) -> list[Dict[str, str]]:
        """
        Convert LangChain messages to LiteLLM format

        Args:
            messages: List of LangChain BaseMessage objects

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
            else:
                # Default to user message
                formatted.append({"role": "user", "content": str(msg.content)})

        return formatted

    def invoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
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
                    extra={"model": self.model_name, "tokens": response.usage.total_tokens if response.usage else 0},
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

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        """
        Asynchronous LLM invocation

        Args:
            messages: List of messages
            **kwargs: Additional parameters for the model

        Returns:
            AIMessage with the response
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
                    extra={"model": self.model_name, "tokens": response.usage.total_tokens if response.usage else 0},
                )

                return AIMessage(content=content)

            except Exception as e:
                logger.error(
                    f"Async LLM invocation failed: {e}",
                    extra={"model": self.model_name, "provider": self.provider},
                    exc_info=True,
                )

                metrics.failed_calls.add(1, {"operation": "llm.ainvoke", "model": self.model_name})
                span.record_exception(e)

                if self.enable_fallback and self.fallback_models:
                    return await self._try_fallback_async(messages, **kwargs)

                raise

    def _try_fallback(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        """Try fallback models if primary fails"""
        for fallback_model in self.fallback_models:
            if fallback_model == self.model_name:
                continue  # Skip if it's the same model

            logger.warning(f"Trying fallback model: {fallback_model}", extra={"primary_model": self.model_name})

            try:
                formatted_messages = self._format_messages(messages)
                response = completion(
                    model=fallback_model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )

                content = response.choices[0].message.content

                logger.info("Fallback successful", extra={"fallback_model": fallback_model})

                metrics.successful_calls.add(1, {"operation": "llm.fallback", "model": fallback_model})

                return AIMessage(content=content)

            except Exception as e:
                logger.error(f"Fallback model {fallback_model} failed: {e}", exc_info=True)
                continue

        raise RuntimeError("All models failed including fallbacks")

    async def _try_fallback_async(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        """Try fallback models asynchronously"""
        for fallback_model in self.fallback_models:
            if fallback_model == self.model_name:
                continue

            logger.warning(f"Trying fallback model: {fallback_model}", extra={"primary_model": self.model_name})

            try:
                formatted_messages = self._format_messages(messages)
                response = await acompletion(
                    model=fallback_model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )

                content = response.choices[0].message.content

                logger.info("Async fallback successful", extra={"fallback_model": fallback_model})

                metrics.successful_calls.add(1, {"operation": "llm.fallback_async", "model": fallback_model})

                return AIMessage(content=content)

            except Exception as e:
                logger.error(f"Async fallback model {fallback_model} failed: {e}", exc_info=True)
                continue

        raise RuntimeError("All async models failed including fallbacks")


def create_llm_from_config(config) -> LLMFactory:
    """
    Create LLM instance from configuration

    Args:
        config: Settings object with LLM configuration

    Returns:
        Configured LLMFactory instance
    """
    # Determine API key based on provider
    api_key_map = {
        "anthropic": config.anthropic_api_key,
        "openai": config.openai_api_key,
        "google": config.google_api_key,
        "gemini": config.google_api_key,
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

    return LLMFactory(
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
