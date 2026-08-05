type Props = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function SectionTitle({ eyebrow, title, description }: Props) {
  return (
    <div className="max-w-3xl">
      <p className="text-xs font-semibold uppercase tracking-[0.26em] text-cyan-700">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{title}</h2>
      {description ? <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p> : null}
    </div>
  );
}
