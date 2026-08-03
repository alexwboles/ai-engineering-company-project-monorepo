"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiRequest } from "@/lib/api-client";

type MessageResponse = {
  message: string;
};

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);

    try {
      const result = await apiRequest<MessageResponse>(
        "/auth/forgot-password",
        {
          method: "POST",
          body: JSON.stringify({ email: email.trim() }),
        },
        { authRequired: false }
      );

      setSubmitted(true);
      setMessage(result.message || "If that address is registered, you will receive a reset link shortly.");
    } catch {
      setError("Unable to process your request right now. Please try again, or contact support if it continues.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">HealthCore Access</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Forgot password</h1>
        <p className="mt-2 text-sm text-slate-600">Enter your email and we will send a secure reset link.</p>

        <form className="mt-5 grid gap-4" onSubmit={onSubmit}>
          <label className="text-sm text-slate-700">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
              disabled={submitted || submitting}
            />
          </label>

          {error ? (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
              <p>{error}</p>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setError("")}
                  className="rounded bg-rose-700 px-3 py-1 text-white hover:bg-rose-800"
                >
                  Retry
                </button>
                <Link href="/login" className="underline underline-offset-2">
                  Back to login
                </Link>
              </div>
            </div>
          ) : null}
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

          <button
            type="submit"
            disabled={submitted || submitting}
            className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {submitted ? "Request sent" : submitting ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-600">
          Remembered it?{" "}
          <Link href="/login" className="font-semibold text-indigo-700 hover:text-indigo-800">
            Return to login
          </Link>
        </p>
      </section>
    </main>
  );
}
