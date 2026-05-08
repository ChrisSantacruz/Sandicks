"""Shared application context for Telegram handlers."""

from dataclasses import dataclass

from src.bot.meme_flow import MemeConversationStore, MemeGenerationQueue
from src.services.meme_orchestrator import MemeOrchestrator
from src.services.meme_prompt_parser import MemePromptParser


@dataclass(slots=True)
class BotContext:
    """Container for dependencies used by handlers."""

    meme_orchestrator: MemeOrchestrator
    meme_prompt_parser: MemePromptParser
    meme_queue: MemeGenerationQueue
    meme_conversations: MemeConversationStore
