async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}

export const api = {
  entitlements: () => req<any>("/api/auth/entitlements"),
  stats: () => req<any>("/api/stats"),
  meta: () => req<{ relay_available: boolean; billing_mode: string; vision_models: string[]; default_model: string }>("/api/meta"),

  projects: () => req<{ projects: any[] }>("/api/projects").then((d) => d.projects),
  createProject: (b: any) => req<any>("/api/projects", { method: "POST", body: JSON.stringify(b) }).then((d) => d.project),

  assets: (projectId?: string) => req<{ assets: any[] }>(`/api/assets${projectId ? `?project_id=${projectId}` : ""}`).then((d) => d.assets),
  asset: (id: string) => req<any>(`/api/assets/${id}`),
  createAsset: (b: any) => req<any>("/api/assets", { method: "POST", body: JSON.stringify(b) }).then((d) => d.asset),
  deleteAsset: (id: string) => req<any>(`/api/assets/${id}`, { method: "DELETE" }),

  tasks: () => req<{ tasks: any[] }>("/api/tasks").then((d) => d.tasks),
  task: (id: string) => req<any>(`/api/tasks/${id}`),
  createTask: (b: any) => req<any>("/api/tasks", { method: "POST", body: JSON.stringify(b) }).then((d) => d.task),
  deleteTask: (id: string) => req<any>(`/api/tasks/${id}`, { method: "DELETE" }),

  runTask: (b: { task_id: string; asset_id: string; model?: string }) => req<any>("/api/run", { method: "POST", body: JSON.stringify(b) }),
  runs: () => req<{ runs: any[] }>("/api/runs").then((d) => d.runs),
  getRun: (id: string) => req<any>(`/api/runs/${id}`),
  job: (id: string) => req<any>(`/api/jobs/${id}`),

  exportUrl: (tid: string) => `/api/tasks/${tid}/export`,
};

const TERMINAL = ["succeeded", "partial", "failed", "blocked", "timed_out", "cancelled", "interrupted"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Submit a durable job and poll it to completion, then return the finished run.
export async function runToCompletion(
  submit: () => Promise<any>,
  getRun: (id: string) => Promise<any>,
  onStatus?: (s: string) => void,
): Promise<any> {
  const sub = await submit();
  if (!sub?.job_id) return sub;                       // fallback: synchronous response
  let job = await api.job(sub.job_id);
  onStatus?.(job.status);
  let tries = 0;
  while (!TERMINAL.includes(job.status) && tries < 120) {
    await sleep(900);
    job = await api.job(sub.job_id);
    onStatus?.(job.status);
    tries++;
  }
  const run = await getRun(sub.run_id);
  return { ...run, _job: job };
}

export const usd = (n: number) => "$" + (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 });
export const ms = (n: number | null) => (n == null ? "—" : n >= 1000 ? (n / 1000).toFixed(2) + "s" : Math.round(n) + "ms");
export const num = (n: number) => (n ?? 0).toLocaleString();
export const pct = (n: number | null | undefined) => (n == null ? "—" : Math.round(n * 100) + "%");
