"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";

type TicketStatus = "analyzing" | "waiting_for_approval" | "done" | "discarded" | "failed" | "drafting" | "under_evaluation" | "needs_human_review" | "ready_for_approval";

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
};

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
};

export default function RfpIntakePage() {
  const [tickets, setTickets] = useState<RfpTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [generating, setGenerating] = useState<string | null>(null);

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
    if (!tickets.some((ticket) => ["analyzing", "waiting_for_approval", "drafting", "under_evaluation"].includes(ticket.status))) {
      return;
    }
    const timer = window.setInterval(() => void loadTickets(), 2000);
    return () => window.clearInterval(timer);
  }, [loadTickets, tickets]);

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
            <p className="mt-1 text-sm text-slate-600">Statuses refresh while analysis is in progress.</p>
          </div>
          <button type="button" onClick={() => void loadTickets()} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Refresh</button>
        </div>

        {loading ? <p className="mt-4 rounded-xl bg-white p-6 text-sm text-slate-600">Loading RFP tickets...</p> : null}
        {!loading && tickets.length === 0 ? <p className="mt-4 rounded-xl bg-white p-6 text-sm text-slate-600">No RFP tickets yet.</p> : null}
        <div className="mt-4 space-y-5">
          {tickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} onGenerate={generateResponse} generating={generating === ticket.id} />)}
        </div>
      </section>
    </main>
  );
}

function TicketCard({ ticket, onGenerate, generating }: { ticket: RfpTicket; onGenerate: (ticketId: string) => void; generating: boolean }) {
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
      {ticket.response ? <ResponseHandoff response={ticket.response} /> : null}
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

function ResponseHandoff({ response }: { response: NonNullable<RfpTicket["response"]> }) {
  return <section className="mt-6 border-t border-slate-200 pt-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h4 className="text-lg font-semibold text-slate-950">Pricing proposal handoff</h4>
        <p className="mt-1 text-sm text-slate-600">Each department draft is shown with its readability, relevance, and HealthCore guideline results.</p>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${response.ready_for_part_3 ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>{response.ready_for_part_3 ? "Ready for Part 3" : "Human review needed"}</span>
    </div>
    <div className="mt-4 space-y-4">
      {response.department_tickets.map((department) => <div key={department.department} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h5 className="font-semibold text-slate-950">{department.department}</h5>
          <span className={`text-xs font-semibold ${department.evaluation.passed ? "text-emerald-700" : "text-rose-700"}`}>{department.evaluation.passed ? "All evaluators passed" : "Needs human review"} | {department.iterations} iteration(s)</span>
        </div>
        <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-white p-4 text-sm leading-6 text-slate-700">{department.assigned_content}</pre>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {Object.entries(department.evaluation.results).map(([name, result]) => <div key={name} className={`rounded-lg px-3 py-2 text-xs ${result.passed ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-800"}`}><p className="font-semibold">{name}: {result.passed ? "pass" : "fail"}</p>{result.failed_rules?.length ? <p className="mt-1">{result.failed_rules.join(", ")}</p> : null}{result.feedback ? <p className="mt-1">{result.feedback}</p> : null}</div>)}
        </div>
      </div>)}
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
