"""Reusable async service for meme prompt enhancement via LLM providers."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

from groq import Groq
from loguru import logger

from src.config.settings import Settings
from src.utils.prompt_loader import load_prompt_file


class PromptServiceError(Exception):
    """Raised when prompt enhancement fails."""


class LlmProviderError(Exception):
    """Raised when an LLM provider call fails."""


@dataclass(frozen=True, slots=True)
class LlmRequest:
    """Provider-agnostic request payload for chat completion."""

    model: str
    system_prompt: str
    user_prompt: str
    temperature: float
    max_completion_tokens: int
    top_p: float


class LlmProvider(Protocol):
    """Contract for pluggable prompt completion providers."""

    async def complete(self, request: LlmRequest) -> str:
        """Return generated prompt text."""


class GroqProvider:
    """Groq provider implementation using streaming chat completions."""

    def __init__(self, api_key: str) -> None:
        self._client = Groq(api_key=api_key)

    async def complete(self, request: LlmRequest) -> str:
        try:
            content = await asyncio.to_thread(self._complete_sync, request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Groq provider call failed")
            raise LlmProviderError("Groq completion request failed.") from exc

        normalized = content.strip()
        if not normalized:
            raise LlmProviderError("Groq completion returned empty content.")
        return normalized

    def _complete_sync(self, request: LlmRequest) -> str:
        completion = self._client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            temperature=request.temperature,
            max_completion_tokens=request.max_completion_tokens,
            top_p=request.top_p,
            stream=True,
            stop=None,
        )

        chunks: list[str] = []
        for chunk in completion:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                chunks.append(delta)
        return "".join(chunks)


class PromptService:
    """Enhances short meme ideas into concise cinematic prompts."""

    def __init__(self, settings: Settings, provider: LlmProvider | None = None) -> None:
        self._settings = settings
        self._provider = provider or GroqProvider(api_key=settings.groq_api_key)
        prompts_root = settings.prompts_root
        self._system_prompt = load_prompt_file(prompts_root / "system" / "main_system.md")
        self._enhancer_prompt = load_prompt_file(prompts_root / "image" / "meme_enhancer.md")
        self._base_character_prompt = load_prompt_file(prompts_root / "image" / "base_character.md")
        self._request_template = load_prompt_file(prompts_root / "image" / "prompt_request_template.md")

    async def enhance(self, short_prompt: str) -> str:
        """Build optimized prompt text from short meme prompt input."""
        normalized_prompt = short_prompt.strip()
        if not normalized_prompt:
            raise PromptServiceError("The meme prompt is empty.")

        request = LlmRequest(
            model=self._settings.groq_model,
            system_prompt=self._system_prompt,
            user_prompt=self._build_user_prompt(normalized_prompt),
            temperature=self._settings.groq_temperature,
            max_completion_tokens=self._settings.groq_max_completion_tokens,
            top_p=self._settings.groq_top_p,
        )

        logger.info("Enhancing prompt model={} provider=groq", request.model)
        try:
            optimized_prompt = await self._provider.complete(request)
        except LlmProviderError as exc:
            raise PromptServiceError("Prompt enhancement provider failed.") from exc

        return self._enforce_output_size(optimized_prompt)

    def _build_user_prompt(self, short_prompt: str) -> str:
        return self._request_template.format(
            enhancer_prompt=self._enhancer_prompt,
            base_character_prompt=self._base_character_prompt,
            user_idea=short_prompt,
        )

    def _enforce_output_size(self, output: str) -> str:
        # Keep output compact for lower token usage in downstream image calls.
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        single_line = " ".join(lines)
        words = single_line.split()
        if len(words) > self._settings.prompt_output_max_words:
            return " ".join(words[: self._settings.prompt_output_max_words]).rstrip(",.;: ")
        return single_line
