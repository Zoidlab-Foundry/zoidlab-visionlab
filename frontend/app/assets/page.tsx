"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

function fmtSize(n: number) {
  if (!n) return "—";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(2) + " MB";
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const load = () => {
    api.assets().then(setAssets).catch(() => {});
    api.projects().then(setProjects).catch(() => {});
  };
  useEffect(load, []);

  async function upload(files: FileList | null) {
    if (!files || !files.length) return;
    setErr(null);
    setBusy(true);
    try {
      for (const f of Array.from(files)) {
        if (!f.type.startsWith("image/")) { setErr(`${f.name}: not an image`); continue; }
        const dataUrl: string = await new Promise((res, rej) => {
          const rd = new FileReader();
          rd.onload = () => res(String(rd.result));
          rd.onerror = () => rej(new Error("read failed"));
          rd.readAsDataURL(f);
        });
        if (dataUrl.length > 12_000_000) { setErr(`${f.name}: too large (max ~9MB)`); continue; }
        await api.createAsset({ name: f.name, mime: f.type, data_url: dataUrl, project_id: projectId || null });
      }
      load();
    } catch (e: any) {
      setErr(e.message || "upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function del(id: string) {
    await api.deleteAsset(id).catch(() => {});
    load();
  }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Assets</h1>
          <p className="mt-1 text-[13px] text-dim">Upload the images you want to analyze. They’re stored to your account only and passed to the vision model at run time.</p>
        </div>
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
          className="rounded-lg border border-line bg-panel px-3 py-2 text-[13px] text-ink">
          <option value="">No project</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}
        onClick={() => fileRef.current?.click()}
        className={`mt-5 cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition ${drag ? "border-vi bg-vi/5" : "border-line bg-panel hover:border-vi/40"}`}
      >
        <div className="text-[15px] font-medium text-ink">{busy ? "Uploading…" : "Drop images here or click to browse"}</div>
        <div className="mt-1 text-[12px] text-faint">PNG · JPG · WEBP · GIF — up to ~9MB each</div>
        <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => upload(e.target.files)} />
      </div>
      {err && <div className="mt-3 rounded-lg border border-bad/30 bg-bad/5 px-4 py-2.5 text-[12.5px] text-bad">{err}</div>}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {assets.map((a) => (
          <div key={a.id} className="group overflow-hidden rounded-2xl border border-line bg-panel">
            <div className="aspect-video overflow-hidden bg-panel2">
              {/* thumbnail is fetched lazily with the data_url via single-asset endpoint */}
              <AssetThumb id={a.id} name={a.name} />
            </div>
            <div className="p-3">
              <div className="truncate text-[12.5px] font-medium text-ink" title={a.name}>{a.name}</div>
              <div className="mt-0.5 flex items-center justify-between text-[11px] text-faint">
                <span>{fmtSize(a.size_bytes)}</span>
                <button onClick={() => del(a.id)} className="text-faint opacity-0 transition group-hover:opacity-100 hover:text-bad">delete</button>
              </div>
              {(a.risk_flags || []).length > 0 && (
                <div className="mt-1.5 inline-flex rounded-full bg-warn/10 px-2 py-0.5 text-[10px] text-warn">⚠ {a.risk_flags.join(", ")}</div>
              )}
            </div>
          </div>
        ))}
        {!assets.length && !busy && (
          <div className="col-span-full rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">
            No assets yet. Upload an image to get started, then head to <Link href="/run" className="text-cy hover:underline">Run</Link>.
          </div>
        )}
      </div>
    </div>
  );
}

function AssetThumb({ id, name }: { id: string; name: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let ok = true;
    api.asset(id).then((a) => { if (ok) setSrc(a.data_url || null); }).catch(() => {});
    return () => { ok = false; };
  }, [id]);
  if (!src) return <div className="flex h-full w-full items-center justify-center text-[11px] text-faint">…</div>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={name} className="h-full w-full object-cover" />;
}
