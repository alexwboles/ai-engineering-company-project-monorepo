// apps/healthcore-backend/src/utils/collections.ts

import {
  Claim,
  Appointment,
  AppointmentStatus,
} from "../../../../packages/shared/index";

/**
 * filterClaims
 * Returns claims that match ALL provided filter criteria.
 */
export function filterClaims(
  claims: Claim[],
  filters: Partial<
    Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">
  >
): Claim[] {
  return claims.filter((claim) => {
    return Object.entries(filters).every(([key, value]) => {
      if (value === undefined) return true;
      return (claim as any)[key] === value;
    });
  });
}

/**
 * filterAppointmentsByStatus
 * Returns appointments whose status matches ANY of the provided statuses.
 */
export function filterAppointmentsByStatus(
  appointments: Appointment[],
  statuses: AppointmentStatus[]
): Appointment[] {
  return appointments.filter((appt) => statuses.includes(appt.status));
}

/**
 * sortClaimsById
 * Returns claims sorted alphanumerically by claimId.
 * Must NOT mutate original array.
 */
export function sortClaimsById(
  claims: Claim[],
  direction: "asc" | "desc"
): Claim[] {
  const sorted = [...claims].sort((a, b) =>
    a.claimId.localeCompare(b.claimId)
  );
  return direction === "asc" ? sorted : sorted.reverse();
}

/**
 * sortAppointmentsByDate
 * Returns appointments sorted by scheduledDate.
 * Must NOT mutate original array.
 */
export function sortAppointmentsByDate(
  appointments: Appointment[],
  direction: "asc" | "desc"
): Appointment[] {
  const sorted = [...appointments].sort((a, b) =>
    a.scheduledDate.localeCompare(b.scheduledDate)
  );
  return direction === "asc" ? sorted : sorted.reverse();
}

/**
 * groupClaimsBy
 * Groups claims by a specified key.
 */
export function groupClaimsBy(
  claims: Claim[],
  key: "locationId" | "payerName" | "status" | "serviceType"
): Record<string, Claim[]> {
  return claims.reduce<Record<string, Claim[]>>((acc, claim) => {
    const groupKey = claim[key];
    if (!acc[groupKey]) acc[groupKey] = [];
    acc[groupKey].push(claim);
    return acc;
  }, {});
}
