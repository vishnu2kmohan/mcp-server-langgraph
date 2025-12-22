"""
Agentic Memory

Structured note-taking and checkpoints for persistent agent memory.

Implements:
- NOTES.md management for persistent notes
- Phase checkpoints for context recovery
- Session summarization

Usage:
    from mcp_server_langgraph.memory import NotesManager, CheckpointManager

    notes = NotesManager(notes_path=Path("./NOTES.md"))
    checkpoints = CheckpointManager(storage_dir=Path("./checkpoints"))
"""

from mcp_server_langgraph.memory.checkpoints import Checkpoint, CheckpointManager
from mcp_server_langgraph.memory.notes import Note, NotesManager

__all__ = [
    # Notes
    "Note",
    "NotesManager",
    # Checkpoints
    "Checkpoint",
    "CheckpointManager",
]
