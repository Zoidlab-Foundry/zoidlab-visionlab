"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, ms, pct } from "../../../lib/api";
import RunResult from "../../../components/RunResult";

export default function RunDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<any>(null);
  const [img, setImg] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.getRun(id).then((r) => {
      setRun(r);
      if (r.asset_id) api.asset(r.asset_id).then((a) => setImg(a.data_url)).catch(() => {});
    }).catch(() => setErr(true));
  }, [id]);

  if (err) return <div className="py-10 text-[13px] text-faint">Run not found. <Link href="/runs" className="text-cy hover:underline">Back to runs</Link>.</div>;
  if (!run) return <div className="py-10 text-[13px] text-dim">Loading…</div>;

  return (
    <div className="py-8">
      <Link href="/runs" className="text-[12px] text-dim hover:text-ink">← Runs</Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">{run.task_name}</h1>
          <div className="mt-1 text-[12px] text-faint">{run.asset_name} · {run.model} · {run.created_at?.slice(0, 19).replace("T", " ")}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[12px]">
          <span className={`rounded-full px-2.5 py-1 font-medium ${run.status === "completed" ? "bg-ok/10 text-ok" : run.status === "blocked" ? "bg-warn/10 text-warn" : "bg-bad/10 text-bad"}`}>{run.status}</span>
          {run.confidence != null && <span className="text-dim">conf {pct(run.confidence)}</span>}
          {run.cost_usd != null && <span className="text-dim">· {usd(run.cost_usd)}</span>}
          {run.latency_ms != null && <span className="text-dim">· {ms(run.latency_ms)}</span>}
        </div>
      </div>

      {(run.risk_flags || []).length > 0 && (
        <div className="mt-3 inline-flex rounded-full bg-warn/10 px-3 py-1 text-[12px] text-warn">⚠ {run.risk_flags.join(", ")}</div>
      )}

      {img && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-line bg-panel2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={img} alt={run.asset_name} className="mx-auto max-h-[320px] object-contain" />
        </div>
      )}

      <div className="mt-4">
        <RunResult run={run} />
      </div>

      <details className="mt-4 rounded-2xl border border-line bg-panel p-4">
        <summary className="cursor-pointer text-[12.5px] text-dim">Token & correlation detail</summary>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-dim sm:grid-cols-4">
          <div><div className="text-faint">Prompt tokens</div><div className="tnum text-ink">{run.prompt_tokens ?? "—"}</div></div>
          <div><div className="text-faint">Completion tokens</div><div className="tnum text-ink">{run.completion_tokens ?? "—"}</div></div>
          <div><div className="text-faint">Total tokens</div><div className="tnum text-ink">{run.total_tokens ?? "—"}</div></div>
          <div><div className="text-faint">Correlation</div><div className="truncate font-mono text-[11px] text-ink" title={run.correlation_id}>{run.correlation_id || "—"}</div></div>
        </div>
      </details>
    </div>
  );
}
