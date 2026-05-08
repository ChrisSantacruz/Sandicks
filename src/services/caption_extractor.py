"""Service to detect and extract optional caption text from meme prompts.

When the user includes phrases like `saying ...`, `that says ...`,
or `with text "..."`, the caption is separated from the prompt so the image
model does not try to render the text (which it does poorly), and so the
caption can be overlaid later with a proper font.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedCaption:
    """Result of separating an optional caption from the meme prompt."""

    cleaned_prompt: str
    caption: str | None


_CAPTION_KEYWORDS: tuple[str, ...] = (
    r"with\s+(?:the\s+)?text",
    r"that\s+says",
    r"saying",
    r"text",
)

_KEYWORDS_GROUP = "|".join(_CAPTION_KEYWORDS)
_QUOTE_CHARS = "\"'\u201c\u201d\u2018\u2019\u00ab\u00bb"

# Caption wrapped in quotes: keyword [optional :] "caption"
_QUOTED_PATTERN = re.compile(
    rf"\b(?P<keyword>{_KEYWORDS_GROUP})\s*:?\s*"
    rf"[{_QUOTE_CHARS}](?P<caption>[^{_QUOTE_CHARS}]+)[{_QUOTE_CHARS}]",
    re.IGNORECASE,
)

# Unquoted caption: keyword [optional :] caption-up-to-comma-or-end
_UNQUOTED_PATTERN = re.compile(
    rf"\b(?P<keyword>{_KEYWORDS_GROUP})\s*:?\s+(?P<caption>[^,;]+?)\s*(?:[,;]|$)",
    re.IGNORECASE,
)

_MAX_CAPTION_CHARS = 80
_TRIM_CHARS = " \t\n.,;:!¡¿?-"


class CaptionExtractor:
    """Detects an optional caption phrase inside a meme prompt."""

    def extract(self, prompt: str) -> ExtractedCaption:
        """Return cleaned prompt and caption if present, otherwise caption=None."""
        if not prompt or not prompt.strip():
            return ExtractedCaption(cleaned_prompt=prompt, caption=None)

        text = prompt.strip()
        match = _QUOTED_PATTERN.search(text) or _UNQUOTED_PATTERN.search(text)
        if match is None:
            return ExtractedCaption(cleaned_prompt=text, caption=None)

        caption = match.group("caption").strip().strip(_TRIM_CHARS)
        if not caption:
            return ExtractedCaption(cleaned_prompt=text, caption=None)

        if len(caption) > _MAX_CAPTION_CHARS:
            caption = caption[:_MAX_CAPTION_CHARS].rstrip()

        cleaned = (text[: match.start()] + " " + text[match.end():]).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip(_TRIM_CHARS)
        if not cleaned:
            # Avoid sending an empty prompt to the LLM. Fall back to original
            # so the scene still has context, even if it includes the caption phrase.
            cleaned = text

        return ExtractedCaption(cleaned_prompt=cleaned, caption=caption)
