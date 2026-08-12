"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api-client";

type SupplierStatus = "active" | "suspended";
type SupplierCountry = "USA" | "UK";
type SupplierCurrency = "USD" | "GBP";
type ComplianceAgreement = "BAA" | "DPA" | "both";
type SupplierCategory =
  | "medical_supplies"
  | "laboratory_services"
  | "pharmaceutical"
  | "clinical_software"
  | "it_infrastructure"
  | "hr_and_payroll_software"
  | "cleaning_and_facilities"
  | "patient_communication"
  | "billing_and_coding_software"
  | "training_platforms";

type Supplier = {
  id: number;
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  monthly_rate: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  updated_at: string;
  compliance_agreement: ComplianceAgreement | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
};

const COUNTRY_OPTIONS: SupplierCountry[] = ["USA", "UK"];
const CATEGORY_OPTIONS: SupplierCategory[] = [
  "medical_supplies",
  "laboratory_services",
  "pharmaceutical",
  "clinical_software",
  "it_infrastructure",
  "hr_and_payroll_software",
  "cleaning_and_facilities",
  "patient_communication",
  "billing_and_coding_software",
  "training_platforms",
];
const COMPLIANCE_OPTIONS: ComplianceAgreement[] = ["BAA", "DPA", "both"];

function statusClasses(status: SupplierStatus): string {
  return status === "active"
    ? "bg-emerald-100 text-emerald-800 border-emerald-200"
    : "bg-rose-100 text-rose-800 border-rose-200";
}

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [countryFilter, setCountryFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [rateInputs, setRateInputs] = useState<Record<number, string>>({});
  const [updatingIds, setUpdatingIds] = useState<number[]>([]);

  const [name, setName] = useState("");
  const [country, setCountry] = useState<SupplierCountry | "">("");
  const [categories, setCategories] = useState<SupplierCategory[]>([]);
  const [monthlyRate, setMonthlyRate] = useState("");
  const [currency, setCurrency] = useState<SupplierCurrency>("USD");
  const [status, setStatus] = useState<SupplierStatus>("active");
  const [complianceAgreement, setComplianceAgreement] = useState<ComplianceAgreement | "">("");
  const [contractRenewalDate, setContractRenewalDate] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);

  async function fetchSuppliers() {
    setIsLoading(true);
    setListError("");
    const params = new URLSearchParams();
    if (countryFilter) params.set("country", countryFilter);
    if (categoryFilter) params.set("category", categoryFilter);

    try {
      const query = params.toString();
      const payload = await apiRequest<Supplier[]>(`/suppliers${query ? `?${query}` : ""}`, {}, { authRequired: false });
      setSuppliers(payload);
      setRateInputs(Object.fromEntries(payload.map((supplier) => [supplier.id, String(supplier.monthly_rate)])));
    } catch {
      setListError("Unable to load suppliers right now. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countryFilter, categoryFilter]);

  function toggleCategory(category: SupplierCategory) {
    setCategories((current) =>
      current.includes(category) ? current.filter((item) => item !== category) : [...current, category]
    );
  }

  function resetForm() {
    setName("");
    setCountry("");
    setCategories([]);
    setMonthlyRate("");
    setCurrency("USD");
    setStatus("active");
    setComplianceAgreement("");
    setContractRenewalDate("");
    setContactEmail("");
    setNotes("");
  }

  async function handleCreateSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    const numericRate = Number(monthlyRate);
    if (!name.trim() || !country || categories.length === 0 || !monthlyRate.trim()) {
      setFormError("Name, country, category, and monthly rate are required.");
      return;
    }
    if (!Number.isFinite(numericRate) || numericRate <= 0) {
      setFormError("Monthly rate must be greater than zero.");
      return;
    }

    setFormSubmitting(true);
    try {
      await apiRequest<Supplier>("/suppliers", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          country,
          categories,
          monthly_rate: numericRate,
          currency,
          status,
          compliance_agreement: complianceAgreement || null,
          contract_renewal_date: contractRenewalDate || null,
          contact_email: contactEmail || null,
          notes: notes || null,
        }),
      }, { authRequired: false });
      resetForm();
      setActionSuccess("Supplier created successfully.");
      await fetchSuppliers();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Unable to create supplier. Please try again.");
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleRateUpdate(supplier: Supplier) {
    const monthly_rate = Number(rateInputs[supplier.id]);
    if (!Number.isFinite(monthly_rate) || monthly_rate <= 0) {
      setListError("Monthly rate must be greater than zero.");
      return;
    }
    setUpdatingIds((current) => [...current, supplier.id]);
    try {
      const updated = await apiRequest<Supplier>(`/suppliers/${supplier.id}/rate`, {
        method: "PATCH",
        body: JSON.stringify({ monthly_rate }),
      }, { authRequired: false });
      setSuppliers((current) => current.map((item) => (item.id === supplier.id ? updated : item)));
      setRateInputs((current) => ({ ...current, [supplier.id]: String(updated.monthly_rate) }));
      setActionSuccess(`${supplier.name} monthly rate updated successfully.`);
    } catch {
      setListError("Unable to update the monthly rate. Please try again.");
    } finally {
      setUpdatingIds((current) => current.filter((id) => id !== supplier.id));
    }
  }

  async function handleStatusUpdate(supplierId: number, nextStatus: SupplierStatus) {
    setUpdatingIds((current) => [...current, supplierId]);
    try {
      const updated = await apiRequest<Supplier>(`/suppliers/${supplierId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      }, { authRequired: false });
      setSuppliers((current) => current.map((item) => (item.id === supplierId ? updated : item)));
      setActionSuccess(`${updated.name} status updated to ${updated.status}.`);
    } catch {
      setListError("Unable to update the status. Please try again.");
    } finally {
      setUpdatingIds((current) => current.filter((id) => id !== supplierId));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-teal-200 bg-teal-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">Supplier Directory</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">HealthCore supplier management</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">Manage contract costs, compliance agreements, and supplier status from one directory.</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Filters</h2>
        {actionSuccess ? <p role="status" className="mt-3 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{actionSuccess}</p> : null}
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-slate-700">Country
            <select value={countryFilter} onChange={(event) => setCountryFilter(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
              <option value="">All countries</option>
              {COUNTRY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label className="text-sm text-slate-700">Category
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
              <option value="">All categories</option>
              {CATEGORY_OPTIONS.map((option) => <option key={option} value={option}>{label(option)}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Register new supplier</h2>
        <form onSubmit={handleCreateSupplier} className="mt-4 grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-slate-700">Name<input value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" required /></label>
            <label className="text-sm text-slate-700">Country<select value={country} onChange={(event) => { const next = event.target.value as SupplierCountry; setCountry(next); setCurrency(next === "USA" ? "USD" : "GBP"); }} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" required><option value="">Select a country</option>{COUNTRY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-slate-700">Monthly rate<input value={monthlyRate} onChange={(event) => setMonthlyRate(event.target.value)} type="number" min="0" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" required /></label>
            <label className="text-sm text-slate-700">Currency<select value={currency} onChange={(event) => setCurrency(event.target.value as SupplierCurrency)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"><option value="USD">USD</option><option value="GBP">GBP</option></select></label>
          </div>
          <fieldset className="rounded-lg border border-slate-200 p-3"><legend className="px-1 text-sm font-medium text-slate-700">Categories</legend><div className="mt-2 grid gap-2 sm:grid-cols-2">{CATEGORY_OPTIONS.map((category) => <label key={category} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={categories.includes(category)} onChange={() => toggleCategory(category)} />{label(category)}</label>)}</div></fieldset>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-slate-700">Status<select value={status} onChange={(event) => setStatus(event.target.value as SupplierStatus)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"><option value="active">active</option><option value="suspended">suspended</option></select></label>
            <label className="text-sm text-slate-700">Compliance agreement<select value={complianceAgreement} onChange={(event) => setComplianceAgreement(event.target.value as ComplianceAgreement | "")} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"><option value="">Not applicable</option>{COMPLIANCE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-slate-700">Contract renewal date<input type="date" value={contractRenewalDate} onChange={(event) => setContractRenewalDate(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label><label className="text-sm text-slate-700">Contact email<input type="email" value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label></div>
          <label className="text-sm text-slate-700">Notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 min-h-20 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
          {formError ? <p className="text-sm text-rose-700">{formError}</p> : null}
          <button type="submit" disabled={formSubmitting} className="inline-flex w-fit items-center rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60">{formSubmitting ? "Saving..." : "Create supplier"}</button>
        </form>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Suppliers</h2>
        {listError ? <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700"><p>{listError}</p><button type="button" onClick={() => void fetchSuppliers()} className="rounded bg-rose-700 px-3 py-1 text-xs font-semibold text-white">Retry</button></div> : null}
        <div className="mt-4 overflow-x-auto"><table className="min-w-full text-sm"><thead className="text-left text-xs uppercase tracking-wide text-slate-500"><tr><th className="pb-2">Name</th><th className="pb-2">Country</th><th className="pb-2">Categories</th><th className="pb-2">Monthly rate</th><th className="pb-2">Compliance</th><th className="pb-2">Status</th><th className="pb-2">Updated at</th></tr></thead><tbody className="divide-y divide-slate-100 text-slate-700">
          {isLoading ? <tr><td className="py-4" colSpan={7}>Loading suppliers...</td></tr> : suppliers.length === 0 ? <tr><td className="py-4" colSpan={7}>No suppliers found for the selected filters.</td></tr> : suppliers.map((supplier) => { const isUpdating = updatingIds.includes(supplier.id); return <tr key={supplier.id}><td className="py-3 font-medium text-slate-900">{supplier.name}</td><td className="py-3">{supplier.country}</td><td className="py-3">{supplier.categories.map(label).join(", ")}</td><td className="py-3"><div className="flex items-center gap-2"><input className="w-24 rounded border border-slate-300 px-2 py-1" type="number" min="0" step="0.01" aria-label={`Monthly rate for ${supplier.name}`} value={rateInputs[supplier.id] ?? String(supplier.monthly_rate)} onChange={(event) => setRateInputs((current) => ({ ...current, [supplier.id]: event.target.value }))} /><span>{supplier.currency}</span><button className="rounded bg-slate-900 px-2 py-1 text-xs font-medium text-white disabled:opacity-60" onClick={() => void handleRateUpdate(supplier)} disabled={isUpdating}>Update</button></div></td><td className="py-3">{supplier.compliance_agreement ?? "Not applicable"}</td><td className="py-3"><div className="flex items-center gap-2"><span className={`rounded-full border px-2 py-1 text-xs font-semibold ${statusClasses(supplier.status)}`}>{supplier.status}</span><select className="rounded border border-slate-300 px-2 py-1" aria-label={`Status for ${supplier.name}`} value={supplier.status} onChange={(event) => void handleStatusUpdate(supplier.id, event.target.value as SupplierStatus)} disabled={isUpdating}><option value="active">active</option><option value="suspended">suspended</option></select></div></td><td className="py-3">{new Date(supplier.updated_at).toLocaleString()}</td></tr>; })}
        </tbody></table></div>
      </section>
    </main>
  );
}
