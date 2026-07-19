"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

/* In-app guide: what VisionLab is and how to run your first extraction.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "vl_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Upload your images",
    body: "Head to Assets and drag in the images you want to analyze — invoices, menus, screenshots, diagrams (PNG, JPG, WEBP, GIF up to ~9MB). They're stored to your account only and optionally filed under a project.",
  },
  {
    title: "Define an extraction task",
    body: "On Tasks, click New Task. A task is a reusable recipe: an instruction prompt plus a schema of typed fields (string, number, currency, date…) you want pulled out of every image. Pick a vision model or leave it on Auto.",
  },
  {
    title: "Run it on the live relay",
    body: "On Run, pick a task and an asset. The image goes to a real vision model through the Nyquest relay as a durable background job (queued → running → done) — every run is a real API call, billed to your own Nyquest wallet.",
  },
  {
    title: "Read the structured result",
    body: "The result comes back schema-shaped: your fields filled in, plus a confidence score, evidence quotes from the image, and risk flags — alongside measured cost, latency, and token counts.",
  },
  {
    title: "Track every run",
    body: "Runs lists every extraction you own with status, confidence, cost, and latency. Drill into any run for the original image, the full result, and token & correlation detail for auditing.",
  },
  {
    title: "Export the recipe",
    body: "Any task exports as a portable package (Export package) — share the prompt-plus-schema recipe with your team or version it alongside your code.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the VisionLab guide"
      >
        Guide
      </button>
      {open && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="VisionLab guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">⦿</span>
              <h2 className="text-[16px] font-semibold">How VisionLab works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Turn images into structured, schema-shaped data — real vision calls with confidence, evidence, and risk flags. Six steps from image to answer:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-black hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
