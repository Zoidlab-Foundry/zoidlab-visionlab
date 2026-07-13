"use client";

function renderVal(v: any): string {
  if (v == null) return "—";
  if (typeof v === "object") return JSON.stringify(v, null, 2);
  return String(v);
}

export default function RunResult({ run }: { run: any }) {
  const structured = run.structured || {};
  const keys = Object.keys(structured);

  if (run.status === "blocked") {
    return (
      <div className="rounded-2xl border border-warn/30 bg-warn/5 p-5 text-[13px] text-warn">
        <div className="font-semibold">Blocked by TrustGate policy</div>
        {run.error && <p className="mt-1 text-[12.5px]">{run.error}</p>}
      </div>
    );
  }
  if (run.status === "failed") {
    return (
      <div className="rounded-2xl border border-bad/30 bg-bad/5 p-5 text-[13px] text-bad">
        <div className="font-semibold">Run failed</div>
        {run.error && <p className="mt-1 text-[12.5px]">{run.error}</p>}
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <div className="rounded-2xl border border-line bg-panel p-5">
        <div className="text-[12px] uppercase tracking-wider text-faint">Summary</div>
        <p className="mt-2 text-[13.5px] leading-relaxed text-ink">{run.summary || "—"}</p>
        {(run.evidence || []).length > 0 && (
          <div className="mt-4">
            <div className="text-[12px] uppercase tracking-wider text-faint">Evidence</div>
            <ul className="mt-2 space-y-1">
              {run.evidence.map((e: string, i: number) => (
                <li key={i} className="flex gap-2 text-[12.5px] text-dim"><span className="text-vi">›</span><span>{e}</span></li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-line bg-panel p-5">
        <div className="text-[12px] uppercase tracking-wider text-faint">Structured fields</div>
        {keys.length ? (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-[12.5px]">
              <tbody>
                {keys.map((k) => (
                  <tr key={k} className="border-t border-line/60 align-top">
                    <td className="w-32 py-2 pr-3 font-medium text-dim">{k}</td>
                    <td className="py-2 font-mono text-[12px] text-ink"><pre className="whitespace-pre-wrap break-words">{renderVal(structured[k])}</pre></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-2 text-[12.5px] text-faint">No structured fields returned.</p>
        )}
      </div>
    </div>
  );
}
