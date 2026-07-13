"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

type Field = { name: string; type: string; description: string };
const TYPES = ["string", "number", "currency", "date", "boolean", "array", "object"];

export default function TasksPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("structured");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("auto");
  const [fields, setFields] = useState<Field[]>([{ name: "", type: "string", description: "" }]);

  const load = () => api.tasks().then(setTasks).catch(() => {});
  useEffect(() => { load(); api.meta().then(setMeta).catch(() => {}); }, []);

  function reset() {
    setName(""); setCategory("structured"); setPrompt(""); setModel("auto");
    setFields([{ name: "", type: "string", description: "" }]);
  }

  async function save() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await api.createTask({
        name: name.trim(), category, prompt, model,
        schema_fields: fields.filter((f) => f.name.trim()).map((f) => ({ ...f, name: f.name.trim() })),
      });
      setOpen(false); reset(); load();
    } finally { setSaving(false); }
  }

  async function del(id: string) { await api.deleteTask(id).catch(() => {}); load(); }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Tasks</h1>
          <p className="mt-1 text-[13px] text-dim">A task is a reusable extraction recipe — a prompt plus the schema of fields you want pulled out of every image.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New task</button>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {tasks.map((t) => (
          <div key={t.id} className="rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[14px] font-semibold text-ink">{t.name}</div>
                <div className="mt-0.5 text-[11px] text-faint">{t.category} · {t.model}</div>
              </div>
              <span className="rounded-full bg-vi/10 px-2 py-0.5 text-[10.5px] text-vi">{(t.schema_fields || []).length} fields</span>
            </div>
            {t.prompt && <p className="mt-2 line-clamp-2 text-[12px] text-dim">{t.prompt}</p>}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(t.schema_fields || []).slice(0, 8).map((f: Field) => (
                <span key={f.name} className="rounded-md border border-line px-1.5 py-0.5 text-[10.5px] text-dim">{f.name}<span className="text-faint"> · {f.type}</span></span>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-3 text-[12px]">
              <Link href={`/run?task=${t.id}`} className="font-medium text-cy hover:underline">Run →</Link>
              <a href={api.exportUrl(t.id)} target="_blank" className="text-dim hover:text-ink">Export package</a>
              <button onClick={() => del(t.id)} className="ml-auto text-faint hover:text-bad">delete</button>
            </div>
          </div>
        ))}
        {!tasks.length && <div className="md:col-span-2 rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">No tasks yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm">
          <div className="mt-10 w-full max-w-2xl rounded-2xl border border-line bg-panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">New extraction task</h2>
              <button onClick={() => setOpen(false)} className="text-faint hover:text-ink">✕</button>
            </div>
            <div className="mt-4 grid gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="text-[12px] text-dim">Name</span>
                  <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Receipt totals"
                    className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50" />
                </label>
                <label className="block">
                  <span className="text-[12px] text-dim">Category</span>
                  <input value={category} onChange={(e) => setCategory(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50" />
                </label>
              </div>
              <label className="block">
                <span className="text-[12px] text-dim">Prompt / instruction</span>
                <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={2} placeholder="What should the model look for and extract?"
                  className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50" />
              </label>
              <label className="block">
                <span className="text-[12px] text-dim">Model</span>
                <select value={model} onChange={(e) => setModel(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50">
                  <option value="auto">Auto ({meta?.default_model || "default"})</option>
                  {(meta?.vision_models || []).map((m: string) => <option key={m} value={m}>{m}</option>)}
                </select>
              </label>

              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-dim">Extraction schema</span>
                  <button onClick={() => setFields([...fields, { name: "", type: "string", description: "" }])} className="text-[12px] text-cy hover:underline">+ field</button>
                </div>
                <div className="mt-2 space-y-2">
                  {fields.map((f, i) => (
                    <div key={i} className="flex gap-2">
                      <input value={f.name} onChange={(e) => setFields(fields.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} placeholder="field name"
                        className="w-40 rounded-lg border border-line bg-panel2 px-2.5 py-1.5 text-[12.5px] text-ink outline-none focus:border-vi/50" />
                      <select value={f.type} onChange={(e) => setFields(fields.map((x, j) => j === i ? { ...x, type: e.target.value } : x))}
                        className="rounded-lg border border-line bg-panel2 px-2 py-1.5 text-[12.5px] text-ink outline-none focus:border-vi/50">
                        {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <input value={f.description} onChange={(e) => setFields(fields.map((x, j) => j === i ? { ...x, description: e.target.value } : x))} placeholder="description (optional)"
                        className="flex-1 rounded-lg border border-line bg-panel2 px-2.5 py-1.5 text-[12.5px] text-ink outline-none focus:border-vi/50" />
                      <button onClick={() => setFields(fields.filter((_, j) => j !== i))} className="px-1 text-faint hover:text-bad">✕</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={save} disabled={saving || !name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                {saving ? "Saving…" : "Create task"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
