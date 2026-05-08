"""FastAPI application factory and lifespan wiring."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from loguru import logger

from src.api.routes.health import router as health_router
from src.bot.application import build_dispatcher, start_bot_polling, stop_bot_polling
from src.bot.context import BotContext
from src.bot.meme_flow import MemeConversationStore, MemeGenerationQueue
from src.config.settings import Settings, get_settings
from src.core.logging import configure_logging
from src.services.caption_extractor import CaptionExtractor
from src.services.image_caption_renderer import ImageCaptionRenderer
from src.services.image_generation import ImageGenerationService
from src.services.logo_overlay_renderer import LogoOverlayRenderer
from src.services.meme_orchestrator import MemeOrchestrator
from src.services.meme_prompt_parser import MemePromptParser
from src.services.prompt_service import PromptService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down long-lived application resources."""
    settings: Settings = get_settings()
    configure_logging(settings)

    prompt_enhancer = PromptService(settings=settings)
    image_generator = ImageGenerationService(settings=settings)
    caption_extractor = CaptionExtractor()
    caption_renderer = ImageCaptionRenderer(settings=settings)
    logo_renderer = LogoOverlayRenderer(settings=settings)
    meme_prompt_parser = MemePromptParser()
    bot_context = BotContext(
        meme_orchestrator=MemeOrchestrator(
            settings=settings,
            prompt_enhancer=prompt_enhancer,
            image_generator=image_generator,
            caption_extractor=caption_extractor,
            caption_renderer=caption_renderer,
            logo_renderer=logo_renderer,
        ),
        meme_prompt_parser=meme_prompt_parser,
        meme_queue=MemeGenerationQueue(),
        meme_conversations=MemeConversationStore(),
    )

    dispatcher = build_dispatcher(bot_context=bot_context)
    bot, polling_task = await start_bot_polling(settings=settings, dispatcher=dispatcher)
    app.state.bot = bot
    app.state.polling_task = polling_task
    logger.info("Application startup complete")

    try:
        yield
    finally:
        await stop_bot_polling(bot=bot, polling_task=polling_task)
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create configured FastAPI app."""
    app = FastAPI(title="Telegram AI Meme Bot", lifespan=lifespan)
    app.include_router(health_router)
    return app
