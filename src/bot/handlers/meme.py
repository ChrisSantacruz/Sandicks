"""Telegram handlers for meme generation commands."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message
from loguru import logger

from src.bot.context import BotContext
from src.bot.meme_flow import PendingMemeRequest
from src.config.settings import get_settings
from src.services.meme_orchestrator import MemeOrchestrationError

router = Router(name="meme-handler")
settings = get_settings()


HELP_TEXT = (
    "CRYPTO MEME BOT - QUICK ALPHA\n\n"
    "How it works:\n"
    "1) Send /meme\n"
    "2) I ask for your meme idea\n"
    "3) Send one clear prompt with scene + vibe + optional caption\n"
    "4) I generate and drop your meme in chat\n\n"
    "Prompt examples:\n"
    '- "Bull mascot in Times Square, green candles everywhere, saying \\"WE ARE SO BACK\\""\n'
    '- "A degen trader on a rocket to the moon, neon cyberpunk, with text \\"BUY THE DIP\\""\n'
    '- "Diamond hands warrior in a storm, dramatic lighting, that says \\"HODL THE LINE\\""\n\n'
    "What is not allowed:\n"
    "- Hate or harassment\n"
    "- Explicit sexual content\n"
    "- Graphic violence\n"
    "- Illegal activity promotion\n"
    "- Personal data leaks or doxxing\n\n"
    "Keep it creative, safe, and meme-worthy."
)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Handle /start command with quick usage instructions."""
    await message.answer("Welcome. Use /meme to create a meme or /help to see commands.")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Show available bot commands."""
    await message.answer(HELP_TEXT)


@router.message(Command("chatid"))
async def chat_id_handler(message: Message) -> None:
    """Show current chat id for setup/debug."""
    await message.answer(f"Current chat id: `{message.chat.id}`")


async def _safe_delete_message(message: Message) -> None:
    """Delete message if possible, ignore common delete errors."""
    try:
        await message.delete()
    except TelegramBadRequest:
        logger.debug("Could not delete message id={}", message.message_id)


async def _safe_delete_by_id(message: Message, message_id: int) -> None:
    """Delete message by id if possible, ignore common delete errors."""
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
    except TelegramBadRequest:
        logger.debug("Could not delete message id={}", message_id)


@router.message(Command("meme"))
async def meme_command_handler(message: Message, bot_context: BotContext) -> None:
    """Start interactive meme creation flow."""
    if not message.from_user:
        return

    if message.chat.id != settings.telegram_allowed_chat_id:
        await message.answer(
            "This bot only works in the configured chat.\n"
            f"Allowed chat id: `{settings.telegram_allowed_chat_id}`\n"
            f"Current chat id: `{message.chat.id}`\n"
            "Use /chatid here to verify where you are sending commands."
        )
        await _safe_delete_message(message)
        return

    await _safe_delete_message(message)

    user_id = message.from_user.id
    chat_id = message.chat.id

    if bot_context.meme_conversations.has_pending(chat_id=chat_id, user_id=user_id):
        await message.answer("You already started a meme. Please send your description.")
        return

    prompt_message = await message.answer(
        "How do you want your meme? Send me a full description now."
    )
    bot_context.meme_conversations.set_pending(
        chat_id=chat_id,
        user_id=user_id,
        request=PendingMemeRequest(
            command_message_id=message.message_id,
            bot_prompt_message_id=prompt_message.message_id,
        ),
    )


@router.message(F.text)
async def fallback_text_handler(message: Message, bot_context: BotContext) -> None:
    """Consume pending meme descriptions or show guidance."""
    if not message.from_user or not message.text:
        return

    if message.chat.id != settings.telegram_allowed_chat_id:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    pending_request = bot_context.meme_conversations.pop_pending(chat_id=chat_id, user_id=user_id)
    if not pending_request:
        await message.answer("Use /meme to start creating a meme or /help for command list.")
        return

    await _safe_delete_message(message)
    await _safe_delete_by_id(message=message, message_id=pending_request.command_message_id)
    await _safe_delete_by_id(message=message, message_id=pending_request.bot_prompt_message_id)

    _, users_ahead = await bot_context.meme_queue.acquire_turn()
    queue_note = (
        f" ({users_ahead} request(s) ahead in queue)"
        if users_ahead > 0
        else ""
    )
    waiting_message = await message.answer(f"Your meme is being generated{queue_note}.")

    image_path: str | None = None
    try:
        image_path = await bot_context.meme_orchestrator.create_meme(message.text.strip())
    except MemeOrchestrationError as exc:
        logger.warning("Meme generation failed error={}", str(exc))
        await waiting_message.edit_text("I could not generate your meme right now. Please try again.")
        return
    finally:
        await bot_context.meme_queue.release_turn()

    await _safe_delete_message(waiting_message)
    if image_path is None:
        return

    username = message.from_user.username or message.from_user.full_name
    caption = (
        f"Meme generated by @{message.from_user.username}"
        if message.from_user.username
        else f"Meme generated by {username}"
    )
    await message.answer_photo(photo=FSInputFile(path=image_path), caption=caption)
