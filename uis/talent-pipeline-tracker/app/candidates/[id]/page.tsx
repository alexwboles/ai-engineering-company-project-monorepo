"use client";

import { useCallback, useEffect, useState } from "react";
import { CandidateDetailPage } from "@/components/candidate-detail-page";
import { getRecordById, getRecordNotes } from "@/services/records";
import type { CandidateNote, CandidateRecord } from "@/types/talent";

export default function Page({ params }: { params: { id: string } }) {
  const id = params.id;
  const [record, setRecord] = useState<CandidateRecord | null>(null);
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [initialError, setInitialError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);

  const retry = useCallback(() => {
    setReloadToken((current) => current + 1);
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setInitialError(null);

      try {
        const [loadedRecord, loadedNotes] = await Promise.all([getRecordById(id), getRecordNotes(id)]);
        setRecord(loadedRecord);
        setNotes(loadedNotes ?? []);
      } catch {
        setRecord(null);
        setNotes([]);
        setInitialError("Unable to load candidate details right now.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id, reloadToken]);

  if (loading) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-1 items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
        <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Loading candidate details...</p>
      </main>
    );
  }

  return (
    <CandidateDetailPage
      id={id}
      initialCandidate={record}
      initialNotes={notes}
      initialError={initialError}
      onRetryLoad={retry}
    />
  );
}
