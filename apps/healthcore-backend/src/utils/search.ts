// apps/healthcore-backend/src/utils/search.ts

import { Claim, Clinician } from "../../../../packages/shared/index";

/**
 * findClaimById
 * Linear search — returns the claim or null.
 */
export function findClaimById(
  claims: Claim[],
  claimId: string
): Claim | null {
  for (const claim of claims) {
    if (claim.claimId === claimId) return claim;
  }
  return null;
}

/**
 * findClinicianById
 * Linear search — returns the clinician or null.
 */
export function findClinicianById(
  clinicians: Clinician[],
  clinicianId: string
): Clinician | null {
  for (const clinician of clinicians) {
    if (clinician.clinicianId === clinicianId) return clinician;
  }
  return null;
}

/**
 * binarySearchClaimById
 * Assumes claims are already sorted ASCENDING by claimId.
 * Returns index if found, -1 otherwise.
 */
export function binarySearchClaimById(
  sortedClaims: Claim[],
  targetId: string
): number {
  let left = 0;
  let right = sortedClaims.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const midId = sortedClaims[mid].claimId;

    if (midId === targetId) return mid;

    if (midId < targetId) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }

  return -1;
}
