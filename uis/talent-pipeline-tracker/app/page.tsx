import { Suspense } from "react";
import { CandidateListPage } from "@/components/candidate-list-page";

export default function Home() {
  return (
    <Suspense fallback={<p className="mx-auto mt-10 w-full max-w-6xl rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Loading HealthCore candidate pipeline...</p>}>
      <CandidateListPage />
    </Suspense>
  );
}
