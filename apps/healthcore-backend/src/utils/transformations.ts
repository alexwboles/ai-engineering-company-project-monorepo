// apps/healthcore-backend/src/utils/transformations.ts

import {
  Claim,
  Location,
  Appointment,
  Clinician,
  CMEReport,
  CMEStatus,
} from "../../../../packages/shared/index";

import { groupClaimsBy } from "./collections";

/* -------------------------------------------------------
   BILLING DENIAL RATE CALCULATIONS
-------------------------------------------------------- */

/**
 * calculateDenialRate
 * Returns % of claims denied, rounded to 2 decimals.
 * Throws if claims array is empty.
 */
export function calculateDenialRate(claims: Claim[]): number {
  if (claims.length === 0) {
    throw new Error("Cannot calculate denial rate for empty claim list.");
  }

  const denied = claims.filter((c) => c.status === "denied").length;
  const rate = (denied / claims.length) * 100;

  return Number(rate.toFixed(2));
}

/**
 * denialRateByPayer
 * Groups by payerName → calculates denial rate per payer.
 */
export function denialRateByPayer(
  claims: Claim[]
): Record<string, number> {
  const grouped = groupClaimsBy(claims, "payerName");
  const result: Record<string, number> = {};

  for (const payer of Object.keys(grouped)) {
    result[payer] = calculateDenialRate(grouped[payer]);
  }

  return result;
}

/**
 * denialRateByLocation
 * Groups by locationId → calculates denial rate per location.
 */
export function denialRateByLocation(
  claims: Claim[]
): Record<string, number> {
  const grouped = groupClaimsBy(claims, "locationId");
  const result: Record<string, number> = {};

  for (const loc of Object.keys(grouped)) {
    result[loc] = calculateDenialRate(grouped[loc]);
  }

  return result;
}

/**
 * flagHighDenialPayers
 * Returns payers whose denial rate exceeds threshold (default 8%).
 */
export function flagHighDenialPayers(
  claims: Claim[],
  threshold: number = 8
): string[] {
  const rates = denialRateByPayer(claims);
  return Object.entries(rates)
    .filter(([_, rate]) => rate > threshold)
    .map(([payer]) => payer);
}

/* -------------------------------------------------------
   NO-SHOW COST ESTIMATION
-------------------------------------------------------- */

/**
 * calculateNoShowCost
 * Calculates total lost revenue for no-shows in the 7 days
 * ending on weekEndingDate (inclusive).
 */
export function calculateNoShowCost(
  appointments: Appointment[],
  location: Location,
  weekEndingDate: string
): number {
  const end = new Date(weekEndingDate);
  const start = new Date(end);
  start.setDate(end.getDate() - 6);

  const total = appointments
    .filter(
      (appt) =>
        appt.locationId === location.locationId &&
        appt.status === "no_show"
    )
    .filter((appt) => {
      const d = new Date(appt.scheduledDate);
      return d >= start && d <= end;
    })
    .reduce((sum, appt) => {
      const fee = location.averageConsultationFee[appt.serviceType];
      return sum + fee;
    }, 0);

  return Number(total.toFixed(2));
}

/**
 * noShowRateByLocation
 * % of appointments that are no-shows per location.
 */
export function noShowRateByLocation(
  appointments: Appointment[]
): Record<string, number> {
  const grouped: Record<string, Appointment[]> = {};

  for (const appt of appointments) {
    if (!grouped[appt.locationId]) grouped[appt.locationId] = [];
    grouped[appt.locationId].push(appt);
  }

  const result: Record<string, number> = {};

  for (const loc of Object.keys(grouped)) {
    const total = grouped[loc].length;
    const noShows = grouped[loc].filter((a) => a.status === "no_show").length;

    const rate = total === 0 ? 0 : (noShows / total) * 100;
    result[loc] = Number(rate.toFixed(2));
  }

  return result;
}

/**
 * flagHighNoShowLocations
 * Returns locationIds whose no-show rate exceeds threshold (default 20%).
 */
export function flagHighNoShowLocations(
  appointments: Appointment[],
  threshold: number = 20
): string[] {
  const rates = noShowRateByLocation(appointments);
  return Object.entries(rates)
    .filter(([_, rate]) => rate > threshold)
    .map(([loc]) => loc);
}

/* -------------------------------------------------------
   CME COMPLIANCE ENGINE
-------------------------------------------------------- */

/**
 * Helper: days between two dates (calendar days).
 */
function daysBetween(a: string, b: string): number {
  const d1 = new Date(a);
  const d2 = new Date(b);
  const diff = d2.getTime() - d1.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/**
 * Helper: end of CME cycle = start + 365 days.
 */
function getCycleEnd(startDate: string): string {
  const d = new Date(startDate);
  d.setDate(d.getDate() + 365);
  return d.toISOString().split("T")[0];
}

/**
 * generateCMEReport
 * Produces one CMEReport per clinician.
 */
export function generateCMEReport(
  clinicians: Clinician[],
  asOfDate: string
): CMEReport[] {
  return clinicians.map((c) => {
    const cycleEnd = getCycleEnd(c.cmeYearStartDate);

    const hoursRemaining = Math.max(0, c.cmeHoursRequired - c.cmeHoursLogged);

    const percentComplete =
      c.cmeHoursRequired === 0
        ? 100
        : Number(((c.cmeHoursLogged / c.cmeHoursRequired) * 100).toFixed(1));

    const daysRemainingInCycle = Math.max(
      0,
      daysBetween(asOfDate, cycleEnd)
    );

    const licenceDaysRemaining = Math.max(
      0,
      daysBetween(asOfDate, c.licenceExpiryDate)
    );

    const complianceStatus = determineCMEStatus(
      c,
      percentComplete,
      asOfDate,
      cycleEnd
    );

    return {
      clinicianId: c.clinicianId,
      fullName: `${c.firstName} ${c.lastName}`,
      role: c.role,
      locationId: c.locationId,
      hoursRequired: c.cmeHoursRequired,
      hoursLogged: c.cmeHoursLogged,
      hoursRemaining,
      percentComplete,
      daysRemainingInCycle,
      complianceStatus,
      licenceExpiryDate: c.licenceExpiryDate,
      licenceDaysRemaining,
    };
  });
}

/**
 * determineCMEStatus
 * Implements HealthCore's CME rules.
 */
function determineCMEStatus(
  clinician: Clinician,
  percentComplete: number,
  asOfDate: string,
  cycleEnd: string
): CMEStatus {
  const cycleEnded = new Date(asOfDate) > new Date(cycleEnd);

  if (clinician.cmeHoursLogged >= clinician.cmeHoursRequired) {
    return "complete";
  }

  if (cycleEnded) {
    return "overdue";
  }

  // Active cycle → check "at risk"
  const cycleStart = new Date(clinician.cmeYearStartDate);
  const totalDays = daysBetween(
    clinician.cmeYearStartDate,
    cycleEnd
  );
  const elapsedDays = daysBetween(
    clinician.cmeYearStartDate,
    asOfDate
  );

  const cyclePace = (elapsedDays / totalDays) * 100;

  if (percentComplete < cyclePace - 15) {
    return "at_risk";
  }

  return "on_track";
}

/**
 * getCliniciansAtRisk
 * Returns clinicians whose CME status is at_risk or overdue.
 */
export function getCliniciansAtRisk(
  clinicians: Clinician[],
  asOfDate: string
): Clinician[] {
  const reports = generateCMEReport(clinicians, asOfDate);
  const riskyIds = reports
    .filter((r) => r.complianceStatus === "at_risk" || r.complianceStatus === "overdue")
    .map((r) => r.clinicianId);

  return clinicians.filter((c) => riskyIds.includes(c.clinicianId));
}

/**
 * getCliniciansWithExpiringLicences
 * Returns clinicians whose licence expires within N days.
 */
export function getCliniciansWithExpiringLicences(
  clinicians: Clinician[],
  asOfDate: string,
  daysThreshold: number
): Clinician[] {
  return clinicians.filter((c) => {
    const daysLeft = daysBetween(asOfDate, c.licenceExpiryDate);
    return daysLeft <= daysThreshold;
  });
}
