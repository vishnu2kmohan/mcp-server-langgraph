"""
Meta-test for WebSocket Handler Signature Validation.

Validates that all WebSocket handlers in websocket/handlers/ implement
the correct method signatures as defined by WebSocketBase.

This test catches signature mismatches like:
- on_connect(user: AuthUser | None) instead of on_connect(user: AuthUser)
- on_disconnect(user) instead of on_disconnect()
- on_message(...) instead of handle_message(...)

Why this matters:
- Handlers with wrong signatures won't work correctly at runtime
- Python's duck typing won't catch these errors until the method is called
- This test provides compile-time-like validation for handler contracts
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = [pytest.mark.meta, pytest.mark.unit]


class MethodSignature(NamedTuple):
    """A method signature found in a handler class."""

    class_name: str
    method_name: str
    file_path: Path
    line_number: int
    parameters: list[str]
    return_annotation: str | None


def get_handlers_path() -> Path:
    """Get the path to the websocket/handlers directory."""
    current = Path(__file__).parent
    src_root = current.parent.parent / "src" / "mcp_server_langgraph" / "websocket" / "handlers"
    if not src_root.exists():
        pytest.skip(f"Handlers directory not found at {src_root}")
    return src_root


def find_handler_classes(handlers_path: Path) -> list[tuple[Path, str, ast.ClassDef]]:
    """Find all classes that extend WebSocketBase in handler files."""
    handlers: list[tuple[Path, str, ast.ClassDef]] = []

    # Files to exclude (not handlers, just utilities)
    excluded_files = {
        "__init__.py",
        "llm_streaming_broadcaster.py",
        "metrics_broadcaster.py",
    }

    for py_file in handlers_path.glob("*.py"):
        if py_file.name in excluded_files:
            continue

        content = py_file.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class extends WebSocketBase
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr

                    if base_name == "WebSocketBase":
                        handlers.append((py_file, node.name, node))

    return handlers


def extract_method_signature(
    file_path: Path,
    class_name: str,
    class_node: ast.ClassDef,
    method_name: str,
) -> MethodSignature | None:
    """Extract the signature of a specific method from a class."""
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                # Extract parameter names (skip 'self')
                params = []
                for arg in node.args.args[1:]:  # Skip self
                    param_name = arg.arg
                    # Include type annotation if present
                    if arg.annotation:
                        param_name += f": {ast.unparse(arg.annotation)}"
                    params.append(param_name)

                # Extract return annotation
                return_ann = None
                if node.returns:
                    return_ann = ast.unparse(node.returns)

                return MethodSignature(
                    class_name=class_name,
                    method_name=method_name,
                    file_path=file_path,
                    line_number=node.lineno,
                    parameters=params,
                    return_annotation=return_ann,
                )

    return None


@pytest.mark.meta
class TestWebSocketHandlerSignatures:
    """Validate that all WebSocket handlers implement correct method signatures."""

    def test_all_handlers_extend_websocket_base(self) -> None:
        """All handler classes should extend WebSocketBase."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        # We should find at least 15 handlers
        assert len(handlers) >= 15, (
            f"Expected at least 15 WebSocketBase handlers, found {len(handlers)}. "
            f"Did some handlers get removed or renamed?"
        )

    def test_all_handlers_implement_handle_message(self) -> None:
        """All handlers must implement handle_message (abstract method)."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        missing = []
        for file_path, class_name, class_node in handlers:
            sig = extract_method_signature(file_path, class_name, class_node, "handle_message")
            if sig is None:
                missing.append(f"{class_name} in {file_path.name}")

        assert not missing, (
            f"The following handlers are missing handle_message implementation:\n"
            f"  - {chr(10).join(missing)}\n\n"
            f"handle_message is an abstract method and must be implemented."
        )

    def test_handle_message_has_correct_signature(self) -> None:
        """handle_message should have signature: (message: MessageEnvelope) -> MessageEnvelope | None."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        wrong_signatures = []
        for file_path, class_name, class_node in handlers:
            sig = extract_method_signature(file_path, class_name, class_node, "handle_message")
            if sig is None:
                continue

            # Check parameters - should be exactly one: message: MessageEnvelope
            if len(sig.parameters) != 1:
                wrong_signatures.append(
                    f"{class_name}.handle_message has {len(sig.parameters)} params "
                    f"(expected 1): {sig.parameters} at {file_path.name}:{sig.line_number}"
                )
            elif not sig.parameters[0].startswith("message"):
                wrong_signatures.append(
                    f"{class_name}.handle_message first param should be 'message', "
                    f"got '{sig.parameters[0]}' at {file_path.name}:{sig.line_number}"
                )

        assert not wrong_signatures, (
            f"The following handlers have incorrect handle_message signatures:\n"
            f"  - {chr(10).join(wrong_signatures)}\n\n"
            f"Expected: handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None"
        )

    def test_on_connect_has_correct_signature_if_overridden(self) -> None:
        """on_connect should have signature: (user: AuthUser) -> None (non-optional user)."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        wrong_signatures = []
        for file_path, class_name, class_node in handlers:
            sig = extract_method_signature(file_path, class_name, class_node, "on_connect")
            if sig is None:
                continue  # Not overridden, that's fine

            # Check parameters - should be exactly one: user: AuthUser (non-optional)
            if len(sig.parameters) != 1:
                wrong_signatures.append(
                    f"{class_name}.on_connect has {len(sig.parameters)} params "
                    f"(expected 1): {sig.parameters} at {file_path.name}:{sig.line_number}"
                )
            elif "| None" in sig.parameters[0] or "Optional" in sig.parameters[0]:
                wrong_signatures.append(
                    f"{class_name}.on_connect has optional user param: '{sig.parameters[0]}' "
                    f"at {file_path.name}:{sig.line_number}. "
                    f"Should be 'user: AuthUser' (non-optional)"
                )

        assert not wrong_signatures, (
            f"The following handlers have incorrect on_connect signatures:\n"
            f"  - {chr(10).join(wrong_signatures)}\n\n"
            f"Expected: on_connect(self, user: AuthUser) -> None"
        )

    def test_on_disconnect_has_correct_signature_if_overridden(self) -> None:
        """on_disconnect should have signature: () -> None (no parameters besides self)."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        wrong_signatures = []
        for file_path, class_name, class_node in handlers:
            sig = extract_method_signature(file_path, class_name, class_node, "on_disconnect")
            if sig is None:
                continue  # Not overridden, that's fine

            # Check parameters - should be zero (only self)
            if len(sig.parameters) != 0:
                wrong_signatures.append(
                    f"{class_name}.on_disconnect has {len(sig.parameters)} params "
                    f"(expected 0): {sig.parameters} at {file_path.name}:{sig.line_number}"
                )

        assert not wrong_signatures, (
            f"The following handlers have incorrect on_disconnect signatures:\n"
            f"  - {chr(10).join(wrong_signatures)}\n\n"
            f"Expected: on_disconnect(self) -> None"
        )

    def test_no_legacy_on_message_method(self) -> None:
        """Handlers should not have on_message (legacy name for handle_message)."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        legacy_methods = []
        for file_path, class_name, class_node in handlers:
            sig = extract_method_signature(file_path, class_name, class_node, "on_message")
            if sig is not None:
                legacy_methods.append(
                    f"{class_name}.on_message at {file_path.name}:{sig.line_number}"
                )

        assert not legacy_methods, (
            f"The following handlers use legacy 'on_message' instead of 'handle_message':\n"
            f"  - {chr(10).join(legacy_methods)}\n\n"
            f"Rename on_message to handle_message and update signature to match WebSocketBase"
        )

    def test_handler_count_sanity_check(self) -> None:
        """Sanity check that we have expected number of handlers."""
        handlers_path = get_handlers_path()
        handlers = find_handler_classes(handlers_path)

        # We expect at least 15 handlers based on current codebase
        assert len(handlers) >= 15, (
            f"Only {len(handlers)} handlers found. Expected at least 15. "
            f"Did some handlers get accidentally removed?"
        )

        # Upper bound sanity check
        assert len(handlers) <= 50, (
            f"{len(handlers)} handlers found. This seems excessive - "
            f"consider consolidating if growing beyond 50."
        )
