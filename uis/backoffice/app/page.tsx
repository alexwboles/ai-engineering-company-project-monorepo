import { buildOperationalSnapshot } from "@/lib/operational-snapshot";
import { DashboardTelemetry } from "@/app/dashboard-telemetry";

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

export default function Home() {
  const asOfDate = "2025-03-14";
  const snapshot = buildOperationalSnapshot(asOfDate);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <DashboardTelemetry
        asOfDate={asOfDate}
      />
      <header className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">HealthCore Backoffice</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Operations Command View</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          This internal entry dashboard imports Milestone 2 TypeScript business logic from its original module
          and renders immediate operational indicators for billing, patient access, and clinician compliance.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-slate-500">Overall claim denial rate</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{formatPercent(snapshot.claimDenialRate)}</p>
        </article>
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:col-span-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Denial rate by payer</p>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-slate-700">
            {Object.entries(snapshot.denialRateByPayer).map(([payer, rate]) => (
              <span key={payer} className="rounded-full bg-slate-100 px-3 py-1">
                {payer}: {formatPercent(rate)}
              </span>
            ))}
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Weekly No-Show Cost by Location</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Location</th>
                  <th className="pb-2">Weekly cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {snapshot.noShowCostByLocation.map((row) => (
                  <tr key={row.locationId}>
                    <td className="py-2">{row.locationName}</td>
                    <td className="py-2 font-medium">${row.weeklyCost.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">CME Compliance Snapshot</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Clinician</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Progress</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {snapshot.cmeSummary.map((row) => (
                  <tr key={row.clinicianId}>
                    <td className="py-2">{row.fullName}</td>
                    <td className="py-2">{row.status.replaceAll("_", " ")}</td>
                    <td className="py-2">{row.percentComplete.toFixed(1)}% ({row.hoursRemaining}h remaining)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
  );
}
