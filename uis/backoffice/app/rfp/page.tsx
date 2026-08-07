"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";
import { getStoredToken } from "@/lib/auth-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000";

type TicketStatus = "analyzing" | "waiting_for_approval" | "done" | "discarded" | "failed" | "drafting" | "under_evaluation" | "needs_human_review" | "ready_for_approval" | "awaiting_approval" | "partially_approved" | "needs_revision" | "arbitrating" | "producing";

type ApprovalState = {
  thread_id: string;
  ticket_id: string;
  status: string;
  branches: Record<string, {
    department: string;
    approver_role: string;
    status: string;
    draft: string;
    evaluation: { passed?: boolean; iterations?: number; results?: Record<string, { passed: boolean; feedback?: string | null; failed_rules?: string[] | null }> };
    iterations: number;
    revision_attempts: number;
    approval?: { actor?: string; comment?: string | null; at?: string } | null;
    feedback?: string | null;
  }>;
  arbitration?: { status?: string; conflicts?: Array<{ conflict_id?: string; departments?: string[]; resolution?: string }> } | null;
  final_document?: { filename?: string; generated_at?: string } | null;
  trace?: Array<{ node: string; agent: string; ts: string }>;
};

type RfpTicket = {
  id: string;
  filename: string;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
  status_history: Array<{ status: string; at: string }>;
  metadata?: {
    client?: string | null;
    submission_deadline?: string | null;
    departments_mentioned?: string[];
    word_count?: number;
    page_count?: number;
  } | null;
  readability?: { complexity?: string; gunning_fog_grade?: number; flesch_kincaid_grade?: number } | null;
  classifier?: { is_rfp?: boolean; reason?: string; confidence?: number } | null;
  result?: {
    summary?: string;
    readability_estimate?: string;
    by_department?: Array<{
      department: string;
      needs: string[];
      key_aspects: string[];
      contact: string;
    }>;
  } | null;
  error?: string | null;
  response?: {
    approval_status: string;
    ready_for_part_3: boolean;
    department_tickets: Array<{
      department: string;
      assigned_content: string;
      iterations: number;
      needs_human_review: boolean;
      evaluation: {
        passed: boolean;
        iterations: number;
        results: Record<string, { passed: boolean; feedback?: string | null; failed_rules?: string[] | null }>;
      };
    }>;
  } | null;
  approval?: ApprovalState | null;
  final_document?: { filename?: string; generated_at?: string } | null;
};

type SseNotification = {
  id: string;
  event: string;
  data: Record<string, unknown>;
};

function parseSseBlock(block: string): SseNotification | null {
  let id = "";
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("id:")) id = line.slice(3).trim();
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    const data: unknown = JSON.parse(dataLines.join("\n"));
    return data && typeof data === "object" ? { id, event, data: data as Record<string, unknown> } : null;
  } catch {
    return null;
  }
}

const STATUS_STYLES: Record<TicketStatus, string> = {
  analyzing: "bg-blue-100 text-blue-800",
  waiting_for_approval: "bg-amber-100 text-amber-800",
  done: "bg-emerald-100 text-emerald-800",
  discarded: "bg-slate-200 text-slate-700",
  failed: "bg-rose-100 text-rose-800",
  drafting: "bg-indigo-100 text-indigo-800",
  under_evaluation: "bg-orange-100 text-orange-800",
  needs_human_review: "bg-rose-100 text-rose-800",
  ready_for_approval: "bg-emerald-100 text-emerald-800",
  awaiting_approval: "bg-amber-100 text-amber-800",
  partially_approved: "bg-cyan-100 text-cyan-800",
  needs_revision: "bg-rose-100 text-rose-800",
  arbitrating: "bg-orange-100 text-orange-800",
  producing: "bg-indigo-100 text-indigo-800",
};

export default function RfpIntakePage() {
  const [tickets, setTickets] = useState<RfpTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [generating, setGenerating] = useState<string | null>(null);
  const [startingApproval, setStartingApproval] = useState<string | null>(null);
  const [approvalAction, setApprovalAction] = useState<string | null>(null);
  const [approvalComments, setApprovalComments] = useState<Record<string, string>>({});
  const [finalDocument, setFinalDocument] = useState<{ ticketId: string; filename: string; content: string } | null>(null);
  const [streamStatus, setStreamStatus] = useState<"connecting" | "connected" | "reconnecting">("connecting");
  const [realtimeNotice, setRealtimeNotice] = useState("");
  const seenEventIds = useRef(new Set<string>());
  const lastEventId = useRef("");

  const loadTickets = useCallback(async () => {
    try {
      setError("");
      setTickets(await apiRequest<RfpTicket[]>("/rfp/tickets"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load RFP tickets.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadTickets(), 0);
    return () => window.clearTimeout(timer);
  }, [loadTickets]);

  useEffect(() => {
    let stopped = false;
    let retryAttempt = 0;
    let retryTimer: number | null = null;
    let controller: AbortController | null = null;

    async function consumeNotification(notification: SseNotification) {
      if (notification.id && seenEventIds.current.has(notification.id)) return;
      if (notification.id) {
        seenEventIds.current.add(notification.id);
        lastEventId.current = notification.id;
      }

      const ticketId = typeof notification.data.ticket_id === "string" ? notification.data.ticket_id : "";
      if (!ticketId || !["rfp_ticket_created", "rfp_ticket_updated"].includes(notification.event)) return;

      if (notification.event === "rfp_ticket_created") {
        const status = typeof notification.data.status === "string" ? notification.data.status : "analyzing";
        setRealtimeNotice(`New RFP ticket ${ticketId.slice(0, 12)} needs processing (${status.replaceAll("_", " ")}).`);
      }

      try {
        const ticket = await apiRequest<RfpTicket>(`/rfp/tickets/${ticketId}`);
        setTickets((current) => {
          const exists = current.some((item) => item.id === ticket.id);
          return exists ? current.map((item) => item.id === ticket.id ? ticket : item) : [ticket, ...current];
        });
      } catch {
        // The named notification remains visible even if the detail request is transiently unavailable.
      }
    }

    async function connect() {
      if (stopped) return;
      const token = getStoredToken();
      if (!token) return;
      setStreamStatus(retryAttempt === 0 ? "connecting" : "reconnecting");
      controller = new AbortController();
      try {
        const response = await fetch(`${API_BASE_URL}/rfp/tickets/stream`, {
          headers: { Accept: "text/event-stream", Authorization: `Bearer ${token}`, ...(lastEventId.current ? { "Last-Event-ID": lastEventId.current } : {}) },
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok || !response.body) throw new Error("SSE stream unavailable");
        retryAttempt = 0;
        setStreamStatus("connected");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!stopped) {
          const { done, value } = await reader.read();
          if (done) throw new Error("SSE stream closed");
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() ?? "";
          for (const block of blocks) {
            const notification = parseSseBlock(block);
            if (notification) await consumeNotification(notification);
          }
        }
      } catch {
        if (stopped) return;
        setStreamStatus("reconnecting");
        const delay = Math.min(1000 * 2 ** Math.min(retryAttempt, 5), 30000);
        retryAttempt += 1;
        retryTimer = window.setTimeout(() => void connect(), delay);
      }
    }

    void connect();
    return () => {
      stopped = true;
      controller?.abort();
      if (retryTimer !== null) window.clearTimeout(retryTimer);
    };
  }, []);

  async function uploadRfp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = (form.elements.namedItem("file") as HTMLInputElement).files?.[0];
    if (!file) {
      setError("Choose a PDF RFP before uploading.");
      return;
    }
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("RFP intake accepts PDF files only.");
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");
    const payload = new FormData();
    payload.append("file", file);
    try {
      await apiRequest<RfpTicket>("/rfp/tickets", { method: "POST", body: payload });
      form.reset();
      setMessage("RFP ticket created. Analysis is running and the status will refresh automatically.");
      await loadTickets();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to upload this RFP.");
    } finally {
      setUploading(false);
    }
  }

  async function generateResponse(ticketId: string) {
    setGenerating(ticketId);
    setError("");
    try {
      await apiRequest<RfpTicket>(`/rfp/tickets/${ticketId}/generate`, { method: "POST" });
      setMessage("Department drafts are being generated and evaluated. This ticket will refresh automatically.");
      await loadTickets();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to start response generation.");
    } finally {
      setGenerating(null);
    }
  }

  async function startApprovals(ticketId: string) {
    setStartingApproval(ticketId);
    setError("");
    try {
      await apiRequest<ApprovalState>(`/rfp/tickets/${ticketId}/approvals/start`, { method: "POST" });
      setMessage("Department approval gates are open. Each lead can decide independently.");
      await loadTickets();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to start department approvals.");
    } finally {
      setStartingApproval(null);
    }
  }

  async function submitApproval(ticketId: string, department: string, decision: "approve" | "reject" | "request_changes") {
    const comment = approvalComments[`${ticketId}:${department}`]?.trim() || undefined;
    if (decision !== "approve" && !comment) {
      setError("Add a comment explaining the requested change before rejecting a section.");
      return;
    }
    setApprovalAction(`${ticketId}:${department}`);
    setError("");
    try {
      await apiRequest<ApprovalState>(`/rfp/tickets/${ticketId}/approvals/${encodeURIComponent(department)}`, {
        method: "POST",
        body: JSON.stringify({ decision, comment }),
      });
      setMessage(`${department} approval updated to ${decision.replaceAll("_", " ")}.`);
      await loadTickets();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to record this approval decision.");
    } finally {
      setApprovalAction(null);
    }
  }

  async function loadFinalDocument(ticketId: string) {
    try {
      const document = await apiRequest<{ filename: string; content: string }>(`/rfp/tickets/${ticketId}/final-document`);
      setFinalDocument({ ticketId, ...document });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load the final proposal.");
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
      <header className="rounded-3xl border border-violet-200 bg-white/90 p-6 shadow-sm sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-700">HealthCore Digital | Sales enablement</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">RFP Intake</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
          Upload a proposal request once. HealthCore Digital converts it, checks that it is a real RFP, and routes the relevant work to the right department leads.
        </p>
      </header>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Create an RFP ticket</h2>
        <form className="mt-4 flex flex-wrap items-end gap-4" onSubmit={uploadRfp}>
          <label className="min-w-0 flex-1 text-sm font-medium text-slate-700">
            PDF document
            <input name="file" type="file" accept="application/pdf,.pdf" className="mt-2 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
          </label>
          <button type="submit" disabled={uploading} className="rounded-lg bg-violet-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60">
            {uploading ? "Creating ticket..." : "Upload RFP"}
          </button>
        </form>
        {message ? <p className="mt-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">{message}</p> : null}
        {error ? <p className="mt-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">{error}</p> : null}
      </section>

      <section className="mt-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-950">Tickets</h2>
            <p className="mt-1 text-sm text-slate-600">Live ticket notifications: <span className={streamStatus === "connected" ? "font-semibold text-emerald-700" : "font-semibold text-amber-700"}>{streamStatus}</span></p>
          </div>
          <button type="button" onClick={() => void loadTickets()} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Refresh</button>
        </div>

        {realtimeNotice ? <p className="mt-4 rounded-xl border border-cyan-300 bg-cyan-50 px-4 py-3 text-sm font-semibold text-cyan-950" role="status">{realtimeNotice}</p> : null}

        {loading ? <p className="mt-4 rounded-xl bg-white p-6 text-sm text-slate-600">Loading RFP tickets...</p> : null}
        {!loading && tickets.length === 0 ? <p className="mt-4 rounded-xl bg-white p-6 text-sm text-slate-600">No RFP tickets yet.</p> : null}
        <div className="mt-4 space-y-5">
          {tickets.map((ticket) => <TicketCard
            key={ticket.id}
            ticket={ticket}
            onGenerate={generateResponse}
            generating={generating === ticket.id}
            onStartApprovals={startApprovals}
            startingApproval={startingApproval === ticket.id}
            onSubmitApproval={submitApproval}
            approvalAction={approvalAction}
            approvalComments={approvalComments}
            setApprovalComment={(key, value) => setApprovalComments((current) => ({ ...current, [key]: value }))}
            onLoadFinalDocument={loadFinalDocument}
          />)}
        </div>
      </section>
      {finalDocument ? <section className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-lg font-semibold text-emerald-950">Final proposal: {finalDocument.filename}</h2><p className="mt-1 text-sm text-emerald-800">Generated after every HealthCore department approved its section.</p></div>
          <button type="button" onClick={() => setFinalDocument(null)} className="rounded-lg border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-800">Close</button>
        </div>
        <pre className="mt-4 max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-xl bg-white p-4 text-sm leading-6 text-slate-700">{finalDocument.content}</pre>
      </section> : null}
    </main>
  );
}

function TicketCard({ ticket, onGenerate, generating, onStartApprovals, startingApproval, onSubmitApproval, approvalAction, approvalComments, setApprovalComment, onLoadFinalDocument }: {
  ticket: RfpTicket;
  onGenerate: (ticketId: string) => void;
  generating: boolean;
  onStartApprovals: (ticketId: string) => void;
  startingApproval: boolean;
  onSubmitApproval: (ticketId: string, department: string, decision: "approve" | "reject" | "request_changes") => void;
  approvalAction: string | null;
  approvalComments: Record<string, string>;
  setApprovalComment: (key: string, value: string) => void;
  onLoadFinalDocument: (ticketId: string) => void;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-950">{ticket.filename}</h3>
          <p className="mt-1 text-xs text-slate-500">Ticket {ticket.id.slice(0, 12)} | Created {formatDate(ticket.created_at)}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${STATUS_STYLES[ticket.status]}`}>{ticket.status.replaceAll("_", " ")}</span>
      </div>

      {ticket.metadata ? <div className="mt-5 grid gap-3 text-sm text-slate-700 sm:grid-cols-4">
        <Metric label="Issuer" value={ticket.metadata.client ?? "Not identified"} />
        <Metric label="Due" value={ticket.metadata.submission_deadline ?? "Not identified"} />
        <Metric label="Words" value={String(ticket.metadata.word_count ?? 0)} />
        <Metric label="Complexity" value={ticket.readability?.complexity ?? "Calculating"} />
      </div> : null}

      {ticket.status === "discarded" ? <p className="mt-5 rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Not routed: {ticket.error ?? ticket.classifier?.reason ?? "The document did not meet the RFP criteria."}</p> : null}
      {ticket.status === "failed" ? <p className="mt-5 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800">Analysis failed: {ticket.error ?? "Please upload the document again."}</p> : null}
      {ticket.status === "done" && !ticket.response ? <button type="button" onClick={() => onGenerate(ticket.id)} disabled={generating} className="mt-5 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60">{generating ? "Starting response generation..." : "Generate pricing proposal draft"}</button> : null}
      {ticket.response ? <ResponseHandoff
        ticket={ticket}
        response={ticket.response}
        onStartApprovals={onStartApprovals}
        startingApproval={startingApproval}
        onSubmitApproval={onSubmitApproval}
        approvalAction={approvalAction}
        approvalComments={approvalComments}
        setApprovalComment={setApprovalComment}
        onLoadFinalDocument={onLoadFinalDocument}
      /> : null}
      {ticket.result ? <div className="mt-5">
        <p className="text-sm font-semibold text-slate-950">Sales routing summary</p>
        <p className="mt-1 text-sm text-slate-700">{ticket.result.summary}</p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {(ticket.result.by_department ?? []).map((row) => <div key={row.department} className="rounded-xl border border-violet-100 bg-violet-50/50 p-4">
            <h4 className="font-semibold text-violet-950">{row.department}</h4>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-violet-700">Ask: {row.contact}</p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">{row.needs.map((need) => <li key={need}>{need}</li>)}</ul>
          </div>)}
        </div>
      </div> : null}
    </article>
  );
}

function ResponseHandoff({ ticket, response, onStartApprovals, startingApproval, onSubmitApproval, approvalAction, approvalComments, setApprovalComment, onLoadFinalDocument }: {
  ticket: RfpTicket;
  response: NonNullable<RfpTicket["response"]>;
  onStartApprovals: (ticketId: string) => void;
  startingApproval: boolean;
  onSubmitApproval: (ticketId: string, department: string, decision: "approve" | "reject" | "request_changes") => void;
  approvalAction: string | null;
  approvalComments: Record<string, string>;
  setApprovalComment: (key: string, value: string) => void;
  onLoadFinalDocument: (ticketId: string) => void;
}) {
  return <section className="mt-6 border-t border-slate-200 pt-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h4 className="text-lg font-semibold text-slate-950">Pricing proposal handoff</h4>
        <p className="mt-1 text-sm text-slate-600">Each department draft is shown with its readability, relevance, and HealthCore guideline results.</p>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${response.ready_for_part_3 ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>{response.ready_for_part_3 ? "Ready for human approval" : "Human review needed"}</span>
    </div>
    {!ticket.approval && response.ready_for_part_3 ? <button type="button" onClick={() => onStartApprovals(ticket.id)} disabled={startingApproval} className="mt-4 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-60">{startingApproval ? "Opening approval gates..." : "Start human approvals"}</button> : null}
    {ticket.final_document ? <button type="button" onClick={() => onLoadFinalDocument(ticket.id)} className="mt-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800">View final approved proposal</button> : null}
    <div className="mt-4 space-y-4">
      {response.department_tickets.map((department) => {
        const branch = ticket.approval?.branches[department.department];
        const actionKey = `${ticket.id}:${department.department}`;
        return <div key={department.department} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h5 className="font-semibold text-slate-950">{department.department}</h5>
            <span className={`text-xs font-semibold ${branch?.status === "approved" || (!branch && department.evaluation.passed) ? "text-emerald-700" : "text-rose-700"}`}>{branch?.status?.replaceAll("_", " ") ?? (department.evaluation.passed ? "All evaluators passed" : "Needs human review")} | {department.iterations} iteration(s)</span>
          </div>
          <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-white p-4 text-sm leading-6 text-slate-700">{department.assigned_content}</pre>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {Object.entries(department.evaluation.results).map(([name, result]) => <div key={name} className={`rounded-lg px-3 py-2 text-xs ${result.passed ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-800"}`}><p className="font-semibold">{name}: {result.passed ? "pass" : "fail"}</p>{result.failed_rules?.length ? <p className="mt-1">{result.failed_rules.join(", ")}</p> : null}{result.feedback ? <p className="mt-1">{result.feedback}</p> : null}</div>)}
          </div>
          {branch?.status === "awaiting_approval" || branch?.status === "needs_human_review" || branch?.status === "needs_revision" ? <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-950">Human sign-off: {branch.approver_role}</p>
            <p className="mt-1 text-xs text-amber-900">Review the draft and evaluation snapshot before deciding. This gate pauses only this department.</p>
            <textarea value={approvalComments[actionKey] ?? ""} onChange={(event) => setApprovalComment(actionKey, event.target.value)} placeholder="Optional approval note, or required reason for changes" className="mt-3 min-h-20 w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm text-slate-700" />
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => onSubmitApproval(ticket.id, department.department, "approve")} disabled={approvalAction === actionKey} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-60">Approve section</button>
              <button type="button" onClick={() => onSubmitApproval(ticket.id, department.department, "request_changes")} disabled={approvalAction === actionKey} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-60">Request changes</button>
              <button type="button" onClick={() => onSubmitApproval(ticket.id, department.department, "reject")} disabled={approvalAction === actionKey} className="rounded-lg bg-rose-700 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-60">Reject section</button>
            </div>
          </div> : null}
        </div>;
      })}
    </div>
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-slate-50 px-3 py-2"><p className="text-xs uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 font-medium text-slate-900">{value}</p></div>;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
