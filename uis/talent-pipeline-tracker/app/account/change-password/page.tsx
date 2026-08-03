"use client";

import { FormEvent, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";

type MessageResponse = {
  message: string;
};

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    setSaving(true);

    try {
      const result = await apiRequest<MessageResponse>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });

      setMessage(result.message || "Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setError(requestError.message);
      } else {
        setError("Unable to change password right now.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-700">Account Security</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Change password</h1>
        <p className="mt-2 text-sm text-slate-600">Confirm your current password and set a new one.</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="grid gap-4" onSubmit={onSubmit}>
          <label className="text-sm text-slate-700">
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          <label className="text-sm text-slate-700">
            New password
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          <label className="text-sm text-slate-700">
            Confirm new password
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </label>

          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-60"
          >
            {saving ? "Saving..." : "Change password"}
          </button>
        </form>
      </section>
    </main>
  );
}
