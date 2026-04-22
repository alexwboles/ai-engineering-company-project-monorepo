// HealthCore Data Models
// Define interfaces for the main business entities based on the CONTEXT.md

// Clinic entity
export interface Clinic {
  id: string;
  name: string;
  country: 'US' | 'UK';
  city: string;
  address: string;
  ehrSystem: 'US' | 'UK'; // US and UK use different EHRs
}

// Employee entity
export interface Employee {
  id: string;
  name: string;
  role: 'Physician' | 'Nurse Practitioner' | 'Nurse' | 'Medical Assistant' | 'Operations' | 'Administration' | 'Technology' | 'Other';
  clinicId: string;
  country: 'US' | 'UK';
  hireDate: string; // ISO date
  isClinician: boolean;
  cmeHours?: number; // Continuing Medical Education hours (clinicians only)
}

// Patient entity
export interface Patient {
  id: string;
  name: string;
  country: 'US' | 'UK';
  clinicId: string;
  dateOfBirth: string; // ISO date
  language: 'English' | 'Spanish' | 'Other';
}

// Appointment entity
export interface Appointment {
  id: string;
  patientId: string;
  clinicId: string;
  date: string; // ISO date
  time: string; // HH:mm
  status: 'Scheduled' | 'Completed' | 'No-Show' | 'Cancelled';
  createdBy: string; // Employee ID
}

// Billing entity
export interface Billing {
  id: string;
  appointmentId: string;
  country: 'US' | 'UK';
  amount: number;
  status: 'Pending' | 'Paid' | 'Denied';
  payer: 'Insurance' | 'Medicare' | 'Medicaid' | 'Private' | 'NHS';
}

// Compliance Training entity
export interface ComplianceTraining {
  id: string;
  employeeId: string;
  completed: boolean;
  dateCompleted?: string; // ISO date
  type: 'HIPAA' | 'GDPR' | 'Other';
}
