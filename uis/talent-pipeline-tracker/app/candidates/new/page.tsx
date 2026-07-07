"use client";

import Link from "next/link";
import { useState } from "react";
import { CandidateForm } from "@/components/candidate-form";
import { createRecord } from "@/services/records";

export default function Page() {
  const [createdCandidateId, setCreatedCandidateId] = useState<string | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">HealthCore Candidate Intake</p>
          <h1 className="text-2xl font-semibold text-slate-900">Register Candidate Record</h1>
        </div>
        <Link href="/" className="text-sm font-semibold text-cyan-700 hover:text-cyan-800">
          Back to candidate list
        </Link>
      </header>

      <CandidateForm
        title="New Candidate Form"
        submitLabel="Create Candidate"
        onSubmit={async (payload) => {
          const created = await createRecord(payload);
          setCreatedCandidateId(created.id);
        }}
      />

      {createdCandidateId ? (
        <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Candidate record created successfully. Review the profile in{" "}
          <Link href={`/candidates/${createdCandidateId}`} className="font-semibold underline">
            candidate details
          </Link>
          .
        </p>
      ) : null}
    </main>
  );
}
