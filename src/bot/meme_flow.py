"""Conversation and queue state for meme generation."""

import asyncio
from dataclasses import dataclass


@dataclass(slots=True)
class PendingMemeRequest:
    """Tracks temporary messages for a pending `/meme` prompt."""

    command_message_id: int
    bot_prompt_message_id: int


class MemeConversationStore:
    """Keeps pending `/meme` requests per chat-user pair."""

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], PendingMemeRequest] = {}

    def set_pending(self, chat_id: int, user_id: int, request: PendingMemeRequest) -> None:
        self._pending[(chat_id, user_id)] = request

    def pop_pending(self, chat_id: int, user_id: int) -> PendingMemeRequest | None:
        return self._pending.pop((chat_id, user_id), None)

    def has_pending(self, chat_id: int, user_id: int) -> bool:
        return (chat_id, user_id) in self._pending


class MemeGenerationQueue:
    """Global FIFO queue that enforces sequential meme generation."""

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._next_ticket = 0
        self._serving_ticket = 0

    async def acquire_turn(self) -> tuple[int, int]:
        """Reserve and wait for the next available generation turn."""
        async with self._condition:
            ticket = self._next_ticket
            self._next_ticket += 1
            users_ahead = ticket - self._serving_ticket
            while ticket != self._serving_ticket:
                await self._condition.wait()
            return ticket, users_ahead

    async def release_turn(self) -> None:
        """Allow the next waiting request to start generation."""
        async with self._condition:
            self._serving_ticket += 1
            self._condition.notify_all()
