import type { CandidateStatus } from "@/types/talent";

const STATUS_STYLES: Record<string, string> = {
  received: "bg-slate-100 text-slate-800",
  in_progress: "bg-amber-100 text-amber-800",
  selected: "bg-emerald-100 text-emerald-800",
  discarded: "bg-rose-100 text-rose-800",
};

function formatValue(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function StatusPill({ status }: { status: CandidateStatus | string }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"}`}>
      {formatValue(status)}
    </span>
  );
}
