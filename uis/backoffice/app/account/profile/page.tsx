"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api-client";

type Profile = {
  id: number;
  user_id: number;
  name: string;
  phone: string;
  address: string;
};

type AuthMeResponse = {
  email: string;
  role: "admin" | "manager" | "user";
  profile: Profile | null;
};

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const me = await apiRequest<AuthMeResponse>("/auth/me");
      setEmail(me.email ?? "");
      setRole(me.role ?? "");
      setForm({
        name: me.profile?.name ?? "",
        phone: me.profile?.phone ?? "",
        address: me.profile?.address ?? "",
      });
    } catch {
      setError("Unable to load your profile right now.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      await apiRequest<Profile>("/profiles/me", {
        method: "PUT",
        body: JSON.stringify({
          name: form.name,
          phone: form.phone,
          address: form.address,
        }),
      });

      setMessage("Profile updated successfully.");
    } catch (requestError) {
      if (requestError instanceof ApiError && Object.keys(requestError.fieldErrors).length > 0) {
        setError(Object.values(requestError.fieldErrors)[0] ?? "Unable to update profile.");
      } else {
        setError("Unable to update your profile. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">Account Management</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Profile</h1>
        <p className="mt-2 text-sm text-slate-600">Update your profile details linked to your authenticated user account.</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {loading ? (
          <p className="text-sm text-slate-600">Loading profile...</p>
        ) : error && !email ? (
          <div className="flex flex-wrap items-center gap-3 text-sm text-rose-700">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => void load()}
              className="rounded bg-rose-700 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-800"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Email</dt>
                <dd className="font-medium text-slate-900">{email || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Role</dt>
                <dd className="font-medium text-slate-900">{role || "—"}</dd>
              </div>
            </dl>

            <form className="mt-5 grid gap-4" onSubmit={onSubmit}>
              <label className="text-sm text-slate-700">
                Name
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>

              <label className="text-sm text-slate-700">
                Phone
                <input
                  value={form.phone}
                  onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>

              <label className="text-sm text-slate-700">
                Address
                <input
                  value={form.address}
                  onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>

              {error ? <p className="text-sm text-rose-700">{error}</p> : null}
              {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
              >
                {saving ? "Saving..." : "Save profile"}
              </button>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
