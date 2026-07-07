"use client";

import Link from "next/link";
import { useState } from "react";
import { CandidateForm } from "@/components/candidate-form";
import { StagePill } from "@/components/stage-pill";
import { StatusPill } from "@/components/status-pill";
import {
  addRecordNote,
  deleteRecordNote,
  getRecordById,
  getRecordNotes,
  patchRecord,
  replaceRecord,
} from "@/services/records";
import {
  STAGE_OPTIONS,
  STATUS_OPTIONS,
  type CandidateNote,
  type CandidateRecord,
} from "@/types/talent";

type Props = {
  id: string;
  initialCandidate: CandidateRecord | null;
  initialNotes: CandidateNote[];
  initialError?: string | null;
};

function toReadableDate(value: string) {
  return new Date(value).toLocaleDateString();
}

export function CandidateDetailPage({ id, initialCandidate, initialNotes, initialError = null }: Props) {
  const [candidate, setCandidate] = useState<CandidateRecord | null>(initialCandidate);
  const [notes, setNotes] = useState<CandidateNote[]>(initialNotes);
  const [noteContent, setNoteContent] = useState("");

  const [error] = useState<string | null>(initialError);

  const [statusFeedback, setStatusFeedback] = useState<string | null>(null);
  const [stageFeedback, setStageFeedback] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isUpdatingStage, setIsUpdatingStage] = useState(false);

  const [isAddingNote, setIsAddingNote] = useState(false);
  const [noteFeedback, setNoteFeedback] = useState<string | null>(null);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);

  const handleStatusChange = async (nextStatus: string) => {
    if (!candidate || nextStatus === candidate.status) {
      return;
    }

    setIsUpdatingStatus(true);
    setStatusFeedback(null);

    try {
      const updated = await patchRecord(id, { status: nextStatus as (typeof STATUS_OPTIONS)[number] });
      setCandidate(updated);
      setStatusFeedback("Status updated.");
    } catch (statusError) {
      setStatusFeedback(statusError instanceof Error ? statusError.message : "Unable to update status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleStageChange = async (nextStage: string) => {
    if (!candidate || nextStage === candidate.stage) {
      return;
    }

    setIsUpdatingStage(true);
    setStageFeedback(null);

    try {
      const updated = await patchRecord(id, { stage: nextStage as (typeof STAGE_OPTIONS)[number] });
      setCandidate(updated);
      setStageFeedback("Stage updated.");
    } catch (stageError) {
      setStageFeedback(stageError instanceof Error ? stageError.message : "Unable to update stage.");
    } finally {
      setIsUpdatingStage(false);
    }
  };

  const handleAddNote = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNoteFeedback(null);

    if (!noteContent.trim()) {
      setNoteFeedback("Note content is required.");
      return;
    }

    setIsAddingNote(true);

    try {
      await addRecordNote(id, { content: noteContent.trim() });
      const [record, recordNotes] = await Promise.all([getRecordById(id), getRecordNotes(id)]);
      setCandidate(record);
      setNotes(recordNotes);
      setNoteContent("");
      setNoteFeedback("Note added.");
    } catch (noteError) {
      setNoteFeedback(noteError instanceof Error ? noteError.message : "Unable to add note.");
    } finally {
      setIsAddingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    setDeletingNoteId(noteId);
    setNoteFeedback(null);

    try {
      await deleteRecordNote(id, noteId);
      const [record, recordNotes] = await Promise.all([getRecordById(id), getRecordNotes(id)]);
      setCandidate(record);
      setNotes(recordNotes);
      setNoteFeedback("Note deleted.");
    } catch (deleteError) {
      setNoteFeedback(deleteError instanceof Error ? deleteError.message : "Unable to delete note.");
    } finally {
      setDeletingNoteId(null);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-7 px-4 py-10 sm:px-6 lg:px-8">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">HealthCore Candidate Profile</p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">People and Workforce Detail View</h1>
        </div>
        <Link href="/" className="text-sm font-semibold text-cyan-700 hover:text-cyan-800">
          Back to candidate list
        </Link>
      </header>

      {error ? <p className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

      {!error && candidate ? (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900">{candidate.full_name}</h2>
                <p className="mt-1 text-sm text-slate-500">{candidate.email}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={candidate.status} />
                <StagePill stage={candidate.stage} />
              </div>
            </div>

            <dl className="mt-6 grid gap-5 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Phone</dt>
                <dd className="text-sm text-slate-800">{candidate.phone}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Position</dt>
                <dd className="text-sm text-slate-800">{candidate.position}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">LinkedIn</dt>
                <dd className="text-sm text-slate-800 break-all">{candidate.linkedin_url ? <a className="text-cyan-700 hover:underline" href={candidate.linkedin_url} target="_blank" rel="noreferrer">{candidate.linkedin_url}</a> : "Not provided"}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">CV Link</dt>
                <dd className="text-sm text-slate-800 break-all">{candidate.cv_url ? <a className="text-cyan-700 hover:underline" href={candidate.cv_url} target="_blank" rel="noreferrer">{candidate.cv_url}</a> : "Not provided"}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Years of experience</dt>
                <dd className="text-sm text-slate-800">{candidate.experience_years}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Application date</dt>
                <dd className="text-sm text-slate-800">{toReadableDate(candidate.applied_at)}</dd>
              </div>
            </dl>
          </section>

          <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-2">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Update Status</h3>
              <select
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={candidate.status}
                onChange={(event) => void handleStatusChange(event.target.value)}
                disabled={isUpdatingStatus}
              >
                {STATUS_OPTIONS.map((statusOption) => (
                  <option key={statusOption} value={statusOption}>
                    {statusOption.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">{isUpdatingStatus ? "Saving status..." : statusFeedback ?? "Select a status to update immediately."}</p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-slate-900">Update Stage</h3>
              <select
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={candidate.stage}
                onChange={(event) => void handleStageChange(event.target.value)}
                disabled={isUpdatingStage}
              >
                {STAGE_OPTIONS.map((stageOption) => (
                  <option key={stageOption} value={stageOption}>
                    {stageOption.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">{isUpdatingStage ? "Saving stage..." : stageFeedback ?? "Select a stage to update immediately."}</p>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Internal Hiring Notes</h3>
            <p className="mt-1 text-sm text-slate-500">Capture interview insights, coordination updates, and follow-up actions.</p>

            <form className="mt-4 flex flex-col gap-2" onSubmit={handleAddNote}>
              <textarea
                className="min-h-24 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Write an internal People and Workforce note..."
                value={noteContent}
                onChange={(event) => setNoteContent(event.target.value)}
              />
              <div>
                <button
                  type="submit"
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  disabled={isAddingNote}
                >
                  {isAddingNote ? "Adding note..." : "Add note"}
                </button>
              </div>
            </form>

            {noteFeedback ? <p className="mt-3 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">{noteFeedback}</p> : null}

            <ul className="mt-4 space-y-3">
              {notes.map((note) => (
                <li key={note.id} className="rounded-lg border border-slate-200 p-3">
                  <p className="text-sm text-slate-800">{note.content}</p>
                  <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                    <span>{toReadableDate(note.created_at)}</span>
                    <button
                      type="button"
                      className="font-semibold text-rose-700 disabled:opacity-60"
                      onClick={() => void handleDeleteNote(note.id)}
                      disabled={deletingNoteId === note.id}
                    >
                      {deletingNoteId === note.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <CandidateForm
            title="Edit Candidate Data"
            submitLabel="Save Candidate Changes"
            initialCandidate={candidate}
            onSubmit={async (payload) => {
              const updated = await replaceRecord(id, payload);
              setCandidate(updated);
            }}
          />
        </>
      ) : null}

      {!error && !candidate ? (
        <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">Candidate was not found.</p>
      ) : null}
    </main>
  );
}
