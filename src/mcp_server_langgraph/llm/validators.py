"""
LLM Response Validators using Pydantic AI

Provides type-safe validation and structured extraction from LLM responses.
"""

from typing import Generic, Optional, TypeVar

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field, ValidationError

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer

T = TypeVar("T", bound=BaseModel)


class ValidatedResponse(Generic[T]):
    """
    Container for validated LLM response with metadata.

    Generic type parameter T should be a Pydantic model defining
    the expected structure of the response.
    """

    def __init__(
        self, data: T, raw_content: str, validation_success: bool = True, validation_errors: Optional[list[str]] = None
    ):
        """
        Initialize validated response.

        Args:
            data: Validated and parsed data
            raw_content: Original LLM response text
            validation_success: Whether validation passed
            validation_errors: List of validation error messages
        """
        self.data = data
        self.raw_content = raw_content
        self.validation_success = validation_success
        self.validation_errors = validation_errors or []

    def is_valid(self) -> bool:
        """Check if response passed validation."""
        return self.validation_success

    def get_errors(self) -> list[str]:
        """Get validation error messages."""
        return self.validation_errors


class EntityExtraction(BaseModel):
    """Extracted entities from text."""

    entities: list[dict[str, str]] = Field(description="List of extracted entities with type and value")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in extraction quality")


class IntentClassification(BaseModel):
    """User intent classification."""

    intent: str = Field(description="Primary intent category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    sub_intents: list[str] = Field(default_factory=list, description="Secondary or related intents")
    parameters: dict[str, str] = Field(default_factory=dict, description="Extracted parameters for the intent")


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result."""

    sentiment: str = Field(description="Overall sentiment (positive/negative/neutral)")
    score: float = Field(ge=-1.0, le=1.0, description="Sentiment score (-1 to 1)")
    emotions: list[str] = Field(default_factory=list, description="Detected emotions")


class SummaryExtraction(BaseModel):
    """Extracted summary with key points."""

    summary: str = Field(description="Concise summary of content")
    key_points: list[str] = Field(description="Key points from content")
    length: int = Field(description="Character count of summary")
    compression_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of summary to original length")


class LLMValidator:
    """
    Validator for LLM responses with Pydantic models.

    Provides structured validation and extraction from free-text LLM outputs.
    """

    @staticmethod
    def validate_response(response: AIMessage | str, model_class: type[T], strict: bool = False) -> ValidatedResponse[T]:
        """
        Validate LLM response against a Pydantic model.

        Args:
            response: LLM response (AIMessage or string)
            model_class: Pydantic model class for validation
            strict: Whether to raise exception on validation failure

        Returns:
            ValidatedResponse containing parsed data or errors

        Raises:
            ValidationError: If strict=True and validation fails
        """
        with tracer.start_as_current_span("llm.validate_response") as span:
            # Extract content
            if isinstance(response, AIMessage):
                content = response.content
            else:
                content = str(response)

            span.set_attribute("response.length", len(content))
            span.set_attribute("model.name", model_class.__name__)

            try:
                # Attempt to parse as JSON first (for structured outputs)
                import json

                try:
                    data_dict = json.loads(content)  # type: ignore[arg-type]
                    validated = model_class(**data_dict)
                except json.JSONDecodeError:
                    # Not JSON, try to parse as text
                    # This requires the model to handle string input
                    validated = model_class(content=content) if hasattr(model_class, "content") else None  # type: ignore[assignment]

                    if validated is None:
                        raise ValueError(
                            f"Cannot parse non-JSON content for {model_class.__name__}. "
                            "Model must accept 'content' field or response must be valid JSON."
                        )

                span.set_attribute("validation.success", True)

                logger.info(
                    "Response validated successfully", extra={"model": model_class.__name__, "content_length": len(content)}
                )

                metrics.successful_calls.add(1, {"operation": "validate_response"})

                return ValidatedResponse(data=validated, raw_content=content, validation_success=True)  # type: ignore[arg-type]

            except ValidationError as e:
                span.set_attribute("validation.success", False)
                span.record_exception(e)

                errors = [str(err) for err in e.errors()]

                logger.warning("Response validation failed", extra={"model": model_class.__name__, "errors": errors})

                metrics.failed_calls.add(1, {"operation": "validate_response"})

                if strict:
                    raise

                # Return invalid response with errors
                # Create empty instance for data
                try:
                    empty_data = model_class()
                except Exception:
                    empty_data = None

                return ValidatedResponse(
                    data=empty_data, raw_content=content, validation_success=False, validation_errors=errors  # type: ignore[arg-type]
                )

            except Exception as e:
                span.record_exception(e)

                logger.error(f"Unexpected validation error: {e}", exc_info=True)

                metrics.failed_calls.add(1, {"operation": "validate_response"})

                if strict:
                    raise

                return ValidatedResponse(data=None, raw_content=content, validation_success=False, validation_errors=[str(e)])  # type: ignore[arg-type]

    @staticmethod
    def extract_entities(response: AIMessage | str) -> ValidatedResponse[EntityExtraction]:
        """
        Extract named entities from LLM response.

        Args:
            response: LLM response to extract from

        Returns:
            ValidatedResponse with EntityExtraction data
        """
        return LLMValidator.validate_response(response, EntityExtraction, strict=False)

    @staticmethod
    def classify_intent(response: AIMessage | str) -> ValidatedResponse[IntentClassification]:
        """
        Classify user intent from LLM response.

        Args:
            response: LLM response with intent classification

        Returns:
            ValidatedResponse with IntentClassification data
        """
        return LLMValidator.validate_response(response, IntentClassification, strict=False)

    @staticmethod
    def analyze_sentiment(response: AIMessage | str) -> ValidatedResponse[SentimentAnalysis]:
        """
        Analyze sentiment from LLM response.

        Args:
            response: LLM response with sentiment analysis

        Returns:
            ValidatedResponse with SentimentAnalysis data
        """
        return LLMValidator.validate_response(response, SentimentAnalysis, strict=False)

    @staticmethod
    def extract_summary(response: AIMessage | str) -> ValidatedResponse[SummaryExtraction]:
        """
        Extract summary and key points from LLM response.

        Args:
            response: LLM response with summary

        Returns:
            ValidatedResponse with SummaryExtraction data
        """
        return LLMValidator.validate_response(response, SummaryExtraction, strict=False)


def validate_llm_response(response: AIMessage | str, expected_model: type[T]) -> ValidatedResponse[T]:
    """
    Convenience function to validate LLM response.

    Args:
        response: LLM response to validate
        expected_model: Pydantic model defining expected structure

    Returns:
        ValidatedResponse with parsed data
    """
    return LLMValidator.validate_response(response, expected_model, strict=False)
