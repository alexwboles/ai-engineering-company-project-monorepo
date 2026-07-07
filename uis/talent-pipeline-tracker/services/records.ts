import { apiRequest } from "@/lib/api-client";
import type {
  CandidateCreateInput,
  CandidateListResponse,
  CandidateNote,
  CandidateNotesResponse,
  CandidatePatchInput,
  CandidateRecord,
  NoteCreateInput,
} from "@/types/talent";

export type RecordQuery = {
  status?: string;
  stage?: string;
  search?: string;
  page?: number;
  limit?: number;
};

function toQueryString(query: RecordQuery) {
  const params = new URLSearchParams();

  if (query.status) params.set("status", query.status);
  if (query.stage) params.set("stage", query.stage);
  if (query.search) params.set("search", query.search);
  if (query.page) params.set("page", String(query.page));
  if (query.limit) params.set("limit", String(query.limit));

  const value = params.toString();
  return value ? `?${value}` : "";
}

export async function getRecords(query: RecordQuery = {}): Promise<CandidateListResponse> {
  return apiRequest<CandidateListResponse>(`/records${toQueryString(query)}`);
}

export async function getRecordById(id: string): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`);
}

export async function createRecord(input: CandidateCreateInput): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>("/records", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function replaceRecord(id: string, input: CandidateCreateInput): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export async function patchRecord(id: string, input: CandidatePatchInput): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function getRecordNotes(id: string): Promise<CandidateNote[]> {
  const response = await apiRequest<CandidateNotesResponse | CandidateNote[]>(`/records/${id}/notes`);

  if (Array.isArray(response)) {
    return response;
  }

  return response.data;
}

export async function addRecordNote(id: string, input: NoteCreateInput): Promise<CandidateNote> {
  return apiRequest<CandidateNote>(`/records/${id}/notes`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function deleteRecordNote(id: string, noteId: string): Promise<void> {
  await apiRequest<void>(`/records/${id}/notes/${noteId}`, {
    method: "DELETE",
  });
}
