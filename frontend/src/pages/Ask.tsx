import { useEffect, useRef, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { QueryResponse } from "../api/types";
import AnswerCard from "../components/AnswerCard";

const EXAMPLES = [
  "What is the total revenue by region?",
  "Show the monthly revenue trend",
  "Why did Q3 performance drop?",
  "What is the average salary by department?",
  "Show the monthly revenue trend and explain the Q3 dip",
];

interface Turn {
  id: number;
  question: string;
  response?: QueryResponse;
  error?: string;
  loading: boolean;
}

export default function Ask() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const busy = turns.some((t) => t.loading);

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [turns]);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const id = Date.now();
    const history = turns
      .filter((t) => t.response?.answerable)
      .slice(-3)
      .map((t) => ({ question: t.question, answer: t.response!.answer.slice(0, 4000) }));
    setTurns((ts) => [...ts, { id, question: q, loading: true }]);
    setQuestion("");
    try {
      const response = await api<QueryResponse>("/query", { body: { question: q, history } });
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, response, loading: false } : t)));
    } catch (err) {
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, error: err instanceof Error ? err.message : "Request failed", loading: false } : t)));
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(question);
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Ask your data</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Questions are routed to SQL, document, compute and chart agents. Every number is checked against the data.</p>
        </div>
        {turns.length > 0 && (
          <button type="button" className="btn-secondary" onClick={() => setTurns([])} disabled={busy}>New conversation</button>
        )}
      </div>

      {turns.length === 0 && (
        <div className="card mb-6">
          <p className="mb-3 text-sm font-medium">Try one of these:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((e) => (
              <button key={e} type="button" className="btn-secondary text-left" onClick={() => void ask(e)}>{e}</button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-6">
        {turns.map((t) => (
          <div key={t.id} className="space-y-3">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">{t.question}</div>
            </div>
            <div className="card">
              {t.loading && <p className="animate-pulse text-sm text-slate-500">Analyzing… planning steps, querying data and checking numbers.</p>}
              {t.error && <p className="error-text" role="alert">{t.error}</p>}
              {t.response && <AnswerCard response={t.response} />}
            </div>
          </div>
        ))}
        <div ref={bottom} />
      </div>

      <form onSubmit={onSubmit} className="sticky bottom-0 mt-6 flex gap-2 bg-slate-50 py-4 dark:bg-slate-950">
        <label htmlFor="question" className="sr-only">Question</label>
        <input
          id="question"
          className="input"
          placeholder="e.g. Which product category grew fastest in Q4?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={2000}
        />
        <button type="submit" className="btn shrink-0" disabled={busy || !question.trim()}>Ask</button>
      </form>
    </div>
  );
}
