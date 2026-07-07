"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { StagePill } from "@/components/stage-pill";
import { StatusPill } from "@/components/status-pill";
import { getRecords } from "@/services/records";
import { STAGE_OPTIONS, STATUS_OPTIONS, type CandidateRecord } from "@/types/talent";

function normalizeParam(value: string | null) {
  return value?.trim() || "";
}

function toReadableLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function CandidateListPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [records, setRecords] = useState<CandidateRecord[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const status = normalizeParam(searchParams.get("status"));
  const stage = normalizeParam(searchParams.get("stage"));
  const search = normalizeParam(searchParams.get("search"));

  useEffect(() => {
    async function loadRecords() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getRecords({
          status: status || undefined,
          stage: stage || undefined,
          search: search || undefined,
          limit: 100,
        });

        setRecords(response.data);
        setTotal(response.total);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to fetch candidates.");
      } finally {
        setIsLoading(false);
      }
    }

    void loadRecords();
  }, [status, stage, search]);

  const emptyStateMessage = useMemo(() => {
    if (status || stage || search) {
      return "No candidates match the selected People & Workforce filters.";
    }

    return "No candidate records are available yet.";
  }, [status, stage, search]);

  const updateQueryParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());

    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }

    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  };

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-7 px-4 py-10 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">HealthCore People and Workforce</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Candidate Pipeline Tracker</h1>
          <p className="mt-1 text-sm leading-6 text-slate-500">Review active applicants, update pipeline decisions, and keep internal hiring notes in one workspace.</p>
        </div>
        <Link href="/candidates/new" className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800">
          Register Candidate
        </Link>
      </header>

      <section className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Filter by status
          <select
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={status}
            onChange={(event) => updateQueryParam("status", event.target.value)}
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {toReadableLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Filter by stage
          <select
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={stage}
            onChange={(event) => updateQueryParam("stage", event.target.value)}
          >
            <option value="">All stages</option>
            {STAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {toReadableLabel(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Search by name or email
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="e.g. alex.candidate@healthcore.com"
            value={search}
            onChange={(event) => updateQueryParam("search", event.target.value)}
          />
        </label>
      </section>

      {isLoading ? <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Loading candidate pipeline...</p> : null}
      {error ? <p className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

      {!isLoading && !error ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3 text-sm text-slate-600">Showing {records.length} of {total} candidate records</div>

          {records.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-slate-500">{emptyStateMessage}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Candidate</th>
                    <th className="px-4 py-3">Position</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Stage</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm leading-6">
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-slate-900">{record.full_name}</p>
                        <p className="text-slate-500">{record.email}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{record.position}</td>
                      <td className="px-4 py-3"><StatusPill status={record.status} /></td>
                      <td className="px-4 py-3"><StagePill stage={record.stage} /></td>
                      <td className="px-4 py-3">
                        <Link href={`/candidates/${record.id}`} className="font-semibold text-cyan-700 hover:text-cyan-800">
                          Open candidate detail
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </main>
  );
}
