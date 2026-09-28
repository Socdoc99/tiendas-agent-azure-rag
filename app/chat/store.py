"""Intentionally in-memory storage for public conversation history."""

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PublicMessage:
    """Only natural-language content that may be reused between turns."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class Conversation:
    """One conversation and its lock for serializing same-chat turns."""

    conversation_id: UUID
    lock: Lock = field(default_factory=Lock, repr=False, compare=False)
    _messages: list[PublicMessage] = field(default_factory=list, repr=False)

    def snapshot(self) -> tuple[PublicMessage, ...]:
        """Return a copy of the public history."""

        return tuple(self._messages)

    def append_turn(self, user_message: str, assistant_message: str) -> None:
        """Persist one complete turn, never intermediate graph messages."""

        self._messages.extend(
            (
                PublicMessage(role="user", content=user_message),
                PublicMessage(role="assistant", content=assistant_message),
            )
        )


class ConversationStore:
    """Process-local conversation store; restart intentionally clears it."""

    def __init__(self) -> None:
        self._conversations: dict[UUID, Conversation] = {}
        self._lock = Lock()

    def create(self) -> Conversation:
        """Create a server-generated conversation ID."""

        conversation = Conversation(conversation_id=uuid4())
        with self._lock:
            self._conversations[conversation.conversation_id] = conversation
        return conversation

    def get(self, conversation_id: UUID) -> Conversation | None:
        """Return an existing conversation, without creating arbitrary IDs."""

        with self._lock:
            return self._conversations.get(conversation_id)

    def snapshot(self, conversation_id: UUID) -> tuple[PublicMessage, ...]:
        """Read public history for tests and service-level consumers."""

        conversation = self.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError("Conversation does not exist")
        with conversation.lock:
            return conversation.snapshot()


class ConversationNotFoundError(LookupError):
    """Raised when a client references a UUID absent from this process."""
