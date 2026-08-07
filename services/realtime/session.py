"""Checkpointed support-chat sessions and their single generation producer."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field

try:
    from services.agent.graph import invoke_agent
except ModuleNotFoundError:  # pragma: no cover - supports running from services/api
    from agent.graph import invoke_agent

from .events import (
    CHAT_GENERATION_COMPLETED,
    CHAT_GENERATION_FAILED,
    CHAT_GENERATION_INTERRUPTED,
    CHAT_GENERATION_STARTED,
    CHAT_MESSAGE_RECEIVED,
    CHAT_PROTOCOL_ERROR,
    CHAT_SESSION_CONNECTED,
    CHAT_TOKEN_EMITTED,
    build_event,
)
from .pubsub import SessionEventBus

logger = logging.getLogger("healthcore.realtime")


class ChatClientMessage(BaseModel):
    """Inbound WebSocket contract; user text is never put in telemetry events."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["chat_message", "chat_interrupt"]
    properties: dict[str, Any] = Field(default_factory=dict)


class RealtimeState(TypedDict, total=False):
    session_id: str
    question: str
    message_id: str
    trace_id: str
    status: str


class _Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.active = False
        self.awaiting_resume = False
        self.graph_task: asyncio.Task[Any] | None = None
        self.cancel_event: threading.Event | None = None
        self.pending_resume: tuple[str, str] | None = None
        self.message_ids: set[str] = set()
        self.last_trace_id: str | None = None


class ChatSessionManager:
    """Own one checkpointed graph thread per chat session.

    This manager is deliberately process-local for the assignment: the pub/sub
    boundary is explicit and can be replaced by Redis later without changing
    the WebSocket contract or the support-agent graph.
    """

    def __init__(self, *, bus: SessionEventBus | None = None) -> None:
        self.bus = bus or SessionEventBus()
        self._sessions: dict[str, _Session] = {}
        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._sessions_lock = asyncio.Lock()

    def _build_graph(self):
        builder = StateGraph(RealtimeState)
        builder.add_node("generate_support_response", self._generate_node)
        builder.add_node("wait_for_next_message", self._wait_for_next_message_node)
        builder.add_edge(START, "generate_support_response")
        builder.add_edge("generate_support_response", "wait_for_next_message")
        builder.add_edge("wait_for_next_message", "generate_support_response")
        return builder.compile(checkpointer=self._checkpointer)

    async def connect(self, session_id: str) -> list[dict[str, Any]]:
        self._loop = asyncio.get_running_loop()
        session = await self._get_session(session_id)
        history = await self.bus.history(session_id)
        await self.bus.publish(
            session_id,
            build_event(
                session_id,
                CHAT_SESSION_CONNECTED,
                {"clientCount": 1, "resumeAvailable": session.awaiting_resume or session.active},
            ),
        )
        return history

    @asynccontextmanager
    async def subscribe(self, session_id: str) -> AsyncIterator[tuple[asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]]:
        self._loop = asyncio.get_running_loop()
        await self._get_session(session_id)
        async with self.bus.subscribe(session_id) as subscription:
            yield subscription

    async def disconnect(self, session_id: str) -> None:
        # Generation continues after a client disconnects; a later subscriber
        # receives the bounded history and the same LangGraph thread remains.
        await self._get_session(session_id)

    async def handle_message(self, session_id: str, raw: Any) -> None:
        try:
            message = ChatClientMessage.model_validate(raw)
        except (TypeError, ValueError) as exc:
            await self._publish_protocol_error(session_id, f"Invalid chat event: {exc}")
            return

        text = str(message.properties.get("message") or "").strip()
        message_id = str(message.properties.get("messageId") or uuid4())
        if message_id in (await self._get_session(session_id)).message_ids:
            await self._publish_protocol_error(session_id, "Duplicate message ignored.")
            return
        if not text and message.event_type == "chat_message":
            await self._publish_protocol_error(session_id, "Message cannot be empty.")
            return

        session = await self._get_session(session_id)
        session.message_ids.add(message_id)
        await self.bus.publish(
            session_id,
            build_event(
                session_id,
                CHAT_MESSAGE_RECEIVED,
                {"messageId": message_id, "messageKind": message.event_type},
            ),
        )

        if message.event_type == "chat_interrupt":
            await self._interrupt(session, text, message_id)
            return

        if session.active:
            # A new message while a response is streaming is an intentional
            # interrupt, not a second concurrent agent invocation.
            await self._interrupt(session, text, message_id)
        elif session.awaiting_resume:
            await self._resume(session, text, message_id)
        else:
            await self._start(session, text, message_id)

    async def _interrupt(self, session: _Session, text: str, message_id: str) -> None:
        if not session.active or session.cancel_event is None:
            if text and session.awaiting_resume:
                await self._resume(session, text, message_id)
                return
            await self._publish_protocol_error(session.session_id, "No response is currently generating.")
            return
        session.pending_resume = (text, message_id) if text else None
        session.cancel_event.set()

    async def _start(self, session: _Session, question: str, message_id: str) -> None:
        session.active = True
        session.awaiting_resume = False
        session.cancel_event = threading.Event()
        config = {"configurable": {"thread_id": session.session_id}}
        session.graph_task = asyncio.create_task(
            self._run_graph(
                session,
                {"session_id": session.session_id, "question": question, "message_id": message_id},
                config,
            )
        )

    async def _resume(self, session: _Session, question: str, message_id: str) -> None:
        session.active = True
        session.awaiting_resume = False
        session.cancel_event = threading.Event()
        config = {"configurable": {"thread_id": session.session_id}}
        session.graph_task = asyncio.create_task(
            self._run_graph(session, Command(resume={"question": question, "message_id": message_id}), config)
        )

    async def _run_graph(self, session: _Session, input_value: Any, config: dict[str, Any]) -> None:
        try:
            result = await asyncio.to_thread(self._graph.invoke, input_value, config)
        except Exception:
            logger.exception("Realtime graph failed: session_id=%s", session.session_id)
            session.active = False
            session.cancel_event = None
            await self.bus.publish(
                session.session_id,
                build_event(session.session_id, CHAT_GENERATION_FAILED, {"reason": "graph_error"}),
            )
            return

        session.active = False
        session.cancel_event = None
        interrupted = bool(result.get("__interrupt__")) if isinstance(result, dict) else False
        session.awaiting_resume = interrupted
        if interrupted and session.pending_resume:
            pending = session.pending_resume
            session.pending_resume = None
            await self._resume(session, pending[0], pending[1])

    def _generate_node(self, state: RealtimeState) -> dict[str, Any]:
        session_id = state["session_id"]
        session = self._sessions[session_id]
        message_id = state["message_id"]
        trace_id = f"chat-{session_id}-{uuid4().hex}"
        session.last_trace_id = trace_id
        self._publish_from_worker(
            session_id,
            build_event(
                session_id,
                CHAT_GENERATION_STARTED,
                {"messageId": message_id, "traceId": trace_id},
                request_id=trace_id,
            ),
        )
        try:
            result = invoke_agent(state["question"], trace_id=trace_id)
            answer = str(result.get("answer") or "").strip()
            if result.get("error"):
                self._publish_from_worker(
                    session_id,
                    build_event(
                        session_id,
                        CHAT_GENERATION_FAILED,
                        {"messageId": message_id, "traceId": trace_id, "reason": "agent_error"},
                        request_id=trace_id,
                    ),
                )
                return {"status": "failed", "trace_id": trace_id}
        except Exception:
            logger.exception("Support-agent generation failed: session_id=%s", session_id)
            self._publish_from_worker(
                session_id,
                build_event(
                    session_id,
                    CHAT_GENERATION_FAILED,
                    {"messageId": message_id, "traceId": trace_id, "reason": "agent_error"},
                    request_id=trace_id,
                ),
            )
            return {"status": "failed", "trace_id": trace_id}

        emitted = 0
        for token in _tokens(answer):
            if session.cancel_event is not None and session.cancel_event.is_set():
                self._publish_from_worker(
                    session_id,
                    build_event(
                        session_id,
                        CHAT_GENERATION_INTERRUPTED,
                        {
                            "messageId": message_id,
                            "traceId": trace_id,
                            "reason": "client_interrupt",
                            "partialTokenCount": emitted,
                        },
                        request_id=trace_id,
                    ),
                )
                return {"status": "interrupted", "trace_id": trace_id}
            self._publish_from_worker(
                session_id,
                build_event(
                    session_id,
                    CHAT_TOKEN_EMITTED,
                    {"messageId": message_id, "traceId": trace_id, "sequence": emitted, "token": token},
                    request_id=trace_id,
                ),
            )
            emitted += 1
            # The short yield makes cooperative cancellation observable in local
            # development while the agent work remains outside the WebSocket.
            threading.Event().wait(0.01)

        self._publish_from_worker(
            session_id,
            build_event(
                session_id,
                CHAT_GENERATION_COMPLETED,
                {"messageId": message_id, "traceId": trace_id, "tokenCount": emitted},
                request_id=trace_id,
            ),
        )
        return {"status": "completed", "trace_id": trace_id}

    def _wait_for_next_message_node(self, state: RealtimeState) -> dict[str, Any]:
        """Checkpoint after a response; resume continues from this node."""

        decision = interrupt(
            {
                "event_type": "chat_generation_waiting",
                "sessionId": state["session_id"],
                "messageId": state["message_id"],
            }
        )
        if not isinstance(decision, dict) or not str(decision.get("question") or "").strip():
            return {"status": "closed"}
        return {
            "question": str(decision["question"]).strip(),
            "message_id": str(decision.get("message_id") or uuid4()),
            "status": "resumed",
        }

    def _publish_from_worker(self, session_id: str, event: dict[str, Any]) -> None:
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self.bus.publish(session_id, event), self._loop)
        future.result(timeout=5)

    async def _publish_protocol_error(self, session_id: str, message: str) -> None:
        await self.bus.publish(
            session_id,
            build_event(session_id, CHAT_PROTOCOL_ERROR, {"message": message}),
        )

    async def _get_session(self, session_id: str) -> _Session:
        async with self._sessions_lock:
            return self._sessions.setdefault(session_id, _Session(session_id))


def _tokens(answer: str) -> list[str]:
    """Split into display tokens while retaining whitespace for natural typing."""

    return re.findall(r"\S+\s*", answer)


chat_sessions = ChatSessionManager()
