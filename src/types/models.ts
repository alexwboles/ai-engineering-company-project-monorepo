// HealthCore Data Models
export interface Claim {
  claimId: string;
  patientId: string;
  locationId: string;
  serviceType: ServiceType;
  payerName: string;
  payerId: string;
  submissionDate: string;
  claimAmount: number;
  status: ClaimStatus;
  denialReason?: DenialReason;
  resubmitted: boolean;
}

export type ClaimStatus = "submitted" | "approved" | "denied" | "pending" | "appealed";
export type DenialReason = "missing_authorisation" | "coding_error" | "duplicate_claim" | "patient_not_covered" | "service_not_covered" | "incomplete_documentation";
export type ServiceType = "primary_care" | "chronic_disease" | "preventive" | "specialist" | "womens_health" | "paediatric" | "mental_health";

export interface Appointment {
  appointmentId: string;
  patientId: string;
  locationId: string;
  serviceType: ServiceType;
  scheduledDate: string;
  scheduledTime: string;
  status: AppointmentStatus;
  noShowReason?: string;
  confirmedAt?: string;
}

export type AppointmentStatus = "scheduled" | "confirmed" | "completed" | "no_show" | "cancelled";

export interface Clinician {
  clinicianId: string;
  firstName: string;
  lastName: string;
  role: ClinicianRole;
  locationId: string;
  licenceState: string;
  licenceExpiryDate: string;
  cmeHoursRequired: number;
  cmeHoursLogged: number;
  cmeYearStartDate: string;
}

export type ClinicianRole = "physician" | "nurse_practitioner" | "nurse" | "medical_assistant";

export interface Location {
  locationId: string;
  name: string;
  city: string;
  stateOrCountry: string;
  country: "US" | "UK";
  phone: string;
  averageConsultationFee: Record<ServiceType, number>;
}
