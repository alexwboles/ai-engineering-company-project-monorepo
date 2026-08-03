"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { authApiRequest, AuthApiError, storeToken } from "@/lib/auth-client";

type TokenResponse = {
  access_token: string;
  token_type: string;
};

type UserResponse = {
  id: number;
  email: string;
  is_active: boolean;
  role: "admin" | "manager" | "user";
  created_at: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    phone: "",
    address: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setFormError("");
    setSubmitting(true);

    try {
      try {
        await authApiRequest<UserResponse>("/users", {
          method: "POST",
          body: JSON.stringify({
            email: form.email.trim(),
            password: form.password,
            name: form.name.trim() || undefined,
            phone: form.phone.trim() || undefined,
            address: form.address.trim() || undefined,
          }),
        });
      } catch (registerError) {
        if (registerError instanceof AuthApiError) {
          setFieldErrors(registerError.fieldErrors);
        }
        setFormError("Unable to create your account. Please review your details and try again.");
        return;
      }

      try {
        const loginResult = await authApiRequest<TokenResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: form.email.trim(), password: form.password }),
        });

        storeToken(loginResult.access_token);
        router.replace("/");
      } catch {
        setFormError("Account created, but automatic sign-in failed. Please sign in from the login page.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">HealthCore Access</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Register</h1>

        <form className="mt-5 grid gap-4" onSubmit={onSubmit}>
          <label className="text-sm text-slate-700">
            Email
            <input
              type="email"
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
            {fieldErrors.email ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.email}</span> : null}
          </label>

          <label className="text-sm text-slate-700">
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
            {fieldErrors.password ? <span className="mt-1 block text-xs text-rose-700">{fieldErrors.password}</span> : null}
          </label>

          <label className="text-sm text-slate-700">
            Name (optional)
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="text-sm text-slate-700">
            Phone (optional)
            <input
              value={form.phone}
              onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="text-sm text-slate-700">
            Address (optional)
            <input
              value={form.address}
              onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>

          {formError ? <p className="text-sm text-rose-700">{formError}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60"
          >
            {submitting ? "Registering..." : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-cyan-700 hover:text-cyan-800">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
