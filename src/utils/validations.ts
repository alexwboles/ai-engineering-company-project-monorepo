// Validation utilities for HealthCore
import { Appointment, Clinician, Claim } from '../types/models';

export function validateAppointment(appointment: Appointment): string[] {
  const errors: string[] = [];
  if (!appointment.appointmentId) errors.push('Missing appointment id');
  if (!appointment.patientId) errors.push('Missing patientId');
  if (!appointment.locationId) errors.push('Missing locationId');
  if (!appointment.scheduledDate) errors.push('Missing scheduledDate');
  if (!appointment.scheduledTime) errors.push('Missing scheduledTime');
  if (!appointment.status) errors.push('Missing status');
  return errors;
}

export function validateClinician(clinician: Clinician): string[] {
  const errors: string[] = [];
  if (!clinician.clinicianId) errors.push('Missing clinicianId');
  if (!clinician.firstName) errors.push('Missing firstName');
  if (!clinician.lastName) errors.push('Missing lastName');
  if (!clinician.role) errors.push('Missing role');
  if (!clinician.locationId) errors.push('Missing locationId');
  if (!clinician.licenceState) errors.push('Missing licenceState');
  if (!clinician.licenceExpiryDate) errors.push('Missing licenceExpiryDate');
  if (clinician.cmeHoursRequired == null) errors.push('Missing cmeHoursRequired');
  if (clinician.cmeHoursLogged == null) errors.push('Missing cmeHoursLogged');
  if (!clinician.cmeYearStartDate) errors.push('Missing cmeYearStartDate');
  return errors;
}

export function validateClaim(claim: Claim): string[] {
  const errors: string[] = [];
  if (!claim.claimId) errors.push('Missing claimId');
  if (!claim.patientId) errors.push('Missing patientId');
  if (!claim.locationId) errors.push('Missing locationId');
  if (!claim.serviceType) errors.push('Missing serviceType');
  if (!claim.payerName) errors.push('Missing payerName');
  if (!claim.payerId) errors.push('Missing payerId');
  if (!claim.submissionDate) errors.push('Missing submissionDate');
  if (claim.claimAmount == null) errors.push('Missing claimAmount');
  if (!claim.status) errors.push('Missing status');
  return errors;
}
