"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, usd, ms, pct, runToCompletion } from "../../lib/api";
import RunResult from "../../components/RunResult";

function RunInner() {
  const params = useSearchParams();
  const [tasks, setTasks] = useState<any[]>([]);
  const [assets, setAssets] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [taskId, setTaskId] = useState(params.get("task") || "");
  const [assetId, setAssetId] = useState("");
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.tasks().then(setTasks).catch(() => {});
    api.assets().then(setAssets).catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, []);

  const task = tasks.find((t) => t.id === taskId);
  const asset = assets.find((a) => a.id === assetId);

  async function run() {
    if (!taskId || !assetId) return;
    setRunning(true); setErr(null); setResult(null); setPhase("queued");
    try {
      const r = await runToCompletion(
        () => api.runTask({ task_id: taskId, asset_id: assetId }),
        (rid) => api.getRun(rid),
        (s) => setPhase(s),
      );
      setResult(r);
    } catch (e: any) {
      setErr(e.message || "run failed");
    } finally { setRunning(false); setPhase(null); }
  }

  return (
    <div className="py-8">
      <h1 className="text-[22px] font-semibold">Run a vision task</h1>
      <p className="mt-1 text-[13px] text-dim">Pick an extraction task and an image. The image is sent to the vision model on the live relay and the structured result comes back below.</p>

      {meta && !meta.relay_available && (
        <div className="mt-4 rounded-xl border border-warn/30 bg-warn/5 px-4 py-2.5 text-[12.5px] text-warn">
          Relay key not configured — real vision runs are unavailable until <code className="text-ink">NYQUEST_API_KEY</code> is set on the server.
        </div>
      )}

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <label className="block">
            <span className="text-[12px] text-dim">Task</span>
            <select value={taskId} onChange={(e) => setTaskId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50">
              <option value="">Select a task…</option>
              {tasks.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          {task && (
            <div className="mt-2 rounded-lg border border-line bg-panel2 p-3 text-[12px] text-dim">
              <div className="text-[11px] uppercase tracking-wider text-faint">{task.category} · {task.model}</div>
              {task.prompt && <p className="mt-1">{task.prompt}</p>}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(task.schema_fields || []).map((f: any) => (
                  <span key={f.name} className="rounded-md border border-line px-1.5 py-0.5 text-[10.5px]">{f.name} <span className="text-faint">· {f.type}</span></span>
                ))}
              </div>
            </div>
          )}

          <label className="mt-4 block">
            <span className="text-[12px] text-dim">Image asset</span>
            <select value={assetId} onChange={(e) => setAssetId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50">
              <option value="">Select an asset…</option>
              {assets.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          {!assets.length && <p className="mt-2 text-[12px] text-faint">No assets yet — <Link href="/assets" className="text-cy hover:underline">upload one</Link> first.</p>}

          <button onClick={run} disabled={running || !taskId || !assetId}
            className="mt-5 w-full rounded-lg bg-vi px-4 py-2.5 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
            {running ? (phase === "running" ? "Running vision model…" : phase === "queued" ? "Queued…" : "Working…") : "Run extraction →"}
          </button>
          {err && <div className="mt-3 rounded-lg border border-bad/30 bg-bad/5 px-3 py-2 text-[12.5px] text-bad">{err}</div>}
        </div>

        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="text-[12px] uppercase tracking-wider text-faint">Preview</div>
          <div className="mt-2 aspect-video overflow-hidden rounded-lg border border-line bg-panel2">
            {asset ? <Preview id={asset.id} /> : <div className="flex h-full items-center justify-center text-[12px] text-faint">Select an asset to preview</div>}
          </div>
        </div>
      </div>

      {result && (
        <div className="mt-6">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-[12px]">
            <span className={`rounded-full px-2.5 py-1 font-medium ${result.status === "completed" ? "bg-ok/10 text-ok" : result.status === "blocked" ? "bg-warn/10 text-warn" : "bg-bad/10 text-bad"}`}>{result.status}</span>
            {result.confidence != null && <span className="text-dim">confidence {pct(result.confidence)}</span>}
            {result.cost_usd != null && <span className="text-dim">· {usd(result.cost_usd)}</span>}
            {result.latency_ms != null && <span className="text-dim">· {ms(result.latency_ms)}</span>}
            {(result.risk_flags || []).length > 0 && <span className="rounded-full bg-warn/10 px-2 py-0.5 text-warn">⚠ {result.risk_flags.join(", ")}</span>}
          </div>
          <RunResult run={result} />
        </div>
      )}
    </div>
  );
}

function Preview({ id }: { id: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => { let ok = true; api.asset(id).then((a) => ok && setSrc(a.data_url)).catch(() => {}); return () => { ok = false; }; }, [id]);
  if (!src) return <div className="flex h-full items-center justify-center text-[12px] text-faint">…</div>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="asset" className="h-full w-full object-contain" />;
}

export default function RunPage() {
  return <Suspense fallback={<div className="py-8 text-[13px] text-dim">Loading…</div>}><RunInner /></Suspense>;
}
