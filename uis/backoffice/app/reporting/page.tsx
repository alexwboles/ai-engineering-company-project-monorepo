"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";

type ClinicPerformanceRow = {
  clinic_id: string;
  country: "US" | "UK";
  total_supply_cost: number;
  supply_consumption_count: number;
  critical_stockout_count: number;
  expiry_risk_count: number;
  currency: "USD" | "GBP";
};

type MonthlySupplyReport = {
  month_start: string | null;
  clinics: ClinicPerformanceRow[];
};

export default function ReportingDashboardPage() {
  const [report, setReport] = useState<MonthlySupplyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");

      void apiRequest<MonthlySupplyReport>("/reporting/monthly-clinic-supply-performance")
        .then((nextReport) => {
          if (active) {
            setReport(nextReport);
          }
        })
        .catch((requestError) => {
          if (active) {
            setError(
              requestError instanceof ApiError
                ? requestError.message
                : "Unable to load the monthly supply performance report."
            );
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
      <header className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-teal-100 bg-teal-50 px-6 py-5 sm:px-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-800">
            HealthCore Digital | Monthly board pack
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Monthly Clinic Supply Performance Report
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
            A clear view of supply cost, consumption, stockout risk, and expiry risk across HealthCore clinics.
            Prepared for Dr. Okonkwo and Claire Whitfield.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 sm:px-8">
          <p className="text-sm font-medium text-slate-600">
            Reporting period: {report?.month_start ? formatMonth(report.month_start) : "No completed month available"}
          </p>
          <p className="text-xs text-slate-500">Amounts remain in each clinic&apos;s local reporting currency.</p>
        </div>
      </header>

      {loading ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600" aria-live="polite">
          Loading the monthly supply performance report...
        </section>
      ) : error ? (
        <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-900" role="alert">
          <p className="font-semibold">The report could not be loaded.</p>
          <p className="mt-2">{error}</p>
          <button
            type="button"
            onClick={() => setReloadToken((value) => value + 1)}
            className="mt-4 rounded-lg bg-rose-700 px-4 py-2 font-semibold text-white hover:bg-rose-800"
          >
            Retry report
          </button>
        </section>
      ) : report ? (
        report.clinics.length > 0 ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <KpiPanel
              title="Supply Cost per Clinic"
              description="Purchasing cost recorded for each clinic during the reporting month."
              rows={report.clinics}
              value={(row) => formatCurrency(row.total_supply_cost, row.currency)}
            />
            <KpiPanel
              title="Supply Consumption Volume"
              description="Outbound supply-consumption activity recorded by clinic."
              rows={report.clinics}
              value={(row) => `${row.supply_consumption_count} events`}
            />
            <KpiPanel
              title="Critical Stockout Frequency"
              description="Times a clinic was below its minimum supply threshold."
              rows={report.clinics}
              value={(row) => `${row.critical_stockout_count} alerts`}
              accent="amber"
            />
            <KpiPanel
              title="Expiry Risk Count"
              description="Supply batches flagged as approaching expiry."
              rows={report.clinics}
              value={(row) => `${row.expiry_risk_count} flags`}
              accent="rose"
            />
          </div>
        ) : (
          <section className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600">
            No clinic performance rows have been published for this reporting period yet.
          </section>
        )
      ) : null}

      <div className="flex flex-wrap gap-4 text-sm font-semibold">
        <Link href="/" className="text-teal-700 hover:text-teal-800">
          Back to operations
        </Link>
        <Link href="/telemetry" className="text-slate-700 hover:text-slate-900">
          View technical telemetry
        </Link>
      </div>
    </main>
  );
}

function KpiPanel({
  title,
  description,
  rows,
  value,
  accent = "teal",
}: {
  title: string;
  description: string;
  rows: ClinicPerformanceRow[];
  value: (row: ClinicPerformanceRow) => string;
  accent?: "teal" | "amber" | "rose";
}) {
  const accentClasses = {
    teal: "bg-teal-50 text-teal-800",
    amber: "bg-amber-50 text-amber-800",
    rose: "bg-rose-50 text-rose-800",
  } as const;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`border-b border-slate-100 px-5 py-4 ${accentClasses[accent]}`}>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-xs leading-5 opacity-80">{description}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3 font-semibold">Clinic</th>
              <th className="px-5 py-3 font-semibold">Country</th>
              <th className="px-5 py-3 text-right font-semibold">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {rows.map((row) => (
              <tr key={`${title}-${row.clinic_id}`}>
                <td className="whitespace-nowrap px-5 py-3 font-medium text-slate-900">{row.clinic_id}</td>
                <td className="px-5 py-3">{row.country}</td>
                <td className="whitespace-nowrap px-5 py-3 text-right font-semibold">{value(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatMonth(value: string): string {
  const parsed = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function formatCurrency(value: number, currency: ClinicPerformanceRow["currency"]): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}
