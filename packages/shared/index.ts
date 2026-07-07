// Shared types for HealthCore — Milestone 2

export type ClaimStatus =
  | "submitted"
  | "approved"
  | "denied"
  | "pending"
  | "appealed";

export type DenialReason =
  | "missing_authorisation"
  | "coding_error"
  | "duplicate_claim"
  | "patient_not_covered"
  | "service_not_covered"
  | "incomplete_documentation";

export type ServiceType =
  | "primary_care"
  | "chronic_disease"
  | "preventive"
  | "specialist"
  | "womens_health"
  | "paediatric"
  | "mental_health";

export interface Claim {
  claimId: string; // Format: "CLM-XXXXXX"
  patientId: string; // Format: "HC-XXXXXX"
  locationId: string; // Clinic ID (e.g., "us-tx-001")
  serviceType: ServiceType;
  payerName: string;
  payerId: string;
  submissionDate: string; // ISO 8601 date string
  claimAmount: number; // > 0
  status: ClaimStatus;
  denialReason?: DenialReason; // Only when status === "denied"
  resubmitted: boolean;
}

export type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "completed"
  | "no_show"
  | "cancelled";

export interface Appointment {
  appointmentId: string; // Format: "APT-XXXXXX"
  patientId: string; // Format: "HC-XXXXXX"
  locationId: string; // Clinic ID
  serviceType: ServiceType;
  scheduledDate: string; // ISO 8601 date string
  scheduledTime: string; // "HH:MM" 24-hour
  status: AppointmentStatus;
  noShowReason?: string; // Only when status === "no_show"
  confirmedAt?: string; // ISO 8601 datetime
}

export type ClinicianRole =
  | "physician"
  | "nurse_practitioner"
  | "nurse"
  | "medical_assistant";

export interface Clinician {
  clinicianId: string; // Format: "CLN-XXXXXX"
  firstName: string;
  lastName: string;
  role: ClinicianRole;
  locationId: string;
  licenceState: string; // US state code or "UK"
  licenceExpiryDate: string; // ISO 8601 date string
  cmeHoursRequired: number; // >= 0
  cmeHoursLogged: number; // >= 0
  cmeYearStartDate: string; // ISO 8601 date — start of current CME cycle
}

export interface Location {
  locationId: string;
  name: string;
  city: string;
  stateOrCountry: string;
  country: "US" | "UK";
  phone: string;
  averageConsultationFee: Record<ServiceType, number>;
}

export type CMEStatus = "on_track" | "at_risk" | "overdue" | "complete";

export interface CMEReport {
  clinicianId: string;
  fullName: string; // "${firstName} ${lastName}"
  role: ClinicianRole;
  locationId: string;
  hoursRequired: number;
  hoursLogged: number;
  hoursRemaining: number; // Math.max(0, required - logged)
  percentComplete: number; // (logged / required) * 100, rounded to 1 decimal
  daysRemainingInCycle: number; // Calendar days from asOfDate to end of CME cycle
  complianceStatus: CMEStatus;
  licenceExpiryDate: string;
  licenceDaysRemaining: number; // Calendar days from asOfDate to licence expiry
}
