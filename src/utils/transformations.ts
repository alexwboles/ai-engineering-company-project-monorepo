// Aggregation and reporting functions for HealthCore
import { Appointment, Billing, Employee } from '../types/models';

// Count elements by category (generic)
export function countBy<T, K extends keyof T>(array: T[], key: K): Record<string, number> {
  return array.reduce((acc, item) => {
    const k = String(item[key]);
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
}

// Sum numeric values by field
export function sumBy<T>(array: T[], key: keyof T): number {
  return array.reduce((acc, item) => acc + (typeof item[key] === 'number' ? (item[key] as number) : 0), 0);
}

// Find maximum value by field
export function maxBy<T>(array: T[], key: keyof T): T | null {
  if (array.length === 0) return null;
  return array.reduce((max, item) => (item[key] > max[key] ? item : max), array[0]);
}

// Find minimum value by field
export function minBy<T>(array: T[], key: keyof T): T | null {
  if (array.length === 0) return null;
  return array.reduce((min, item) => (item[key] < min[key] ? item : min), array[0]);
}

// Calculate average of numeric field
export function averageBy<T>(array: T[], key: keyof T): number {
  const nums = array.map(item => (typeof item[key] === 'number' ? (item[key] as number) : 0));
  return nums.length === 0 ? 0 : nums.reduce((a, b) => a + b, 0) / nums.length;
}
