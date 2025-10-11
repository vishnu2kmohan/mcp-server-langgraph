"""
MCP Streaming with Pydantic AI Validation

Provides type-safe streaming responses for MCP server with validation.
"""

import asyncio
import json
from typing import AsyncIterator, Optional

from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class StreamChunk(BaseModel):
    """Single chunk of streaming response."""

    content: str = Field(description="Content chunk")
    chunk_index: int = Field(description="Index in the stream sequence")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    metadata: dict[str, str] = Field(default_factory=dict, description="Chunk metadata")


class StreamedResponse(BaseModel):
    """Complete streaming response with validation."""

    chunks: list[StreamChunk] = Field(description="All received chunks")
    total_length: int = Field(description="Total content length")
    chunk_count: int = Field(description="Number of chunks received")
    is_complete: bool = Field(description="Whether stream completed successfully")
    error_message: Optional[str] = Field(default=None, description="Error message if stream failed")

    def get_full_content(self) -> str:
        """
        Reconstruct full content from chunks.

        Returns:
            Complete concatenated content
        """
        return "".join(chunk.content for chunk in self.chunks)


class MCPStreamingValidator:
    """
    Validator for MCP streaming responses.

    Ensures streaming chunks are properly formatted and validates
    the complete response once streaming is finished.
    """

    def __init__(self):
        """Initialize streaming validator."""
        self.active_streams: dict[str, list[StreamChunk]] = {}

    async def validate_chunk(self, chunk_data: dict, stream_id: str) -> Optional[StreamChunk]:
        """
        Validate a single stream chunk.

        Args:
            chunk_data: Raw chunk data
            stream_id: Unique stream identifier

        Returns:
            Validated StreamChunk or None if invalid
        """
        with tracer.start_as_current_span("mcp.validate_chunk") as span:
            span.set_attribute("stream.id", stream_id)

            try:
                chunk = StreamChunk(**chunk_data)

                # Track chunk in active stream
                if stream_id not in self.active_streams:
                    self.active_streams[stream_id] = []

                self.active_streams[stream_id].append(chunk)

                span.set_attribute("chunk.index", chunk.chunk_index)
                span.set_attribute("chunk.is_final", chunk.is_final)

                logger.debug(
                    "Chunk validated",
                    extra={"stream_id": stream_id, "chunk_index": chunk.chunk_index, "content_length": len(chunk.content)},
                )

                metrics.successful_calls.add(1, {"operation": "validate_chunk"})

                return chunk

            except Exception as e:
                logger.error(f"Chunk validation failed: {e}", extra={"stream_id": stream_id}, exc_info=True)

                metrics.failed_calls.add(1, {"operation": "validate_chunk"})
                span.record_exception(e)

                return None

    async def finalize_stream(self, stream_id: str) -> StreamedResponse:
        """
        Finalize and validate complete stream.

        Args:
            stream_id: Stream to finalize

        Returns:
            Complete StreamedResponse with all chunks
        """
        with tracer.start_as_current_span("mcp.finalize_stream") as span:
            span.set_attribute("stream.id", stream_id)

            if stream_id not in self.active_streams:
                logger.warning(f"Attempted to finalize unknown stream: {stream_id}")

                return StreamedResponse(
                    chunks=[], total_length=0, chunk_count=0, is_complete=False, error_message="Stream not found"
                )

            chunks = self.active_streams[stream_id]

            # Calculate totals
            total_length = sum(len(chunk.content) for chunk in chunks)
            chunk_count = len(chunks)

            # Check if stream completed properly
            is_complete = any(chunk.is_final for chunk in chunks)

            response = StreamedResponse(
                chunks=chunks,
                total_length=total_length,
                chunk_count=chunk_count,
                is_complete=is_complete,
                error_message=None if is_complete else "Stream incomplete",
            )

            span.set_attribute("stream.total_length", total_length)
            span.set_attribute("stream.chunk_count", chunk_count)
            span.set_attribute("stream.is_complete", is_complete)

            logger.info(
                "Stream finalized",
                extra={
                    "stream_id": stream_id,
                    "total_length": total_length,
                    "chunk_count": chunk_count,
                    "is_complete": is_complete,
                },
            )

            # Clean up
            del self.active_streams[stream_id]

            metrics.successful_calls.add(1, {"operation": "finalize_stream"})

            return response


async def stream_validated_response(
    content: str, chunk_size: int = 100, stream_id: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Stream response with validation as newline-delimited JSON.

    Args:
        content: Content to stream
        chunk_size: Size of each chunk in characters
        stream_id: Optional stream identifier

    Yields:
        JSON-serialized StreamChunk objects
    """
    stream_id = stream_id or "default"

    with tracer.start_as_current_span("mcp.stream_validated") as span:
        span.set_attribute("stream.id", stream_id)
        span.set_attribute("content.length", len(content))
        span.set_attribute("chunk.size", chunk_size)

        try:
            # Split content into chunks
            chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

            total_chunks = len(chunks)
            span.set_attribute("stream.total_chunks", total_chunks)

            logger.info(
                "Starting validated stream",
                extra={"stream_id": stream_id, "total_chunks": total_chunks, "content_length": len(content)},
            )

            # Stream each chunk
            for idx, chunk_content in enumerate(chunks):
                is_final = idx == total_chunks - 1

                chunk = StreamChunk(
                    content=chunk_content,
                    chunk_index=idx,
                    is_final=is_final,
                    metadata={"stream_id": stream_id, "total_chunks": str(total_chunks)},
                )

                # Yield as newline-delimited JSON
                yield json.dumps(chunk.model_dump()) + "\n"

                # Small delay to simulate realistic streaming
                await asyncio.sleep(0.01)

            metrics.successful_calls.add(1, {"operation": "stream_validated"})

        except Exception as e:
            logger.error(f"Streaming failed: {e}", extra={"stream_id": stream_id}, exc_info=True)

            metrics.failed_calls.add(1, {"operation": "stream_validated"})
            span.record_exception(e)

            # Yield error chunk
            error_chunk = StreamChunk(content="", chunk_index=-1, is_final=True, metadata={"error": str(e)})

            yield json.dumps(error_chunk.model_dump()) + "\n"


async def stream_agent_response(response_content: str, include_metadata: bool = True) -> AsyncIterator[str]:
    """
    Stream agent response with optional metadata.

    Args:
        response_content: Agent response to stream
        include_metadata: Whether to include metadata in chunks

    Yields:
        JSON chunks with validated structure
    """
    with tracer.start_as_current_span("mcp.stream_agent_response"):
        # Stream with validation
        async for chunk in stream_validated_response(response_content):
            yield chunk

        # Optionally yield final metadata chunk
        if include_metadata:
            metadata_chunk = StreamChunk(
                content="",
                chunk_index=-1,
                is_final=True,
                metadata={"type": "completion", "total_length": str(len(response_content))},
            )

            yield json.dumps(metadata_chunk.model_dump()) + "\n"


# Global validator instance
_streaming_validator = MCPStreamingValidator()


def get_streaming_validator() -> MCPStreamingValidator:
    """
    Get global streaming validator instance.

    Returns:
        MCPStreamingValidator singleton
    """
    return _streaming_validator
