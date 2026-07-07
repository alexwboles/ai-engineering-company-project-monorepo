export const STATUS_OPTIONS = ["received", "in_progress", "selected", "discarded"] as const;
export const STAGE_OPTIONS = [
  "pending",
  "review",
  "personal_interview",
  "technical_interview",
  "offer_presented",
] as const;

export type CandidateStatus = (typeof STATUS_OPTIONS)[number];
export type CandidateStage = (typeof STAGE_OPTIONS)[number];

export type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: CandidateStatus | string;
  stage: CandidateStage | string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

export type CandidateNote = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export type CandidateListResponse = {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
};

export type CandidateNotesResponse = {
  data: CandidateNote[];
  meta?: {
    total?: number;
  };
};

export type CandidateCreateInput = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
};

export type CandidatePatchInput = {
  status?: CandidateStatus | null;
  stage?: CandidateStage | null;
};

export type NoteCreateInput = {
  content: string;
};
