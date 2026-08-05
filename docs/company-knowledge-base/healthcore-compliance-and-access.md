# HealthCore compliance and access policies

Source: `CONTEXT.md` and `CONTEXT_HEALTHCORE.md` in this repository.

## Patient data protection

Patient data is protected under HIPAA for United States operations and UK GDPR for United Kingdom operations. Any HealthCore system that stores, accesses, or shares patient data must be evaluated by Compliance and Data Governance before release. Access should be limited to the operational purpose, auditable, and designed so information is not copied into systems that were not approved for the relevant country.

## Booking and no-show operations

Patient Experience and Access manages booking, confirmation, reminders, follow-up, and discharge communications. US patients currently book by phone and UK patients call a front desk, so the network does not have a shared online booking workflow. The 22% no-show rate is both a patient experience problem and a material revenue loss. Operational teams should use appointment status and no-show reason to identify where reminders, confirmation, or follow-up need improvement.

## Billing and claims operations

Revenue Cycle and Billing handles commercial insurance, Medicare, Medicaid, private pay, and a small NHS contract. A denied claim must have a denial reason such as missing authorisation, coding error, duplicate claim, patient not covered, service not covered, or incomplete documentation. A claim amount must be positive, the submission date cannot be in the future, and a denied claim should be tracked for resubmission or appeal. The current 14% denial rate is the baseline for corrective work.

## Workforce and clinical safety

People and Workforce monitors clinical hiring, onboarding, compliance training, and continuing medical education. Clinicians are physicians, nurse practitioners, nurses, or medical assistants, and each has an annual CME requirement and logged hours. Licence expiry and CME shortfalls are compliance risks that must be surfaced to the responsible manager before a clinician falls out of compliance.
