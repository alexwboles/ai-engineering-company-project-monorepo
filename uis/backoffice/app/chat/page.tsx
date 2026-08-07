"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type ChatEvent = {
  eventId?: string;
  event_type?: string;
  properties?: Record<string, unknown>;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "complete" | "interrupted" | "failed";
};

const SESSION_KEY = "healthcore_support_chat_session_id";
const MAX_RECONNECT_DELAY_MS = 5_000;

function randomId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `chat-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function websocketUrl(sessionId: string): string {
  const explicit = process.env.NEXT_PUBLIC_AGENT_WS_URL;
  if (explicit) {
    return `${explicit.replace(/\/$/, "")}/${encodeURIComponent(sessionId)}`;
  }

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const socketBase = apiBase.replace(/^http/, "ws").replace(/\/$/, "");
  return `${socketBase}/ws/chat/${encodeURIComponent(sessionId)}`;
}

function textProperty(event: ChatEvent, key: string): string {
  const value = event.properties?.[key];
  return typeof value === "string" ? value : "";
}

export default function SupportChatPage() {
  const [sessionId] = useState(() => {
    if (typeof window === "undefined") return randomId();
    const existing = window.sessionStorage.getItem(SESSION_KEY);
    const value = existing ?? randomId();
    window.sessionStorage.setItem(SESSION_KEY, value);
    return value;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(true);
  const seenEventIds = useRef(new Set<string>());

  useEffect(() => {
    mounted.current = true;

    const connect = () => {
      if (!mounted.current) return;
      setConnection(reconnectAttempt.current === 0 ? "connecting" : "reconnecting");
      const socket = new WebSocket(websocketUrl(sessionId));
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectAttempt.current = 0;
        setConnection("connected");
        setError("");
      };

      socket.onmessage = (message) => {
        let event: ChatEvent;
        try {
          event = JSON.parse(message.data) as ChatEvent;
        } catch {
          setError("The chat received an invalid event. Please reconnect and try again.");
          return;
        }

        if (event.eventId && seenEventIds.current.has(event.eventId)) return;
        if (event.eventId) seenEventIds.current.add(event.eventId);

        const eventType = event.event_type;
        const messageId = textProperty(event, "messageId");
        if (eventType === "chat_generation_started") {
          setGenerating(true);
          setMessages((current) => [
            ...current,
            { id: messageId || randomId(), role: "assistant", content: "", status: "streaming" },
          ]);
        } else if (eventType === "chat_token_emitted") {
          const token = textProperty(event, "token");
          setMessages((current) => {
            const index = [...current].reverse().findIndex((item) => item.id === messageId);
            const target = index < 0 ? current.length - 1 : current.length - 1 - index;
            if (target < 0 || current[target]?.role !== "assistant") return current;
            return current.map((item, itemIndex) =>
              itemIndex === target ? { ...item, content: item.content + token } : item,
            );
          });
        } else if (eventType === "chat_generation_completed") {
          setGenerating(false);
          setMessages((current) => current.map((item) => (item.id === messageId ? { ...item, status: "complete" } : item)));
        } else if (eventType === "chat_generation_interrupted") {
          setGenerating(false);
          setMessages((current) => current.map((item) => (item.id === messageId ? { ...item, status: "interrupted" } : item)));
        } else if (eventType === "chat_generation_failed") {
          setGenerating(false);
          setError("The support assistant could not finish this response. Please try again.");
          setMessages((current) => current.map((item) => (item.id === messageId ? { ...item, status: "failed" } : item)));
        } else if (eventType === "chat_protocol_error") {
          setError(textProperty(event, "message") || "The chat message could not be processed.");
        }
      };

      socket.onclose = () => {
        if (!mounted.current) return;
        setConnection("disconnected");
        const delay = Math.min(250 * 2 ** reconnectAttempt.current, MAX_RECONNECT_DELAY_MS);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      socket.onerror = () => setError("The chat connection is unavailable. Retrying automatically.");
    };

    connect();
    return () => {
      mounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
    };
  }, [sessionId]);

  function send(eventType: "chat_message" | "chat_interrupt", message: string): void {
    const socket = socketRef.current;
    const trimmed = message.trim();
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("The chat is reconnecting. Please try again when it is connected.");
      return;
    }
    if (!trimmed) {
      setError("Enter a message for the HealthCore support assistant.");
      return;
    }

    const messageId = randomId();
    setMessages((current) => [...current, { id: messageId, role: "user", content: trimmed, status: "complete" }]);
    socket.send(JSON.stringify({ event_type: eventType, properties: { message: trimmed, messageId } }));
    setDraft("");
    setError("");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    send(generating ? "chat_interrupt" : "chat_message", draft);
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-teal-200 bg-teal-50 p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">HealthCore Digital</p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Live support assistant</h1>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600">{connection}</span>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          Responses stream as they are generated. While a response is typing, send a new message to interrupt it and
          continue the same conversation thread.
        </p>
      </header>

      <section aria-live="polite" className="min-h-80 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {messages.length === 0 ? <p className="text-sm text-slate-500">Ask about HealthCore policies or live operations.</p> : null}
        {messages.map((message) => (
          <article key={message.id} className={`rounded-xl p-4 ${message.role === "user" ? "ml-8 bg-slate-100" : "mr-8 bg-sky-50"}`}>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{message.role === "user" ? "You" : "HealthCore assistant"}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-800">
              {message.content || (message.status === "streaming" ? "Typing..." : "")}
            </p>
            {message.status === "interrupted" ? <p className="mt-2 text-xs text-amber-700">Response interrupted and conversation resumed.</p> : null}
          </article>
        ))}
      </section>

      {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p> : null}

      <form className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={handleSubmit}>
        <label className="text-sm font-semibold text-slate-900" htmlFor="support-message">Message</label>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <input
            className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-teal-500 focus:ring-2"
            id="support-message"
            onChange={(event) => setDraft(event.target.value)}
            placeholder={generating ? "Type a replacement message to interrupt..." : "Ask the support assistant..."}
            value={draft}
          />
          <button className="rounded-full bg-teal-700 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60" disabled={connection !== "connected"} type="submit">
            {generating ? "Interrupt & send" : "Send"}
          </button>
        </div>
      </form>
    </main>
  );
}
