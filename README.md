# ZoidLab VisionLab — Foundry Package 10

**AI Vision Lab.** Runs structured extraction and classification on your own images using
**real vision models** through the Nyquest relay: define a reusable vision task with an
extraction schema, point it at an uploaded image, and get structured JSON back with
confidence and risk flags.

Part of the [ZoidLab Foundry](https://foundry.zoidlab.ai). Requires **Nyquest Pro** (enforced
on both the Next middleware and every FastAPI data endpoint, fail-closed).

## What it does

- **Assets** — upload the images to analyze. Bytes live in object storage (MinIO), not the database.
- **Tasks** — reusable vision tasks: an instruction prompt plus an extraction schema
  (`{name, type, description}` fields) and a model choice.
- **Real vision runs** — a task runs against an asset through the relay, billed to the user's
  wallet. Output is structured JSON with confidence and risk flags.
- **Durable jobs** — a run is a **Celery background job** that moves `queued → running → done`
  and survives an API restart. The Runs page watches it to completion.
- **Runs** — every run with job status, structured output, confidence, tokens, and cost.

## Honesty

- Nothing is simulated. Every result comes from a real relay call against the uploaded image.
- No results exist until you launch a run (which spends real relay credits).
- Confidence and risk flags are the vision model's own assessment, not ground truth.
- With no relay key configured the run endpoint fails loudly rather than fabricating output.

## Stack

- **Backend**: FastAPI + **Postgres with per-tenant FORCE row-level security** (every query
  runs as the non-superuser `app_rls` role keyed on `app.current_owner`, so tenant isolation
  is enforced by the database, not by application code). **Celery + Redis** for durable run
  jobs; **MinIO** for image objects. Shared auth/relay/pricing come from `foundry-common`.
- **Frontend**: Next.js 15 + React 19 + Tailwind. Shared `zb_session` SSO + reusable Pro gate.
  Includes the in-app **Foundry Assistant** (Ask / Guide / Auto).
- **Deploy** (zoidberg): `visionlab-api` (:8704) + `visionlab-web` (:3704) + `visionlab-worker`
  behind the Cloudflare tunnel at `vision.zoidlab.ai`.

## Dev

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
NYQUEST_API_KEY=... .venv/bin/uvicorn main:app --port 8704
cd ../frontend && npm install && npm run dev   # proxies /api → 127.0.0.1:8704
```

Live: https://vision.zoidlab.ai
