"""Aiogram bot factory and polling lifecycle helpers."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.bot.context import BotContext
from src.bot.handlers.meme import router as meme_router
from src.config.settings import Settings


def build_dispatcher(bot_context: BotContext) -> Dispatcher:
    """Build dispatcher and attach routers and shared dependencies."""
    dispatcher = Dispatcher()
    dispatcher.include_router(meme_router)
    dispatcher["bot_context"] = bot_context
    return dispatcher


async def start_bot_polling(
    settings: Settings,
    dispatcher: Dispatcher,
) -> tuple[Bot, asyncio.Task[None]]:
    """Create bot instance and start polling in a background task."""
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    polling_task = asyncio.create_task(dispatcher.start_polling(bot))
    logger.info("Telegram polling started")
    return bot, polling_task


async def stop_bot_polling(bot: Bot, polling_task: asyncio.Task[None]) -> None:
    """Stop polling task and close bot session cleanly."""
    if not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("Telegram polling task cancelled")

    await bot.session.close()
    logger.info("Telegram bot session closed")
