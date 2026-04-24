// Utility functions for HealthCore data
import { Claim, Appointment, Clinician, Location } from '../types/models';

// Filter by predicate
export function filterBy<T>(array: T[], predicate: (item: T) => boolean): T[] {
  return array.filter(predicate);
}

// Sort by key
export function sortBy<T>(array: T[], key: keyof T, ascending: boolean = true): T[] {
  return [...array].sort((a, b) => {
    if (a[key] === b[key]) return 0;
    if (a[key] == null) return 1;
    if (b[key] == null) return -1;
    if (a[key] < b[key]) return ascending ? -1 : 1;
    return ascending ? 1 : -1;
  });
}

// Count by key
export function countBy<T, K extends keyof T>(array: T[], key: K): Record<string, number> {
  return array.reduce((acc, item) => {
    const k = String(item[key]);
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
}

// Validate patient object
export function validatePatient(patient: any): string[] {
  const errors: string[] = [];
  if (!patient.id) errors.push('Missing patient id');
  if (!patient.name) errors.push('Missing patient name');
  if (!patient.country) errors.push('Missing patient country');
  if (!patient.clinicId) errors.push('Missing clinicId');
  if (!patient.dateOfBirth) errors.push('Missing date of birth');
  if (!patient.language) errors.push('Missing language');
  return errors;
}

// Additional utilities for assignment goals will be added in utils/
