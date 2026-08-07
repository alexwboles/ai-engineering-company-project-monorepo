# HealthCore WebSocket Chat

The backoffice support chat uses `WS /ws/chat/{session_id}`. It wraps the
existing HealthCore support-agent graph; it does not change the agent's tools,
memory, or answer policy.

## Event contract

Server events reuse the telemetry envelope already used by the backoffice:

`eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`,
`requestId`, and `properties`.

The relevant lower-snake-case events are:

- `chat_session_connected`: a client joined; `properties` includes whether a checkpoint can resume.
- `chat_message_received`: the producer accepted a message; only its opaque `messageId` and kind are emitted.
- `chat_generation_started`: the agent producer began a run; includes `messageId` and `traceId`.
- `chat_token_emitted`: one display token; includes `messageId`, `sequence`, `token`, and `traceId`.
- `chat_generation_interrupted`: cooperative cancellation stopped the current response; includes the partial token count.
- `chat_generation_completed`: all tokens were sent successfully.
- `chat_generation_failed`: the agent or graph failed without exposing internal details.
- `chat_protocol_error`: the client sent an invalid or unusable event.

Clients send either:

```json
{"event_type":"chat_message","properties":{"message":"What is our UK data policy?","messageId":"client-generated-id"}}
```

or, while a response is streaming:

```json
{"event_type":"chat_interrupt","properties":{"message":"Check the billing policy instead.","messageId":"replacement-id"}}
```

## Why WebSockets instead of SSE

Part 1's server-sent events channel was server-to-client only. This ticket
requires a client interrupt and replacement question while the server is still
streaming, so one persistent bidirectional WebSocket is the correct transport.

## Producer, consumers, and reconnects

`ChatSessionManager` creates one checkpointed LangGraph thread per
`session_id`. It is the single producer: two browser connections subscribe to
the same `SessionEventBus` topic and receive the same event IDs, so they never
duplicate an agent call. A bounded per-session event history is replayed when
a client reconnects; the LangGraph checkpoint preserves the conversation
thread and allows `Command(resume=...)` to continue after the interrupt.

The current bus is intentionally in-process for local development. Its
producer/consumer interface is isolated in `services/realtime/pubsub.py`, so a
Redis pub/sub adapter can replace it without changing the WebSocket contract.

## Interrupt behavior

Tokens already delivered to the browser remain visible as a partial assistant
message, but the current generation receives a cancellation signal and never
emits a completion event. The pending LangGraph checkpoint is then resumed
with the replacement question. This makes the interruption observable and
prevents the stale answer from being treated as complete.

## Run and verify

From the repository root:

```powershell
uv run --project services/api uvicorn services.api.main:app --reload
cd uis/backoffice
npm run dev
```

Open `/chat`, send a HealthCore question, then enter another question while
the first is typing. The button changes to **Interrupt & send**. The focused
contract tests are:

```powershell
uv run --project services/api pytest -q tests/realtime/test_chat_websocket.py
```
