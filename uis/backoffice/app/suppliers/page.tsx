"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api-client";

type SupplierStatus = "active" | "suspended";

type SupplierCategory =
  | "medical_equipment"
  | "pharmaceuticals"
  | "diagnostic_supplies"
  | "it_services"
  | "facility_services";

type Supplier = {
  id: number;
  name: string;
  country: string;
  product_categories: SupplierCategory[];
  rate: number;
  status: SupplierStatus;
  last_rate_update_date: string;
  updated_at: string;
};

const CATEGORY_OPTIONS: SupplierCategory[] = [
  "medical_equipment",
  "pharmaceuticals",
  "diagnostic_supplies",
  "it_services",
  "facility_services",
];

function statusClasses(status: SupplierStatus): string {
  return status === "active"
    ? "bg-emerald-100 text-emerald-800 border-emerald-200"
    : "bg-rose-100 text-rose-800 border-rose-200";
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [countryFilter, setCountryFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [listError, setListError] = useState("");

  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<SupplierCategory[]>([]);
  const [rate, setRate] = useState("");
  const [status, setStatus] = useState<SupplierStatus>("active");
  const [formError, setFormError] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);

  const [rateInputs, setRateInputs] = useState<Record<number, string>>({});
  const [updatingIds, setUpdatingIds] = useState<number[]>([]);

  const uniqueCountries = useMemo(() => {
    return Array.from(new Set(suppliers.map((supplier) => supplier.country))).sort();
  }, [suppliers]);

  async function fetchSuppliers() {
    setIsLoading(true);
    setListError("");

    const params = new URLSearchParams();
    if (countryFilter) {
      params.set("country", countryFilter);
    }
    if (categoryFilter) {
      params.set("category", categoryFilter);
    }

    try {
      const payload = await apiRequest<Supplier[]>(`/suppliers${params.toString() ? `?${params.toString()}` : ""}`);
      setSuppliers(payload);
      setRateInputs(
        payload.reduce<Record<number, string>>((acc, supplier) => {
          acc[supplier.id] = supplier.rate.toString();
          return acc;
        }, {})
      );
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

  function resetForm() {
    setName("");
    setCountry("");
    setSelectedCategories([]);
    setRate("");
    setStatus("active");
  }

  async function handleCreateSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");

    if (!name.trim() || !country.trim() || !rate.trim() || selectedCategories.length === 0) {
      setFormError("Name, country, category, and rate are required.");
      return;
    }

    const numericRate = Number(rate);
    if (!Number.isFinite(numericRate) || numericRate <= 0) {
      setFormError("Rate must be greater than zero.");
      return;
    }

    setFormSubmitting(true);

    try {
      await apiRequest<Supplier>("/suppliers", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          country: country.trim().toUpperCase(),
          product_categories: selectedCategories,
          rate: numericRate,
          status,
        }),
      });

      resetForm();
      await fetchSuppliers();
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setFormError(Object.values(error.fieldErrors)[0] ?? "Unable to create supplier. Please review your input.");
      } else {
        setFormError("Unable to create supplier. Please review your input and try again.");
      }
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleRateUpdate(supplierId: number) {
    const proposedRate = Number(rateInputs[supplierId]);
    if (!Number.isFinite(proposedRate) || proposedRate <= 0) {
      setListError("Rate must be greater than zero.");
      return;
    }

    setUpdatingIds((current) => [...current, supplierId]);

    try {
      const updated = await apiRequest<Supplier>(`/suppliers/${supplierId}/rate`, {
        method: "PATCH",
        body: JSON.stringify({ rate: proposedRate }),
      });
      setSuppliers((current) => current.map((item) => (item.id === supplierId ? updated : item)));
      setRateInputs((current) => ({ ...current, [supplierId]: updated.rate.toString() }));
    } catch {
      setListError("Unable to update the rate. Please try again.");
    } finally {
      setUpdatingIds((current) => current.filter((id) => id !== supplierId));
    }
  }

  async function handleStatusUpdate(supplierId: number, nextStatus: SupplierStatus) {
    setUpdatingIds((current) => [...current, supplierId]);

    try {
      const updated = await apiRequest<Supplier>(`/suppliers/${supplierId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      setSuppliers((current) => current.map((item) => (item.id === supplierId ? updated : item)));
    } catch {
      setListError("Unable to update the status. Please try again.");
    } finally {
      setUpdatingIds((current) => current.filter((id) => id !== supplierId));
    }
  }

  function toggleCategory(category: SupplierCategory) {
    setSelectedCategories((current) =>
      current.includes(category) ? current.filter((item) => item !== category) : [...current, category]
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-teal-200 bg-teal-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">Supplier Directory</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Procurement Management</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          Track supplier performance, availability status, and categories with real-time API updates.
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Filters</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-slate-700">
            Country
            <select
              value={countryFilter}
              onChange={(event) => setCountryFilter(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All countries</option>
              {uniqueCountries.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-slate-700">
            Product category
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All categories</option>
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Register New Supplier</h2>

        <form onSubmit={handleCreateSupplier} className="mt-4 grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm text-slate-700">
              Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                required
              />
            </label>

            <label className="text-sm text-slate-700">
              Country
              <input
                value={country}
                onChange={(event) => setCountry(event.target.value)}
                placeholder="US"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                required
              />
            </label>
          </div>

          <label className="text-sm text-slate-700">
            Rate
            <input
              value={rate}
              onChange={(event) => setRate(event.target.value)}
              type="number"
              min="0"
              step="0.1"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          <fieldset className="rounded-lg border border-slate-200 p-3">
            <legend className="px-1 text-sm font-medium text-slate-700">Product categories</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {CATEGORY_OPTIONS.map((category) => (
                <label key={category} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category)}
                    onChange={() => toggleCategory(category)}
                  />
                  {category.replaceAll("_", " ")}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="text-sm text-slate-700">
            Status
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value as SupplierStatus)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="active">active</option>
              <option value="suspended">suspended</option>
            </select>
          </label>

          {formError ? <p className="text-sm text-rose-700">{formError}</p> : null}

          <button
            type="submit"
            className="inline-flex w-fit items-center rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
            disabled={formSubmitting}
          >
            {formSubmitting ? "Saving..." : "Create supplier"}
          </button>
        </form>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Suppliers</h2>

        {listError ? (
          <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <p>{listError}</p>
            <button
              type="button"
              onClick={() => void fetchSuppliers()}
              className="rounded bg-rose-700 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-800"
            >
              Retry
            </button>
          </div>
        ) : null}

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-2">Name</th>
                <th className="pb-2">Country</th>
                <th className="pb-2">Categories</th>
                <th className="pb-2">Rate</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Last rate update</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {isLoading ? (
                <tr>
                  <td className="py-4" colSpan={6}>
                    Loading suppliers...
                  </td>
                </tr>
              ) : listError ? (
                <tr>
                  <td className="py-4" colSpan={6}>
                    Supplier data is unavailable until the request succeeds.
                  </td>
                </tr>
              ) : suppliers.length === 0 ? (
                <tr>
                  <td className="py-4" colSpan={6}>
                    No suppliers found for the selected filters.
                  </td>
                </tr>
              ) : (
                suppliers.map((supplier) => {
                  const isUpdating = updatingIds.includes(supplier.id);
                  return (
                    <tr key={supplier.id}>
                      <td className="py-3 font-medium text-slate-900">{supplier.name}</td>
                      <td className="py-3">{supplier.country}</td>
                      <td className="py-3">{supplier.product_categories?.join(", ").replaceAll("_", " ") ?? "—"}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <input
                            className="w-20 rounded border border-slate-300 px-2 py-1"
                            type="number"
                            min="0"
                            step="0.1"
                            aria-label={`Rate for ${supplier.name}`}
                            value={rateInputs[supplier.id] ?? supplier.rate.toString()}
                            onChange={(event) =>
                              setRateInputs((current) => ({
                                ...current,
                                [supplier.id]: event.target.value,
                              }))
                            }
                          />
                          <button
                            className="rounded bg-slate-900 px-2 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-60"
                            onClick={() => void handleRateUpdate(supplier.id)}
                            disabled={isUpdating}
                          >
                            Update
                          </button>
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${statusClasses(supplier.status)}`}>
                            {supplier.status}
                          </span>
                          <select
                            className="rounded border border-slate-300 px-2 py-1"
                            aria-label={`Status for ${supplier.name}`}
                            value={supplier.status}
                            onChange={(event) =>
                              void handleStatusUpdate(supplier.id, event.target.value as SupplierStatus)
                            }
                            disabled={isUpdating}
                          >
                            <option value="active">active</option>
                            <option value="suspended">suspended</option>
                          </select>
                        </div>
                      </td>
                      <td className="py-3">
                        {supplier.last_rate_update_date
                          ? new Date(supplier.last_rate_update_date).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
