# CONTEXT — HealthCore

**Milestone 2: Programming Fundamentals**  
**Company:** HealthCore — Outpatient Healthcare Network  
**Your Role:** Junior AI Engineer, HealthCore Digital Team  
**Project Owner:** James Osei, CTO

---

## About HealthCore

HealthCore is an outpatient healthcare services company operating 12 clinics across the United States (Texas, Florida, Georgia) and the United Kingdom (London, Manchester). You're part of HealthCore Digital, the internal technology unit built to modernise clinical and operational workflows. The company processes around 600 patient visits per week, manages insurance billing across US and UK systems, and employs over 200 clinical and administrative staff.

---

## Your Assignment

James Osei, the CTO, needs you to build the core data processing logic for three of HealthCore's most pressing operational problems: billing denial tracking, no-show cost estimation, and CME (continuing medical education) compliance monitoring.

Right now, Tom Callahan's billing team calculates denial rates manually from CSV exports. Marcus Reid's clinical team has no way to estimate how much revenue is lost to no-shows each week. And Diane Foster's people team tracks CME hours in a spreadsheet with no alerts when clinicians fall behind — which creates real regulatory risk.

This milestone focuses on building the TypeScript functions that will power an internal operations dashboard. This is pure programming — no AI, no prompting. James needs to see that you can write solid, well-typed code that handles real business logic correctly.

> "The goal of this milestone is not complexity — it's reliability. These numbers go to Tom, Marcus, and Diane every Monday morning. If they're wrong, I hear about it. Write code you can trust."  
> — James Osei, CTO

---

## What You're Building

You will implement a set of TypeScript utilities to:

1. **Model claims, appointments, and clinician data** using interfaces
2. **Filter and search operational records** by location, status, and date
3. **Calculate billing denial rates** by payer and location
4. **Estimate no-show revenue impact** per clinic per week
5. **Track CME compliance** and flag clinicians at risk
6. **Validate data** before processing

---

## Business Entities

### Claim

A claim represents a billing request submitted to an insurance payer after a patient visit.

**Interface: `Claim`**

```typescript
interface Claim {
  claimId: string; // Format: "CLM-XXXXXX" (e.g., "CLM-000042")
  patientId: string; // Format: "HC-XXXXXX" (e.g., "HC-A3F291")
  locationId: string; // Clinic ID (e.g., "us-tx-001")
  serviceType: ServiceType; // Type of care delivered
  payerName: string; // Insurance provider name (e.g., "BlueCross")
  payerId: string; // Alphanumeric payer code
  submissionDate: string; // ISO 8601 date string
  claimAmount: number; // Amount billed in USD (must be > 0)
  status: ClaimStatus; // Current claim status
  denialReason?: DenialReason; // Only present when status === "denied"
  resubmitted: boolean; // Whether the claim was resubmitted after denial
}

type ClaimStatus = "submitted" | "approved" | "denied" | "pending" | "appealed";

type DenialReason =
  | "missing_authorisation"
  | "coding_error"
  | "duplicate_claim"
  | "patient_not_covered"
  | "service_not_covered"
  | "incomplete_documentation";

type ServiceType =
  | "primary_care"
  | "chronic_disease"
  | "preventive"
  | "specialist"
  | "womens_health"
  | "paediatric"
  | "mental_health";
```

**Validation Rules:**

- `claimAmount` must be > 0
- `submissionDate` must not be a future date
- `locationId` must match one of the known clinic IDs
- If `status === "denied"`, `denialReason` must be present
- `patientId` must match the format `HC-` followed by 6 alphanumeric characters

---

### Appointment

An appointment represents a scheduled patient visit at one of HealthCore's clinics.

**Interface: `Appointment`**

```typescript
interface Appointment {
  appointmentId: string; // Format: "APT-XXXXXX"
  patientId: string; // Format: "HC-XXXXXX"
  locationId: string; // Clinic ID
  serviceType: ServiceType; // Type of care scheduled
  scheduledDate: string; // ISO 8601 date string
  scheduledTime: string; // "HH:MM" in 24-hour format
  status: AppointmentStatus; // Current appointment status
  noShowReason?: string; // Free text, only present when status === "no_show"
  confirmedAt?: string; // ISO 8601 datetime, absent if not yet confirmed
}

type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "completed"
  | "no_show"
  | "cancelled";
```

**Validation Rules:**

- `scheduledTime` must be a valid 24-hour time string in the format "HH:MM"
- `locationId` must match one of the known clinic IDs
- If `status === "no_show"`, `noShowReason` should be present (warn if missing, do not reject)

---

### Clinician

A clinician is a licensed clinical staff member who must maintain continuing medical education hours.

**Interface: `Clinician`**

```typescript
interface Clinician {
  clinicianId: string; // Format: "CLN-XXXXXX"
  firstName: string;
  lastName: string;
  role: ClinicianRole; // Determines CME requirements
  locationId: string; // Assigned clinic
  licenceState: string; // US state code (e.g., "TX") or "UK"
  licenceExpiryDate: string; // ISO 8601 date string
  cmeHoursRequired: number; // Annual CME hours required for this role
  cmeHoursLogged: number; // Hours logged so far in the current cycle
  cmeYearStartDate: string; // ISO 8601 date — start of current CME cycle
}

type ClinicianRole =
  | "physician"
  | "nurse_practitioner"
  | "nurse"
  | "medical_assistant";
```

**Validation Rules:**

- `cmeHoursRequired` must be >= 0
- `cmeHoursLogged` must be >= 0
- `licenceExpiryDate` must be a valid future or present date (past dates are flagged as expired)
- `role` must be one of the four defined values

---

### Location

A location represents one of HealthCore's clinics, including the average fees used for no-show cost calculations.

**Interface: `Location`**

```typescript
interface Location {
  locationId: string;
  name: string;
  city: string;
  stateOrCountry: string;
  country: "US" | "UK";
  phone: string;
  averageConsultationFee: Record<ServiceType, number>; // Average fee in USD per service type
}
```

---

## Sample Data

### Clinicians
```json
[
  { "id": 1, "name": "Dr. Alice Smith", "specialty": "Cardiology", "active": true },
  { "id": 2, "name": "Dr. Bob Jones", "specialty": "Neurology", "active": true },
  { "id": 3, "name": "Dr. Carol Lee", "specialty": "Pediatrics", "active": false }
]
```

### Appointments
```json
[
  { "id": 1, "patient": "John Doe", "clinicianId": 1, "date": "2024-04-01", "status": "completed", "noShow": false },
  { "id": 2, "patient": "Jane Roe", "clinicianId": 2, "date": "2024-04-02", "status": "no-show", "noShow": true },
  { "id": 3, "patient": "Sam Lee", "clinicianId": 1, "date": "2024-04-03", "status": "completed", "noShow": false }
]
```

### Claims
```json
[
  { "id": 1, "appointmentId": 1, "amount": 200, "status": "approved" },
  { "id": 2, "appointmentId": 2, "amount": 150, "status": "denied" },
  { "id": 3, "appointmentId": 3, "amount": 180, "status": "approved" }
]
```

### Locations
```json
[
  { "id": 1, "name": "Main Clinic", "address": "123 Main St" },
  { "id": 2, "name": "Westside Branch", "address": "456 West Ave" }
]
```
