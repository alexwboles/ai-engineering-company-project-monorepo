// Aggregation and reporting utilities for HealthCore
import { Appointment } from '../types/models';

export function countBy<T, K extends keyof T>(array: T[], key: K): Record<string, number> {
  return array.reduce((acc, item) => {
    const k = String(item[key]);
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
}

export function sumBy<T>(array: T[], key: keyof T): number {
  return array.reduce((acc, item) => acc + (typeof item[key] === 'number' ? (item[key] as number) : 0), 0);
}

export function averageBy<T>(array: T[], key: keyof T): number {
  const nums = array.map(item => (typeof item[key] === 'number' ? (item[key] as number) : 0));
  return nums.length === 0 ? 0 : nums.reduce((a, b) => a + b, 0) / nums.length;
}
