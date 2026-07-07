// apps/healthcore-backend/src/utils/validations.ts

import {
  Claim,
  Clinician,
} from "../../../../packages/shared/index";

/* -------------------------------------------------------
   CLAIM VALIDATION
-------------------------------------------------------- */

export function validateClaim(
  claim: Claim,
  knownLocationIds: string[]
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // claimAmount > 0
  if (claim.claimAmount <= 0) {
    errors.push("claimAmount must be greater than 0.");
  }

  // submissionDate must not be in the future
  const submission = new Date(claim.submissionDate);
  const today = new Date();
  if (submission > today) {
    errors.push("submissionDate cannot be a future date.");
  }

  // locationId must be known
  if (!knownLocationIds.includes(claim.locationId)) {
    errors.push(`locationId '${claim.locationId}' is not a known clinic ID.`);
  }

  // patientId format: HC-XXXXXX (alphanumeric)
  const patientRegex = /^HC-[A-Za-z0-9]{6}$/;
  if (!patientRegex.test(claim.patientId)) {
    errors.push("patientId must match format HC-XXXXXX (6 alphanumeric chars).");
  }

  // If denied → denialReason must be present
  if (claim.status === "denied" && !claim.denialReason) {
    errors.push("denialReason must be provided when status is 'denied'.");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/* -------------------------------------------------------
   CLINICIAN VALIDATION
-------------------------------------------------------- */

export function validateClinician(
  clinician: Clinician
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // cmeHoursRequired >= 0
  if (clinician.cmeHoursRequired < 0) {
    errors.push("cmeHoursRequired must be >= 0.");
  }

  // cmeHoursLogged >= 0
  if (clinician.cmeHoursLogged < 0) {
    errors.push("cmeHoursLogged must be >= 0.");
  }

  // licenceExpiryDate must be valid and not in the past
  const expiry = new Date(clinician.licenceExpiryDate);
  const today = new Date();

  if (isNaN(expiry.getTime())) {
    errors.push("licenceExpiryDate must be a valid ISO date.");
  } else if (expiry < today) {
    errors.push("licenceExpiryDate is in the past — licence is expired.");
  }

  // role must be one of the defined values
  const validRoles = [
    "physician",
    "nurse_practitioner",
    "nurse",
    "medical_assistant",
  ];

  if (!validRoles.includes(clinician.role)) {
    errors.push(`Invalid clinician role: ${clinician.role}`);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/* -------------------------------------------------------
   THRESHOLD HELPERS
-------------------------------------------------------- */

export function isDenialRateAboveThreshold(
  rate: number,
  threshold: number = 8
): boolean {
  return rate > threshold;
}

export function isNoShowRateAboveThreshold(
  rate: number,
  threshold: number = 20
): boolean {
  return rate > threshold;
}
