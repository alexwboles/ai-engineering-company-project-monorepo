"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";
import { track } from "@/lib/telemetry";

type IncidentStatus = "open" | "in_progress" | "resolved" | "discarded";
type IncidentOrigin = "customer" | "branch" | "internal";
type IncidentCategory = "complaint" | "request" | "operational_failure";

type Incident = {
  id: number;
  title: string;
  description: string;
  category: IncidentCategory;
  status: IncidentStatus;
  origin: IncidentOrigin;
  branch: string;
  created_at: string;
  updated_at: string;
};

type SummaryResponse = {
  total_incidents: number;
  total_by_status: Record<string, number>;
  total_by_category: Record<string, number>;
  total_by_origin: Record<string, number>;
  total_by_branch: Record<string, number>;
};

const STATUS_OPTIONS: IncidentStatus[] = ["open", "in_progress", "resolved", "discarded"];
const ORIGIN_OPTIONS: IncidentOrigin[] = ["customer", "branch", "internal"];
const CATEGORY_OPTIONS: IncidentCategory[] = ["complaint", "request", "operational_failure"];
const BRANCH_OPTIONS = [
  { value: "central", label: "Central" },
  { value: "us-tx-001", label: "US - Austin Central" },
  { value: "us-fl-001", label: "US - Miami" },
  { value: "us-ga-001", label: "US - Atlanta" },
  { value: "uk-lon-001", label: "UK - London" },
  { value: "uk-man-001", label: "UK - Manchester" },
] as const;

const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["open", "in_progress", "discarded"],
  in_progress: ["in_progress", "resolved", "discarded"],
  resolved: ["resolved"],
  discarded: ["discarded"],
};

function toLabel(value: string) {
  return value.replaceAll("_", " ");
}

function toLocalDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

export default function IncidentsPage() {
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "complaint" as IncidentCategory,
    status: "open" as IncidentStatus,
    origin: "customer" as IncidentOrigin,
    branch: "central",
  });
  const [formError, setFormError] = useState("");
  const [formMessage, setFormMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [originFilter, setOriginFilter] = useState<string>("");
  const [branchFilter, setBranchFilter] = useState<string>("");

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [updatingStatusIds, setUpdatingStatusIds] = useState<Record<number, boolean>>({});
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});

  const branchHighlightClass =
    form.origin === "branch" ? "border-cyan-400 bg-cyan-50" : "border-slate-300 bg-white";

  const incidentQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter) {
      params.set("status", statusFilter);
    }
    if (originFilter) {
      params.set("origin", originFilter);
    }
    if (branchFilter) {
      params.set("branch", branchFilter);
    }
    return params.toString();
  }, [statusFilter, originFilter, branchFilter]);

  const loadIncidents = useCallback(async () => {
    setListLoading(true);
    setListError("");

    try {
      const path = incidentQuery ? `/api/incidents?${incidentQuery}` : "/api/incidents";
      const result = await apiRequest<Incident[]>(path);
      setIncidents(result);
    } catch {
      setListError("Unable to load incidents right now. Please try again.");
    } finally {
      setListLoading(false);
    }
  }, [incidentQuery]);

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError("");

    try {
      const result = await apiRequest<SummaryResponse>("/api/incidents/summary");
      setSummary(result);
    } catch {
      setSummaryError("Unable to load summary metrics right now.");
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadIncidents();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadIncidents]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSummary();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadSummary]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    setFormMessage("");
    setFieldErrors({});

    const nextFieldErrors: Record<string, string> = {};
    if (!form.title.trim()) {
      nextFieldErrors.title = "Title is required.";
    }
    if (!form.description.trim()) {
      nextFieldErrors.description = "Description is required.";
    }
    if (!form.category) {
      nextFieldErrors.category = "Category is required.";
    }
    if (!form.status) {
      nextFieldErrors.status = "Status is required.";
    }
    if (!form.origin) {
      nextFieldErrors.origin = "Origin is required.";
    }
    if (!form.branch) {
      nextFieldErrors.branch = "Branch is required.";
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setFormError("Please correct the highlighted fields and try again.");
      return;
    }

    setSubmitting(true);

    try {
      await apiRequest<Incident>("/api/incidents", {
        method: "POST",
        body: JSON.stringify({
          title: form.title.trim(),
          description: form.description.trim(),
          category: form.category,
          status: form.status,
          origin: form.origin,
          branch: form.branch,
        }),
      });

      setForm({
        title: "",
        description: "",
        category: "complaint",
        status: "open",
        origin: "customer",
        branch: "central",
      });
      setFormMessage("Incident registered successfully.");
      setFieldErrors({});
      await Promise.all([loadIncidents(), loadSummary()]);
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(error.fieldErrors);
      }
      setFormError("Could not save the incident. Please review your input and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onStatusChange(incident: Incident, nextStatus: IncidentStatus) {
    if (nextStatus === incident.status) {
      return;
    }

    const previousStatus = incident.status;
    setRowErrors((current) => ({ ...current, [incident.id]: "" }));
    setUpdatingStatusIds((current) => ({ ...current, [incident.id]: true }));
    setIncidents((current) =>
      current.map((item) => (item.id === incident.id ? { ...item, status: nextStatus } : item))
    );

    try {
      const updated = await apiRequest<Incident>(`/api/incidents/${incident.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });

      setIncidents((current) => current.map((item) => (item.id === incident.id ? updated : item)));
      track("incident_status_changed", {
        incidentId: updated.id,
        previousStatus,
        nextStatus: updated.status,
        origin: updated.origin,
        category: updated.category,
        actorRole: "backoffice_operator",
        timeInPreviousStatusHours: Number(
          ((new Date(updated.updated_at).getTime() - new Date(incident.updated_at).getTime()) / (1000 * 60 * 60)).toFixed(2)
        ),
      });
      await loadSummary();
    } catch {
      setIncidents((current) =>
        current.map((item) => (item.id === incident.id ? { ...item, status: previousStatus } : item))
      );
      setRowErrors((current) => ({
        ...current,
        [incident.id]: "Status update failed. The previous status was restored.",
      }));
    } finally {
      setUpdatingStatusIds((current) => ({ ...current, [incident.id]: false }));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-cyan-200 bg-cyan-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">HealthCore Incident Manager</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Incident control panel</h1>
        <p className="mt-2 text-sm text-slate-600">
          Register incidents, review lifecycle states, and track operational metrics from one place.
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Register incident</h2>
        <form className="mt-4 grid gap-4" onSubmit={onSubmit}>
          <label className="text-sm text-slate-700">
            Title
            <input
              type="text"
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              disabled={submitting}
              required
            />
            {fieldErrors.title ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.title}</span> : null}
          </label>

          <label className="text-sm text-slate-700">
            Description
            <textarea
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              className="mt-1 min-h-[110px] w-full rounded-lg border border-slate-300 px-3 py-2"
              disabled={submitting}
              required
            />
            {fieldErrors.description ? (
              <span className="mt-1 block text-xs text-rose-700">{fieldErrors.description}</span>
            ) : null}
          </label>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label className="text-sm text-slate-700">
              Category
              <select
                value={form.category}
                onChange={(event) => setForm((current) => ({ ...current, category: event.target.value as IncidentCategory }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                disabled={submitting}
                required
              >
                {CATEGORY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {toLabel(option)}
                  </option>
                ))}
              </select>
              {fieldErrors.category ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.category}</span> : null}
            </label>

            <label className="text-sm text-slate-700">
              Status
              <select
                value={form.status}
                onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as IncidentStatus }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                disabled={submitting}
                required
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {toLabel(option)}
                  </option>
                ))}
              </select>
              {fieldErrors.status ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.status}</span> : null}
            </label>

            <label className="text-sm text-slate-700">
              Origin
              <select
                value={form.origin}
                onChange={(event) => setForm((current) => ({ ...current, origin: event.target.value as IncidentOrigin }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                disabled={submitting}
                required
              >
                {ORIGIN_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {toLabel(option)}
                  </option>
                ))}
              </select>
              {fieldErrors.origin ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.origin}</span> : null}
            </label>

            <label className="text-sm text-slate-700">
              Branch
              <select
                value={form.branch}
                onChange={(event) => setForm((current) => ({ ...current, branch: event.target.value }))}
                className={`mt-1 w-full rounded-lg border px-3 py-2 ${branchHighlightClass}`}
                disabled={submitting}
                required
              >
                {BRANCH_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {fieldErrors.branch ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.branch}</span> : null}
            </label>
          </div>

          {formError ? <p className="text-sm text-rose-700">{formError}</p> : null}
          {formMessage ? <p className="text-sm text-emerald-700">{formMessage}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-fit rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60"
          >
            {submitting ? "Saving incident..." : "Create incident"}
          </button>
        </form>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <h2 className="mr-auto text-lg font-semibold text-slate-900">Incident list</h2>
          <label className="text-sm text-slate-700">
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-700">
            Origin
            <select
              value={originFilter}
              onChange={(event) => setOriginFilter(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All</option>
              {ORIGIN_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-700">
            Branch
            <select
              value={branchFilter}
              onChange={(event) => setBranchFilter(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All</option>
              {BRANCH_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => void loadIncidents()}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>

        {listLoading ? <p className="mt-4 text-sm text-slate-600">Loading incidents...</p> : null}

        {listError ? (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <p>{listError}</p>
            <button
              type="button"
              onClick={() => void loadIncidents()}
              className="mt-2 rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold hover:bg-rose-100"
            >
              Retry
            </button>
          </div>
        ) : null}

        {!listLoading && !listError && incidents.length === 0 ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            No incidents to display for the current filters.
          </p>
        ) : null}

        {!listLoading && !listError && incidents.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Title</th>
                  <th className="pb-2">Category</th>
                  <th className="pb-2">Origin</th>
                  <th className="pb-2">Branch</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {incidents.map((incident) => {
                  const allowedTransitions = STATUS_TRANSITIONS[incident.status] || [incident.status];
                  const rowDisabled = Boolean(updatingStatusIds[incident.id]);

                  return (
                    <tr key={incident.id}>
                      <td className="py-3">
                        <p className="font-medium text-slate-900">{incident.title}</p>
                        <p className="mt-1 text-xs text-slate-500">{incident.description}</p>
                        {rowErrors[incident.id] ? <p className="mt-1 text-xs text-rose-700">{rowErrors[incident.id]}</p> : null}
                      </td>
                      <td className="py-3">{toLabel(incident.category)}</td>
                      <td className="py-3">{toLabel(incident.origin)}</td>
                      <td className="py-3">{incident.branch}</td>
                      <td className="py-3">
                        <select
                          value={incident.status}
                          onChange={(event) =>
                            void onStatusChange(incident, event.target.value as IncidentStatus)
                          }
                          disabled={rowDisabled}
                          className="rounded-lg border border-slate-300 px-3 py-1"
                        >
                          {allowedTransitions.map((option) => (
                            <option key={option} value={option}>
                              {toLabel(option)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3">{toLocalDateTime(incident.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Summary metrics</h2>
          <button
            type="button"
            onClick={() => void loadSummary()}
            className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Refresh summary
          </button>
        </div>

        {summaryLoading ? <p className="mt-4 text-sm text-slate-600">Loading summary...</p> : null}

        {summaryError ? (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <p>{summaryError}</p>
            <button
              type="button"
              onClick={() => void loadSummary()}
              className="mt-2 rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold hover:bg-rose-100"
            >
              Retry
            </button>
          </div>
        ) : null}

        {!summaryLoading && !summaryError && summary ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <article className="rounded-lg border border-slate-200 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Total incidents</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{summary.total_incidents}</p>
            </article>

            <article className="rounded-lg border border-slate-200 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">By status</p>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {Object.entries(summary.total_by_status).map(([key, value]) => (
                  <li key={key}>
                    {toLabel(key)}: {value}
                  </li>
                ))}
              </ul>
            </article>

            <article className="rounded-lg border border-slate-200 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">By category</p>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {Object.entries(summary.total_by_category).map(([key, value]) => (
                  <li key={key}>
                    {toLabel(key)}: {value}
                  </li>
                ))}
              </ul>
            </article>

            <article className="rounded-lg border border-slate-200 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">By origin and branch</p>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {Object.entries(summary.total_by_origin).map(([key, value]) => (
                  <li key={`origin-${key}`}>
                    origin {toLabel(key)}: {value}
                  </li>
                ))}
                {Object.entries(summary.total_by_branch).map(([key, value]) => (
                  <li key={`branch-${key}`}>
                    branch {key}: {value}
                  </li>
                ))}
              </ul>
            </article>
          </div>
        ) : null}
      </section>
    </main>
  );
}
