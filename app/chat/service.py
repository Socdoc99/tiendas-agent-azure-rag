"""Application service between FastAPI and the existing LangGraph."""

from collections.abc import Callable, Sequence
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import AgentRunResult, run_agent_turn
from app.chat.models import MAX_MESSAGE_LENGTH, ChatResponse
from app.chat.store import Conversation, ConversationNotFoundError, ConversationStore

AgentTurnRunner = Callable[..., AgentRunResult]


class ChatAgentUnavailableError(RuntimeError):
    """Raised when the agent cannot complete a turn."""


class ChatService:
    """Resolve conversations, run the graph, and persist only completed turns."""

    def __init__(
        self,
        graph: object,
        *,
        store: ConversationStore | None = None,
        runner: AgentTurnRunner = run_agent_turn,
    ) -> None:
        self.graph = graph
        self.store = store or ConversationStore()
        self.runner = runner

    def chat(
        self,
        message: str,
        conversation_id: UUID | None = None,
    ) -> ChatResponse:
        """Run one serialized turn and return its safe public response."""

        normalized_message = self._validate_message(message)
        conversation = self._resolve_conversation(conversation_id)

        # The lock is per conversation, so different conversations can run in
        # parallel while same-conversation turns retain deterministic ordering.
        with conversation.lock:
            history = self._to_langchain_history(conversation.snapshot())
            try:
                result = self.runner(
                    self.graph,
                    normalized_message,
                    history=history,
                )
                answer = result.final_answer.strip()
                if not answer:
                    raise ValueError("The agent returned an empty answer")
            except Exception as error:
                raise ChatAgentUnavailableError from error

            conversation.append_turn(normalized_message, answer)
            return ChatResponse(
                conversation_id=conversation.conversation_id,
                answer=answer,
                query_count=result.query_count,
            )

    def _resolve_conversation(self, conversation_id: UUID | None) -> Conversation:
        if conversation_id is None:
            return self.store.create()
        conversation = self.store.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError("Conversation does not exist")
        return conversation

    @staticmethod
    def _validate_message(message: str) -> str:
        if not isinstance(message, str):
            raise ValueError("message must be a string")
        normalized = message.strip()
        if not normalized:
            raise ValueError("message must not be empty")
        if len(normalized) > MAX_MESSAGE_LENGTH:
            raise ValueError("message is too long")
        return normalized

    @staticmethod
    def _to_langchain_history(
        messages: Sequence[object],
    ) -> list[HumanMessage | AIMessage]:
        history: list[HumanMessage | AIMessage] = []
        for message in messages:
            role = getattr(message, "role", None)
            content = getattr(message, "content", None)
            if role == "user" and isinstance(content, str):
                history.append(HumanMessage(content=content))
            elif role == "assistant" and isinstance(content, str):
                history.append(AIMessage(content=content))
            else:
                raise ValueError("Conversation history contains a non-public message")
        return history
