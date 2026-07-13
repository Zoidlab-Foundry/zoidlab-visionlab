# ZoidLab ModelBench — Foundry Package 08

**Model Benchmark Lab.** Answers *"which model wins on my actual workload?"* by running your
prompts across models on the **live Nyquest relay** and measuring speed, cost, and quality.

Part of the [ZoidLab Foundry](https://foundry.zoidlab.ai). Requires **Nyquest Pro** (enforced
on both the frontend gate and every backend data endpoint, fail-closed).

## What it does

- **Datasets** — prompt suites (seeded reasoning / coding / summarization sets, or your own).
- **Real benchmark runs** — each prompt runs against each selected model through the relay.
  Latency is wall-clock measured, tokens come from the relay's usage, cost is computed from the
  price table. A failed call is recorded as a failure; an unpriced model is flagged, not hidden.
- **Optional LLM-judge quality** — a judge model scores each answer 1–10, clearly labelled as
  a model's opinion, not ground truth.
- **Leaderboard** — per-model avg latency, success rate, cost, tokens, and (if judged) quality,
  aggregated across runs, with fastest / cheapest / best-quality winners.
- **Reports & export** — per-prompt outputs + a portable **Nyquest Benchmark Report** (JSON/YAML).

## Honesty

- Every number in a run is **measured** from a real relay call — nothing is estimated or seeded.
  No results exist until you run a benchmark (which spends real relay credits).
- Latency reflects relay conditions at run time and varies with load; the report says so.
- Quality scores are one judge model's opinion. Cost uses list prices (`pricing.py`).
- If no relay key is configured, the run endpoint returns `503 relay_unavailable` — it never
  fabricates benchmark numbers.

## Stack

- **Backend**: FastAPI + SQLite. `benchmark_engine.py` (real relay runs, measured), `llm.py`
  (relay client), `pricing.py` (cost from tokens). Runs execute in a FastAPI background task and
  are polled for completion.
- **Frontend**: Next.js 15 + React 19 + Tailwind. Shared `zb_session` SSO + reusable Pro gate.
- **Deploy** (zoidberg): `modelbench-api` (:8702) + `modelbench-web` (:3702) behind the Cloudflare
  tunnel at `modelbench.zoidlab.ai`.

## Dev

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
NYQUEST_API_KEY=... .venv/bin/uvicorn main:app --port 8702
cd ../frontend && npm install && npm run dev   # proxies /api → 127.0.0.1:8702
```
