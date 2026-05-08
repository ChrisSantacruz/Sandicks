"""Local test runner for the meme generation pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from src.config.settings import get_settings
from src.core.logging import configure_logging
from src.services.caption_extractor import CaptionExtractor
from src.services.image_caption_renderer import ImageCaptionRenderer
from src.services.image_generation import ImageGenerationService
from src.services.logo_overlay_renderer import LogoOverlayRenderer
from src.services.meme_orchestrator import MemeOrchestrationError, MemeOrchestrator
from src.services.prompt_service import PromptService

TEST_PROMPT = "personaje en una playa con lentes de sol y camisa playera diciendo \"dev life\""


async def _run_test(prompt: str = TEST_PROMPT) -> Path:
    """Generate one meme image and return the output path."""
    settings = get_settings()
    configure_logging(settings)

    prompt_service = PromptService(settings=settings)
    image_generation_service = ImageGenerationService(settings=settings)
    caption_extractor = CaptionExtractor()
    caption_renderer = ImageCaptionRenderer(settings=settings)
    logo_renderer = LogoOverlayRenderer(settings=settings)
    orchestrator = MemeOrchestrator(
        settings=settings,
        prompt_enhancer=prompt_service,
        image_generator=image_generation_service,
        caption_extractor=caption_extractor,
        caption_renderer=caption_renderer,
        logo_renderer=logo_renderer,
    )

    output_path = await orchestrator.create_meme(prompt)
    return output_path


def main() -> int:
    """Execute test generation and print output image path."""
    try:
        output_path = asyncio.run(_run_test())
    except MemeOrchestrationError as exc:
        logger.error("Meme generation pipeline failed: {}", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during local test generation: {}", exc)
        return 1

    print(output_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
