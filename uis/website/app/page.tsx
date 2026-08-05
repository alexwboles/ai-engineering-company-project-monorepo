import { MetricCard } from "@/components/metric-card";
import { SectionTitle } from "@/components/section-title";
import { locations, metrics, services } from "@/lib/content";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-20 px-4 py-10 sm:px-6 lg:px-8">
      <section className="rounded-3xl border border-cyan-100 bg-gradient-to-br from-cyan-50 via-white to-emerald-50 p-8 shadow-sm sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-700">HealthCore Digital</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Accessible, high-quality outpatient care across the US and UK.
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
          HealthCore operates a network of clinics designed around same-day access, continuity of care,
          and modern patient experience. Our teams combine clinical excellence with data-driven operations.
        </p>
      </section>

      <section className="space-y-6">
        <SectionTitle
          eyebrow="Network Impact"
          title="The scale and priorities behind HealthCore"
          description="Our operational model is built to keep care fast, safe, and coordinated across all locations."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle
          eyebrow="Services"
          title="Integrated care programs for everyday clinical needs"
        />
        <div className="grid gap-4 md:grid-cols-3">
          {services.map((service) => (
            <article key={service.title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900">{service.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{service.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle
          eyebrow="Clinic Footprint"
          title="Operating across two healthcare systems"
          description="HealthCore clinics serve patients across multiple US states and UK cities with localized workflows and shared standards."
        />
        <div className="grid gap-4 md:grid-cols-2">
          {locations.map((location) => (
            <article key={location.region} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-baseline justify-between">
                <h3 className="text-lg font-semibold text-slate-900">{location.region}</h3>
                <span className="text-xs uppercase tracking-wide text-slate-500">{location.clinics} clinics</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{location.highlights}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-slate-900 p-8 text-slate-100 sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">Leadership Focus</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight">Building a modern healthcare operating core</h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300">
          HealthCore Digital is unifying workflows across clinical operations, patient access, billing, compliance,
          and workforce enablement. Our roadmap prioritizes measurable outcomes: lower no-show rates, reduced claim denials,
          and better operational visibility for decision-makers.
        </p>
      </section>
    </main>
  );
}
