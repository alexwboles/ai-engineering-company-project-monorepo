"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api-client";

type ReportRow = Record<string, string | number>;

type TelemetryReport = {
  period: { from: string; to: string };
  metrics: {
    events_per_day: ReportRow[];
    event_volume_by_type: ReportRow[];
    error_rate_by_type: ReportRow[];
    latency_by_route: ReportRow[];
    auth_failure_rate: ReportRow[];
  };
};

export default function TelemetryReportPage() {
  const [report, setReport] = useState<TelemetryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      void apiRequest<TelemetryReport>("/telemetry/report")
        .then((nextReport) => {
          if (active) {
            setReport(nextReport);
          }
        })
        .catch((requestError) => {
          if (active) {
            setError(requestError instanceof ApiError ? requestError.message : "Unable to load telemetry report.");
          }
        })
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
    }, 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [reloadToken]);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">Engineering telemetry</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Technical health report</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          Operational volume, error, latency, and authentication signals from the bounded UTC report window.
        </p>
        {report ? (
          <p className="mt-4 text-xs font-medium text-slate-500">
            Window: {formatDate(report.period.from)} to {formatDate(report.period.to)} (UTC)
          </p>
        ) : null}
      </header>

      {loading ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600" aria-live="polite">
          Loading technical telemetry...
        </section>
      ) : error ? (
        <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800" role="alert">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => setReloadToken((value) => value + 1)}
            className="mt-4 rounded-lg bg-rose-700 px-4 py-2 font-semibold text-white hover:bg-rose-800"
          >
            Retry report
          </button>
        </section>
      ) : report ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <MetricTable title="Events per day" rows={report.metrics.events_per_day} columns={["date", "event_count"]} />
          <MetricTable
            title="Event volume by type"
            rows={report.metrics.event_volume_by_type}
            columns={["date", "event_type", "event_count"]}
          />
          <MetricTable
            title="Error rate by type"
            rows={report.metrics.error_rate_by_type}
            columns={["date", "event_type", "error_count", "total_events", "error_rate_percent"]}
          />
          <MetricTable
            title="Latency by route"
            rows={report.metrics.latency_by_route}
            columns={["date", "route", "request_count", "average_duration_ms", "maximum_duration_ms"]}
          />
          <MetricTable
            title="Authentication failure rate"
            rows={report.metrics.auth_failure_rate}
            columns={["date", "total_login_attempts", "failed_login_attempts", "failure_rate_percent"]}
          />
        </div>
      ) : null}

      <Link href="/" className="text-sm font-semibold text-teal-700 hover:text-teal-800">
        Back to operations
      </Link>
    </main>
  );
}

function MetricTable({ title, rows, columns }: { title: string; rows: ReportRow[]; columns: string[] }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {columns.map((column) => (
                <th key={column} className="whitespace-nowrap px-5 py-3 font-semibold">
                  {column.replaceAll("_", " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {rows.length > 0 ? (
              rows.map((row, index) => (
                <tr key={`${title}-${index}`}>
                  {columns.map((column) => (
                    <td key={column} className="whitespace-nowrap px-5 py-3">
                      {String(row[column] ?? "-")}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-5 py-6 text-slate-500">
                  No events in this window.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value: string): string {
  return value.replace("T", " ").replace("Z", " UTC");
}
