"use client";

import { FormEvent, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api-client";

type KnowledgeResponse = { answer: string };

export default function KnowledgePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setError("Enter a question for the HealthCore knowledge assistant.");
      setAnswer(null);
      return;
    }

    setLoading(true);
    setError("");
    setAnswer(null);
    try {
      const response = await apiRequest<KnowledgeResponse>("/knowledge/query", {
        method: "POST",
        body: JSON.stringify({ question: trimmedQuestion }),
      });
      setAnswer(response.answer);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to query the knowledge base.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="rounded-2xl border border-teal-200 bg-teal-50 p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">HealthCore Digital</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Knowledge assistant</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
          Ask a commercial or operational question. The answer is grounded in HealthCore&apos;s approved operating,
          access, billing, workforce, and compliance documents.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="text-sm font-semibold text-slate-900" htmlFor="knowledge-question">
            Your question
          </label>
          <textarea
            className="min-h-32 rounded-xl border border-slate-300 bg-slate-50 p-3 text-sm text-slate-900 outline-none ring-teal-500 focus:ring-2"
            id="knowledge-question"
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="For example: What compliance rules apply when sharing patient data in the UK?"
            value={question}
          />
          <div className="flex items-center justify-between gap-4">
            <p className="text-xs text-slate-500">Answers use the HealthCore knowledge base only.</p>
            <button
              className="rounded-full bg-teal-700 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
              type="submit"
            >
              {loading ? "Searching..." : "Ask assistant"}
            </button>
          </div>
        </form>
      </section>

      {error ? (
        <section aria-live="polite" className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          {error}
        </section>
      ) : null}

      {answer ? (
        <section aria-live="polite" className="rounded-2xl border border-sky-200 bg-sky-50 p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">Answer</p>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-800">{answer}</p>
        </section>
      ) : null}
    </main>
  );
}
