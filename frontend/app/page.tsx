"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, num } from "../lib/api";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tnum text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-dim">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [s, setS] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    api.stats().then(setS).catch(() => {});
    api.runs().then((r) => setRuns(r.slice(0, 6))).catch(() => {});
    api.tasks().then(setTasks).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  return (
    <div className="relative py-8">
      <div className="hero-glow" />
      <div className="relative flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight">
            See, extract, <span className="prism-text">structure</span>.
          </h1>
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-dim">
            Turn images — invoices, menus, screenshots, diagrams — into structured, schema-shaped data.
            Every run is a real vision call through the live Nyquest relay, with confidence, evidence, and risk flags.
          </p>
        </div>
        <Link href="/run" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">
          Run a vision task →
        </Link>
      </div>

      {meta && (
        <div className={`relative mt-4 flex items-center gap-2 rounded-xl border px-4 py-2.5 text-[12.5px] ${meta.relay_available ? "border-ok/30 bg-ok/5 text-ok" : "border-warn/30 bg-warn/5 text-warn"}`}>
          <span className={`h-2 w-2 rounded-full ${meta.relay_available ? "bg-ok" : "bg-warn"}`} />
          {meta.relay_available
            ? <>Live relay connected — vision runs bill the <b>{meta.billing_mode}</b> wallet. Default model: <code className="text-ink">{meta.default_model}</code>.</>
            : <>Relay key not configured — real vision extraction is unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set.</>}
        </div>
      )}

      <div className="relative mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Assets" value={num(s?.assets ?? 0)} sub="uploaded images" />
        <Stat label="Tasks" value={num(s?.tasks ?? 0)} sub="extraction schemas" />
        <Stat label="Vision runs" value={num(s?.runs ?? 0)} sub="real relay calls" />
        <Stat label="Spend" value={usd(s?.spend_usd ?? 0)} sub="across all runs" />
      </div>

      <div className="relative mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Extraction tasks</h2>
            <Link href="/tasks" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {tasks.slice(0, 6).map((t) => (
              <Link key={t.id} href={`/run?task=${t.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{t.name}</div>
                  <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">{t.category}</span>
                </div>
                <div className="mt-0.5 text-[11px] text-faint">{(t.schema_fields || []).length} field(s) · {t.model}</div>
              </Link>
            ))}
            {!tasks.length && <p className="text-[12px] text-faint">No tasks yet. <Link href="/tasks" className="text-cy hover:underline">Create one</Link>.</p>}
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Recent runs</h2>
            <Link href="/runs" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {runs.map((r) => (
              <Link key={r.id} href={`/runs/${r.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{r.task_name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${r.status === "completed" ? "bg-ok/10 text-ok" : r.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn"}`}>{r.status}</span>
                </div>
                <div className="mt-0.5 text-[11px] text-faint">{r.asset_name} · {r.model?.split("/").pop()}</div>
              </Link>
            ))}
            {!runs.length && <p className="text-[12px] text-faint">No runs yet. <Link href="/run" className="text-cy hover:underline">Run a task</Link>.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
