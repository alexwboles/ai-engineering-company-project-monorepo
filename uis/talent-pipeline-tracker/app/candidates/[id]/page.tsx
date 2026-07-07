import { CandidateDetailPage } from "@/components/candidate-detail-page";
import { getRecordById, getRecordNotes } from "@/services/records";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let record = null;
  let notes: Awaited<ReturnType<typeof getRecordNotes>> = [];
  let initialError: string | null = null;

  try {
    [record, notes] = await Promise.all([getRecordById(id), getRecordNotes(id)]);
  } catch (error) {
    initialError = error instanceof Error ? error.message : "Unable to load candidate details.";
  }

  return <CandidateDetailPage id={id} initialCandidate={record} initialNotes={notes} initialError={initialError} />;
}
