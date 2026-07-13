"""Celery tasks for VisionLab — the real work runs here, in the worker process."""
import asyncio

from celery.exceptions import SoftTimeLimitExceeded

from celery_app import app
import db_pg as db
import vision_engine
import foundry
import jobs


@app.task(bind=True, name="visionlab.run_vision", max_retries=2,
          autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_jitter=True)
def run_vision(self, job_id, run_id, task_id, asset_id, model, owner, corr, relay_key, session_token):
    attempts = self.request.retries + 1
    jobs.mark_running(job_id, owner, attempts=attempts)
    db.set_run_status(run_id, "running", owner)
    try:
        task = db.get_task(task_id, owner)
        asset = db.get_asset(asset_id, owner, with_data=True)
        if not task or not asset:
            raise RuntimeError("task or asset not found for run")
        foundry.set_session(session_token)
        res = asyncio.run(vision_engine.run(task, asset, model, relay_key=relay_key))
        try:
            asyncio.run(foundry.emit_spend(res.get("usage"), resource_id=run_id, feature=task.get("name"),
                                           correlation_id=corr, environment="development"))
        except Exception:
            pass
        db.finish_run(run_id, res, owner)
        jobs.mark_terminal(job_id, owner, res)
        return {"status": res.get("status")}
    except SoftTimeLimitExceeded:
        db.finish_run(run_id, {"status": "failed", "error": "timed out (soft limit)"}, owner)
        jobs.mark(job_id, owner, "timed_out", "soft time limit exceeded")
        return {"status": "timed_out"}
    except Exception as e:
        if self.request.retries >= self.max_retries:
            db.finish_run(run_id, {"status": "failed", "error": str(e)[:400]}, owner)
            jobs.mark(job_id, owner, "failed", str(e)[:400], dead=True)
            return {"status": "failed"}
        raise
