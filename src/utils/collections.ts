// Array utility functions for HealthCore
import { Clinic, Employee, Patient, Appointment, Billing, ComplianceTraining } from '../types/models';

// Generic filter function
export function filterBy<T>(array: T[], predicate: (item: T) => boolean): T[] {
  return array.filter(predicate);
}

// Generic sort function (single field, ascending/descending)
export function sortBy<T>(array: T[], key: keyof T, ascending: boolean = true): T[] {
  return [...array].sort((a, b) => {
    if (a[key] === b[key]) return 0;
    if (a[key] == null) return 1;
    if (b[key] == null) return -1;
    if (a[key] < b[key]) return ascending ? -1 : 1;
    return ascending ? 1 : -1;
  });
}

// Multi-field sort
export function sortByMultiple<T>(array: T[], keys: (keyof T)[], ascending: boolean[] = []): T[] {
  return [...array].sort((a, b) => {
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      const asc = ascending[i] ?? true;
      if (a[key] === b[key]) continue;
      if (a[key] == null) return 1;
      if (b[key] == null) return -1;
      if (a[key] < b[key]) return asc ? -1 : 1;
      return asc ? 1 : -1;
    }
    return 0;
  });
}
