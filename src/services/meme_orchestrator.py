"""Application service that orchestrates prompt enhancement and image generation."""

import asyncio
from pathlib import Path

from loguru import logger

from src.config.settings import Settings
from src.services.caption_extractor import CaptionExtractor
from src.services.image_caption_renderer import ImageCaptionRenderer
from src.services.image_generation import ImageGenerationError, ImageGenerationService
from src.services.logo_overlay_renderer import LogoOverlayRenderer
from src.services.prompt_service import PromptService, PromptServiceError


class MemeOrchestrationError(Exception):
    """Raised when the meme generation pipeline fails."""


class MemeOrchestrator:
    """Coordinates prompt optimization, image generation and caption overlay."""

    def __init__(
        self,
        settings: Settings,
        prompt_enhancer: PromptService,
        image_generator: ImageGenerationService,
        caption_extractor: CaptionExtractor,
        caption_renderer: ImageCaptionRenderer,
        logo_renderer: LogoOverlayRenderer,
    ) -> None:
        """Initialize orchestrator with reusable services."""
        self._settings = settings
        self._prompt_enhancer = prompt_enhancer
        self._image_generator = image_generator
        self._caption_extractor = caption_extractor
        self._caption_renderer = caption_renderer
        self._logo_renderer = logo_renderer

    async def create_meme(self, user_prompt: str, model: str | None = None) -> Path:
        """Run full meme pipeline and return generated image path."""
        normalized_prompt = user_prompt.strip()
        if not normalized_prompt:
            raise MemeOrchestrationError("Prompt cannot be empty.")

        extracted = self._caption_extractor.extract(normalized_prompt)
        prompt_for_enhancement = extracted.cleaned_prompt or normalized_prompt
        if extracted.caption:
            logger.info(
                "Caption detected for overlay caption_chars={}", len(extracted.caption)
            )

        try:
            image_path = await asyncio.wait_for(
                self._create_meme_pipeline(prompt_for_enhancement, model=model),
                timeout=self._settings.generation_timeout_seconds,
            )
        except PromptServiceError as exc:
            logger.warning("Prompt enhancement pipeline failed")
            raise MemeOrchestrationError("Prompt enhancement failed.") from exc
        except ImageGenerationError as exc:
            logger.warning("Image generation pipeline failed")
            raise MemeOrchestrationError("Image generation failed.") from exc
        except asyncio.TimeoutError as exc:
            logger.warning("Meme generation timed out")
            raise MemeOrchestrationError("Image generation timed out.") from exc

        if extracted.caption:
            try:
                await asyncio.to_thread(
                    self._caption_renderer.render_caption,
                    image_path,
                    extracted.caption,
                )
            except Exception as exc:  # noqa: BLE001
                # Caption overlay failure should not lose the generated image.
                logger.warning("Caption overlay failed error={}", exc)

        try:
            await asyncio.to_thread(self._logo_renderer.render_logo, image_path)
        except Exception as exc:  # noqa: BLE001
            # Logo overlay failure should not lose the generated image.
            logger.warning("Logo overlay failed error={}", exc)

        return image_path

    async def _create_meme_pipeline(self, user_prompt: str, model: str | None = None) -> Path:
        """Enhance prompt and generate the final image path."""
        enhanced_prompt = await self._prompt_enhancer.enhance(user_prompt)
        return await self._image_generator.generate_image_path(enhanced_prompt, model=model)
