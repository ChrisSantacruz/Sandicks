"""Service to parse and validate `/meme` command payloads."""

from dataclasses import dataclass


class MemePromptParseError(Exception):
    """Raised when a meme command does not include a valid prompt."""


@dataclass(slots=True)
class ParsedMemePrompt:
    """Normalized parsed `/meme` command content."""

    raw_input: str
    normalized_prompt: str


class MemePromptParser:
    """Parses user text and extracts the prompt after `/meme`."""

    def parse_command_text(self, text: str | None) -> ParsedMemePrompt:
        """Parse and validate command text from Telegram messages."""
        if not text:
            raise MemePromptParseError("Message text is empty.")

        stripped_text = text.strip()
        if not stripped_text:
            raise MemePromptParseError("Message text is blank.")

        command_and_rest = stripped_text.split(maxsplit=1)
        command = command_and_rest[0]
        command_name = command.split("@", maxsplit=1)[0].lower()
        if command_name != "/meme":
            raise MemePromptParseError("Unsupported command format for meme generation.")

        prompt = command_and_rest[1].strip() if len(command_and_rest) == 2 else ""
        if not prompt:
            raise MemePromptParseError("No meme prompt provided.")

        return ParsedMemePrompt(raw_input=text, normalized_prompt=prompt)
