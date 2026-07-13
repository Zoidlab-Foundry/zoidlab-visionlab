"""ZoidLab VisionLab API — Foundry Package 10, AI Vision Lab.

Real vision extraction through the Nyquest relay: upload an image asset, define a reusable
vision task + extraction schema, run it, and get structured output + confidence + risk flags.
Every data endpoint requires Nyquest Pro (backend fail-closed). Runs emit SpendGuard usage
and can preflight through TrustGate. NOTE: uses /api (platform-consistent) not /api/v1.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

import db_pg as db
import llm
import vision_engine
import exporter
import foundry
import jobs
import seed_vision
from tasks import run_vision
from auth import session, require_pro, relay_key, entitlement


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    jobs.init()
    interrupted = jobs.reconcile()
    if interrupted:
        print(f"[visionlab] reconciled {interrupted} interrupted job(s)")
    n = seed_vision.run()
    if n:
        print(f"[visionlab] seeded demo project + {n} tasks")
    yield


app = FastAPI(title="ZoidLab VisionLab API", lifespan=lifespan)


def require_owner(request: Request):
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email") if s else None, s.get("name") if s else None)
    return o


@app.get("/api/health")
def health():
    return {"ok": True, "service": "visionlab"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": s.get("sub"), "email": s.get("email"),
            "name": s.get("name"), "tier": s.get("tier")}


@app.get("/api/auth/entitlements")
def auth_entitlements(request: Request):
    return entitlement(request)


@app.get("/api/meta")
async def meta():
    try:
        models = await llm.featured_models()
    except Exception:
        models = ["auto"]
    return {"relay_available": llm.available(), "billing_mode": llm.billing_mode(),
            "vision_models": [m for m in models if any(h in m.lower() for h in ("gpt-4o", "gpt-5", "gemini", "claude"))] or models,
            "default_model": vision_engine.DEFAULT_MODEL}


@app.get("/api/stats")
def stats(request: Request, owner: str = Depends(require_owner)):
    return db.stats(owner)


# --- projects ---
class ProjectBody(BaseModel):
    name: str
    description: Optional[str] = ""
    risk_level: Optional[str] = "low"


@app.get("/api/projects")
def projects(request: Request, owner: str = Depends(require_owner)):
    return {"projects": db.list_projects(owner)}


@app.post("/api/projects")
def create_project(body: ProjectBody, owner: str = Depends(require_owner)):
    return {"ok": True, "project": db.create_project(body.model_dump(), owner)}


# --- assets ---
class AssetBody(BaseModel):
    project_id: Optional[str] = None
    name: Optional[str] = "asset"
    mime: Optional[str] = "image/png"
    data_url: str                     # base64 data URL of the image
    tags: Optional[list] = []


@app.get("/api/assets")
def assets(request: Request, project_id: Optional[str] = None, owner: str = Depends(require_owner)):
    return {"assets": db.list_assets(owner, project_id=project_id)}


@app.post("/api/assets")
def create_asset(body: AssetBody, owner: str = Depends(require_owner)):
    if not (body.data_url or "").startswith("data:image"):
        raise HTTPException(400, "data_url must be a base64 image data URL (data:image/...)")
    if len(body.data_url) > 12_000_000:
        raise HTTPException(413, "image too large (max ~9MB)")
    return {"ok": True, "asset": db.create_asset(body.model_dump(), owner)}


@app.get("/api/assets/{aid}")
def get_asset(aid: str, request: Request, owner: str = Depends(require_owner)):
    a = db.get_asset(aid, owner)
    if not a:
        raise HTTPException(404, "not_found")
    return a


@app.delete("/api/assets/{aid}")
def delete_asset(aid: str, owner: str = Depends(require_owner)):
    if not db.delete_asset(aid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- tasks ---
class TaskBody(BaseModel):
    name: str
    category: Optional[str] = "structured"
    description: Optional[str] = ""
    prompt: Optional[str] = ""
    schema_fields: List[dict] = []
    model: Optional[str] = "auto"


@app.get("/api/tasks")
def tasks(request: Request, owner: str = Depends(require_owner)):
    return {"tasks": db.list_tasks(owner)}


@app.get("/api/tasks/{tid}")
def get_task(tid: str, request: Request, owner: str = Depends(require_owner)):
    t = db.get_task(tid, owner)
    if not t:
        raise HTTPException(404, "not_found")
    return t


@app.post("/api/tasks")
def create_task(body: TaskBody, owner: str = Depends(require_owner)):
    return {"ok": True, "task": db.create_task(body.model_dump(), owner)}


@app.delete("/api/tasks/{tid}")
def delete_task(tid: str, owner: str = Depends(require_owner)):
    if not db.delete_task(tid, owner):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# --- run ---
class RunBody(BaseModel):
    task_id: str
    asset_id: str
    model: Optional[str] = None


@app.post("/api/run")
async def run_task(body: RunBody, request: Request, owner: str = Depends(require_owner)):
    task = db.get_task(body.task_id, owner)
    asset = db.get_asset(body.asset_id, owner, with_data=True)
    if not task:
        raise HTTPException(404, "task_not_found")
    if not asset:
        raise HTTPException(404, "asset_not_found")
    if not llm.available():
        raise HTTPException(503, "relay_unavailable: real vision needs a relay key")
    model = body.model or task.get("model") or vision_engine.DEFAULT_MODEL
    import uuid as _uuid
    corr = "corr_" + _uuid.uuid4().hex[:12]
    foundry.set_session(request.cookies.get("zb_session"))
    # TrustGate preflight (§6.4) — governs the vision action
    pf = await foundry.trustgate_preflight(
        {"prompt": task.get("prompt") or "", "model": model, "data_classification": "internal", "context_type": "vision"},
        correlation_id=corr)
    if pf.get("decision") in ("blocked",):
        rid = db.create_run(task, asset, model, owner, corr)
        db.finish_run(rid, {"status": "blocked", "error": "TrustGate blocked: " + "; ".join(pf.get("reasons") or [])})
        return db.get_run(rid, owner)
    rid = db.create_run(task, asset, model, owner, corr)
    rk = relay_key(request)
    job_id = jobs.create(owner, "vision_run", rid, timeout_s=150)
    async_res = run_vision.delay(job_id, rid, task["id"], asset["id"], model, owner, corr, rk,
                                 request.cookies.get("zb_session"))
    jobs.set_celery(job_id, owner, async_res.id)
    return {"job_id": job_id, "run_id": rid, "status": "queued", "run": db.get_run(rid, owner)}


# --- jobs ---
@app.get("/api/jobs/{jid}")
def get_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    j = jobs.get(jid, owner)
    if not j:
        raise HTTPException(404, "not_found")
    return j


@app.get("/api/jobs")
def list_jobs(request: Request, owner: str = Depends(require_owner)):
    return {"jobs": jobs.list_jobs(owner)}


@app.post("/api/jobs/{jid}/cancel")
def cancel_job(jid: str, request: Request, owner: str = Depends(require_owner)):
    return {"ok": jobs.cancel(jid, owner)}


@app.get("/api/runs")
def runs(request: Request, owner: str = Depends(require_owner)):
    return {"runs": db.list_runs(owner)}


@app.get("/api/runs/{rid}")
def get_run(rid: str, request: Request, owner: str = Depends(require_owner)):
    r = db.get_run(rid, owner)
    if not r:
        raise HTTPException(404, "not_found")
    return r


# --- export ---
@app.get("/api/tasks/{tid}/export")
def export_task(tid: str, request: Request, owner: str = Depends(require_owner)):
    t = db.get_task(tid, owner)
    if not t:
        raise HTTPException(404, "not_found")
    return exporter.to_package(t, owner=owner)
