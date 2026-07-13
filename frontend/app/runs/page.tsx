"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, usd, ms, pct } from "../../lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  useEffect(() => { api.runs().then(setRuns).catch(() => {}); }, []);

  return (
    <div className="py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[22px] font-semibold">Runs</h1>
          <p className="mt-1 text-[13px] text-dim">Every vision extraction you’ve run, with its status, cost, and confidence.</p>
        </div>
        <Link href="/run" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New run →</Link>
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-line bg-panel">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Asset</th>
              <th className="px-4 py-3 font-medium">Model</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Conf.</th>
              <th className="px-4 py-3 font-medium">Cost</th>
              <th className="px-4 py-3 font-medium">Latency</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-line/60 hover:bg-panel2/50">
                <td className="px-4 py-3"><Link href={`/runs/${r.id}`} className="font-medium text-ink hover:text-cy">{r.task_name}</Link></td>
                <td className="px-4 py-3 text-dim">{r.asset_name}</td>
                <td className="px-4 py-3 text-dim">{r.model?.split("/").pop()}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${r.status === "completed" ? "bg-ok/10 text-ok" : r.status === "failed" ? "bg-bad/10 text-bad" : "bg-warn/10 text-warn"}`}>{r.status}</span>
                </td>
                <td className="px-4 py-3 tnum text-dim">{pct(r.confidence)}</td>
                <td className="px-4 py-3 tnum text-dim">{usd(r.cost_usd || 0)}</td>
                <td className="px-4 py-3 tnum text-dim">{ms(r.latency_ms)}</td>
              </tr>
            ))}
            {!runs.length && <tr><td colSpan={7} className="px-4 py-10 text-center text-[13px] text-faint">No runs yet. <Link href="/run" className="text-cy hover:underline">Run a task</Link>.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
