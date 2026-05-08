"""Utilities for loading reusable markdown prompts."""

from pathlib import Path


def load_prompt_file(path: Path) -> str:
    """Load and normalize a markdown prompt file."""
    return path.read_text(encoding="utf-8").strip()
