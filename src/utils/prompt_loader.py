"""Utilities for loading reusable markdown prompts."""

from pathlib import Path


def load_prompt_file(path: Path) -> str:
    """Load and normalize a markdown prompt file."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    normalized = path.as_posix()
    legacy_prefix = ".ai/prompts/"
    if normalized.startswith(legacy_prefix):
        relative_prompt_path = Path(normalized[len(legacy_prefix) :])
        fallback_path = Path("src/prompts") / relative_prompt_path
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8").strip()

    raise FileNotFoundError(f"Prompt file not found: {path}")
