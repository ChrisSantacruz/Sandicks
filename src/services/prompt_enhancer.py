"""Service that improves meme prompts using an external LLM."""
from typing import Any

import httpx
from loguru import logger

from src.config.settings import Settings
from src.utils.prompt_loader import load_prompt_file


class PromptEnhancementError(Exception):
    """Raised when prompt enhancement fails."""


class PromptEnhancerService:
    """Builds optimized generation prompts from short user input."""

    def __init__(self, settings: Settings) -> None:
        """Initialize service with runtime settings and loaded prompt templates."""
        self._settings = settings
        prompts_root = settings.prompts_root
        self._system_prompt = load_prompt_file(prompts_root / "system" / "main_system.md")
        self._enhancer_prompt = load_prompt_file(prompts_root / "image" / "meme_enhancer.md")
        self._base_character_prompt = load_prompt_file(prompts_root / "image" / "base_character.md")

    async def enhance(self, user_prompt: str) -> str:
        """Enhance a user prompt while preserving mascot identity constraints."""
        if not user_prompt.strip():
            raise PromptEnhancementError("The meme prompt is empty.")

        payload: dict[str, Any] = {
            "model": self._settings.groq_model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{self._enhancer_prompt}\n\n"
                        f"Base mascot rules:\n{self._base_character_prompt}\n\n"
                        f"User idea:\n{user_prompt.strip()}"
                    ),
                },
            ],
            "temperature": 0.7,
            "max_tokens": 220,
        }
        headers = {"Authorization": f"Bearer {self._settings.groq_api_key}"}

        logger.info("Enhancing prompt with LLM model={}", self._settings.groq_model)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except ValueError as exc:
            logger.exception("Prompt enhancer returned non-JSON payload")
            raise PromptEnhancementError("Prompt enhancement returned malformed JSON.") from exc
        except httpx.HTTPStatusError as exc:
            logger.exception("Prompt enhancer HTTP error status={}", exc.response.status_code)
            raise PromptEnhancementError(
                f"Prompt enhancement request failed with status {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Prompt enhancer transport error")
            raise PromptEnhancementError("Prompt enhancement service is unavailable.") from exc

        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            logger.exception("Prompt enhancer response has unexpected shape")
            raise PromptEnhancementError("Prompt enhancement returned an invalid response.") from exc

        if not content:
            raise PromptEnhancementError("Prompt enhancement returned empty content.")

        logger.info("Prompt enhanced successfully")
        return content
