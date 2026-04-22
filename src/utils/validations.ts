// Business validation functions for HealthCore
import { Clinic, Employee, Patient, Appointment, Billing, ComplianceTraining } from '../types/models';

// Validate required fields for Patient
export function validatePatient(patient: Patient): string[] {
  const errors: string[] = [];
  if (!patient.id) errors.push('Missing patient id');
  if (!patient.name) errors.push('Missing patient name');
  if (!patient.country) errors.push('Missing patient country');
  if (!patient.clinicId) errors.push('Missing clinicId');
  if (!patient.dateOfBirth) errors.push('Missing date of birth');
  if (!patient.language) errors.push('Missing language');
  return errors;
}

// Validate required fields and CME hours for Employee
export function validateEmployee(employee: Employee): string[] {
  const errors: string[] = [];
  if (!employee.id) errors.push('Missing employee id');
  if (!employee.name) errors.push('Missing employee name');
  if (!employee.role) errors.push('Missing employee role');
  if (!employee.clinicId) errors.push('Missing clinicId');
  if (!employee.country) errors.push('Missing country');
  if (!employee.hireDate) errors.push('Missing hire date');
  if (employee.isClinician && (employee.cmeHours == null || employee.cmeHours < 0)) {
    errors.push('Clinician must have non-negative CME hours');
  }
  return errors;
}

// Validate appointment status and required fields
export function validateAppointment(appointment: Appointment): string[] {
  const errors: string[] = [];
  if (!appointment.id) errors.push('Missing appointment id');
  if (!appointment.patientId) errors.push('Missing patientId');
  if (!appointment.clinicId) errors.push('Missing clinicId');
  if (!appointment.date) errors.push('Missing date');
  if (!appointment.time) errors.push('Missing time');
  if (!appointment.status) errors.push('Missing status');
  if (!appointment.createdBy) errors.push('Missing createdBy');
  if (!['Scheduled', 'Completed', 'No-Show', 'Cancelled'].includes(appointment.status)) {
    errors.push('Invalid appointment status');
  }
  return errors;
}

// Validate billing
export function validateBilling(billing: Billing): string[] {
  const errors: string[] = [];
  if (!billing.id) errors.push('Missing billing id');
  if (!billing.appointmentId) errors.push('Missing appointmentId');
  if (!billing.country) errors.push('Missing country');
  if (billing.amount == null || billing.amount < 0) errors.push('Invalid amount');
  if (!billing.status) errors.push('Missing status');
  if (!billing.payer) errors.push('Missing payer');
  return errors;
}

// Validate compliance training
export function validateComplianceTraining(training: ComplianceTraining): string[] {
  const errors: string[] = [];
  if (!training.id) errors.push('Missing training id');
  if (!training.employeeId) errors.push('Missing employeeId');
  if (training.completed && !training.dateCompleted) errors.push('Completed training must have dateCompleted');
  if (!training.type) errors.push('Missing training type');
  return errors;
}
