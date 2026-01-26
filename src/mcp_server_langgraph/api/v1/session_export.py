"""
Session Export API Endpoint.

REST API for exporting chat sessions in various formats.

Endpoints:
- POST /sessions/{session_id}/export - Export session

Supported formats:
- markdown: Markdown document with messages
- json: Raw JSON export
- html: HTML document with styling

Authentication:
- Uses Keycloak JWT authentication via get_current_user dependency
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user

logger = logging.getLogger(__name__)

# ==============================================================================
# Router
# ==============================================================================

session_export_router = APIRouter(
    prefix="/sessions",
    tags=["sessions", "export"],
)

# ==============================================================================
# Models
# ==============================================================================


class ExportRequest(BaseModel):
    """Export request parameters."""

    format: Literal["markdown", "json", "html"] = Field(default="markdown", description="Export format")
    include_metadata: bool = Field(default=False, description="Include session metadata")


# ==============================================================================
# Session Service
# ==============================================================================

# v8 FIX: Import real service instead of using local stub (Finding 52)
# This enables user-scoped access and ownership enforcement
from mcp_server_langgraph.api.v1.sessions import get_session_service


def _get_user_id(current_user: dict[str, Any]) -> str:
    """Extract user_id from current_user dict.

    v8: Required for ownership enforcement in session_export.
    """
    user_id = current_user.get("sub") or current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user credentials",
        )
    return str(user_id)


# ==============================================================================
# Type Aliases
# ==============================================================================

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# ==============================================================================
# Export Formatters
# ==============================================================================


def format_markdown(session: dict[str, Any], include_metadata: bool = False) -> str:
    """Format session as Markdown."""
    lines: list[str] = []

    # Title
    title = session.get("title", "Untitled Session")
    lines.append(f"# {title}")
    lines.append("")

    # Metadata
    if include_metadata:
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Session ID**: {session.get('id', 'N/A')}")
        lines.append(f"- **Created**: {session.get('created_at', 'N/A')}")
        lines.append(f"- **Updated**: {session.get('updated_at', 'N/A')}")
        lines.append("")

    # Messages
    lines.append("## Conversation")
    lines.append("")

    messages = session.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            lines.append("### User")
        elif role == "assistant":
            lines.append("### Assistant")
        else:
            lines.append(f"### {role.title()}")

        lines.append("")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def format_html(session: dict[str, Any], include_metadata: bool = False) -> str:
    """Format session as HTML."""
    title = session.get("title", "Untitled Session")
    messages = session.get("messages", [])

    # Build HTML
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{_escape_html(title)}</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
        "h1 { color: #333; }",
        ".message { margin: 20px 0; padding: 15px; border-radius: 8px; }",
        ".user { background: #e3f2fd; }",
        ".assistant { background: #f5f5f5; }",
        ".role { font-weight: bold; margin-bottom: 10px; }",
        "pre { background: #263238; color: #aed581; padding: 15px; border-radius: 4px; overflow-x: auto; }",
        "code { font-family: monospace; }",
        ".metadata { color: #666; font-size: 0.9em; margin-bottom: 20px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{_escape_html(title)}</h1>",
    ]

    # Metadata
    if include_metadata:
        html_parts.append('<div class="metadata">')
        html_parts.append(f"<p>Session ID: {_escape_html(session.get('id', 'N/A'))}</p>")
        html_parts.append(f"<p>Created: {_escape_html(session.get('created_at', 'N/A'))}</p>")
        html_parts.append("</div>")

    # Messages
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        role_class = "user" if role == "user" else "assistant"
        html_parts.append(f'<div class="message {role_class}">')
        html_parts.append(f'<div class="role">{_escape_html(role.title())}</div>')
        html_parts.append(f"<div>{_format_content_html(content)}</div>")
        html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])

    return "\n".join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _format_content_html(content: str) -> str:
    """Format message content for HTML with code block handling."""
    # Simple code block handling
    result = _escape_html(content)

    # Replace ```language\ncode\n``` with <pre><code>
    import re

    def replace_code_block(match: re.Match[str]) -> str:
        code = match.group(2)
        return f"<pre><code>{code}</code></pre>"

    result = re.sub(r"```(\w*)\n(.*?)```", replace_code_block, result, flags=re.DOTALL)

    # Replace newlines with <br>
    result = result.replace("\n", "<br>")

    return result


# ==============================================================================
# Endpoints
# ==============================================================================


@session_export_router.post(
    "/{session_id}/export",
    summary="Export session",
    description="Export a chat session in the specified format.",
)
async def export_session(
    session_id: str,
    request: ExportRequest,
    current_user: CurrentUser,
) -> Response:
    """Export a session in the specified format.

    v8: Ownership enforcement - only owner can export session (Finding 45, Q17).
    """
    service = get_session_service()
    user_id = _get_user_id(current_user)

    # v8 FIX: Pass user_id for ownership check (Finding 45)
    # Returns None if session not found OR not owned by user
    if service:
        session = await service.get_session(session_id, user_id)
    else:
        session = None

    if not session:
        # v8 Q17: Same 404 rule as other endpoints (don't reveal existence)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Generate safe filename
    title = session.get("title", "session")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    if not safe_title:
        safe_title = "session"

    timestamp = datetime.now().strftime("%Y%m%d")

    # Format based on requested format
    if request.format == "markdown":
        content = format_markdown(session, request.include_metadata)
        media_type = "text/markdown; charset=utf-8"
        extension = "md"
    elif request.format == "json":
        import json

        content = json.dumps(session, indent=2, default=str)
        media_type = "application/json"
        extension = "json"
    elif request.format == "html":
        content = format_html(session, request.include_metadata)
        media_type = "text/html; charset=utf-8"
        extension = "html"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format: {request.format}",
        )

    filename = f"{safe_title}_{timestamp}.{extension}"

    logger.info(
        "Exported session",
        extra={
            "session_id": session_id,
            "format": request.format,
            "user_id": current_user.get("user_id"),
        },
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
