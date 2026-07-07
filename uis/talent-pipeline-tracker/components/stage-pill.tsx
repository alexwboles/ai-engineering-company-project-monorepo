import type { CandidateStage } from "@/types/talent";

const STAGE_STYLES: Record<string, string> = {
  pending: "bg-zinc-100 text-zinc-800",
  review: "bg-sky-100 text-sky-800",
  personal_interview: "bg-violet-100 text-violet-800",
  technical_interview: "bg-indigo-100 text-indigo-800",
  offer_presented: "bg-teal-100 text-teal-800",
};

function formatValue(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function StagePill({ stage }: { stage: CandidateStage | string }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STAGE_STYLES[stage] ?? "bg-gray-100 text-gray-700"}`}>
      {formatValue(stage)}
    </span>
  );
}
