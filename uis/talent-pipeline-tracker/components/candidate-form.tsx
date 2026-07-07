"use client";

import { useMemo, useState } from "react";
import type { CandidateCreateInput, CandidateRecord } from "@/types/talent";

type FormValues = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  experience_years: string;
};

type Props = {
  title: string;
  submitLabel: string;
  initialCandidate?: CandidateRecord;
  onSubmit: (payload: CandidateCreateInput) => Promise<void>;
};

function toInitialValues(candidate?: CandidateRecord): FormValues {
  return {
    full_name: candidate?.full_name ?? "",
    email: candidate?.email ?? "",
    phone: candidate?.phone ?? "",
    position: candidate?.position ?? "",
    linkedin_url: candidate?.linkedin_url ?? "",
    cv_url: candidate?.cv_url ?? "",
    experience_years: candidate ? String(candidate.experience_years) : "",
  };
}

export function CandidateForm({ title, submitLabel, initialCandidate, onSubmit }: Props) {
  const [values, setValues] = useState<FormValues>(() => toInitialValues(initialCandidate));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const initialValues = useMemo(() => toInitialValues(initialCandidate), [initialCandidate]);

  const onFieldChange = (field: keyof FormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const resetToInitial = () => {
    setValues(initialValues);
    setError(null);
    setSuccess(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const requiredFields: Array<keyof FormValues> = ["full_name", "email", "phone", "position", "experience_years"];
    const missingField = requiredFields.find((field) => values[field].trim().length === 0);

    if (missingField) {
      setError("Please complete all required fields before submitting this candidate record.");
      return;
    }

    const experienceYears = Number(values.experience_years);
    if (Number.isNaN(experienceYears) || experienceYears < 0) {
      setError("Experience years must be a valid number equal to or greater than 0.");
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim(),
        position: values.position.trim(),
        linkedin_url: values.linkedin_url.trim() || null,
        cv_url: values.cv_url.trim() || null,
        experience_years: experienceYears,
      });
      setSuccess("Candidate record saved successfully.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit candidate form.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
      <p className="mt-1 text-sm text-slate-500">Fields marked with * are required for HealthCore hiring records.</p>

      <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Full name *
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={values.full_name}
            onChange={(event) => onFieldChange("full_name", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Email *
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            type="email"
            value={values.email}
            onChange={(event) => onFieldChange("email", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Phone *
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={values.phone}
            onChange={(event) => onFieldChange("phone", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Position *
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={values.position}
            onChange={(event) => onFieldChange("position", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          LinkedIn URL
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={values.linkedin_url}
            onChange={(event) => onFieldChange("linkedin_url", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          CV URL
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={values.cv_url}
            onChange={(event) => onFieldChange("cv_url", event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 sm:col-span-2">
          Years of experience *
          <input
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            type="number"
            min={0}
            step="0.5"
            value={values.experience_years}
            onChange={(event) => onFieldChange("experience_years", event.target.value)}
          />
        </label>

        {error ? <p className="sm:col-span-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        {success ? <p className="sm:col-span-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</p> : null}

        <div className="sm:col-span-2 flex gap-2">
          <button
            type="submit"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Saving..." : submitLabel}
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
            onClick={resetToInitial}
            disabled={isSubmitting}
          >
            Reset
          </button>
        </div>
      </form>
    </section>
  );
}
