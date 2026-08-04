"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api-client";
import { storeToken } from "@/lib/auth-client";
import { track } from "@/lib/telemetry";

type LoginResponse = {
  access_token: string;
  token_type: string;
};

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const successMessage = searchParams.get("reset") === "success" ? "Password updated. You can sign in now." : "";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    track("auth_login_attempted", {
      authMethod: "password",
      clientApp: "backoffice",
      authProvider: "healthcore_api",
      mfaUsed: false,
    });

    try {
      const result = await apiRequest<LoginResponse>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ email: email.trim(), password }),
        },
        { authRequired: false }
      );

      storeToken(result.access_token);
      router.replace("/");
    } catch (requestError) {
      track("auth_login_failed", {
        authMethod: "password",
        clientApp: "backoffice",
        failureReason: requestError instanceof ApiError && requestError.status === 401 ? "invalid_credentials" : "network_error",
        lockoutTriggered: false,
        attemptCount: 1,
      });

      if (requestError instanceof ApiError && requestError.status === 401) {
        setError("Invalid email or password. Please try again.");
      } else {
        setError("Unable to sign in right now. Please try again, or contact support if the problem continues.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">HealthCore Access</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Login</h1>
        {successMessage ? <p className="mt-3 text-sm text-emerald-700">{successMessage}</p> : null}

        <form className="mt-5 grid gap-4" onSubmit={onSubmit}>
          <label className="text-sm text-slate-700">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          <label className="text-sm text-slate-700">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          <p className="-mt-1 text-right text-sm">
            <Link href="/forgot-password" className="font-medium text-indigo-700 hover:text-indigo-800">
              Forgot your password?
            </Link>
          </p>

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
                <Link href="/forgot-password" className="underline underline-offset-2">
                  Reset password
                </Link>
              </div>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-600">
          Need an account?{" "}
          <Link href="/register" className="font-semibold text-indigo-700 hover:text-indigo-800">
            Register
          </Link>
        </p>
      </section>
    </main>
  );
}
