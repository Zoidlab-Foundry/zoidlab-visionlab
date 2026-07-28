"""VisionLab assistant manifest — what the in-app assistant knows and may do.

This file is the assistant's security boundary: only the capabilities declared here exist
for it, and they execute through this app's own session-authed API (require_pro + RLS apply).
Delete-class operations and asset upload (multipart/base64) are intentionally not declared.
"""
from foundry_common.assistant import cap, page

MANIFEST = {
    "app": "VisionLab",
    "description": (
        "VisionLab runs structured extraction and classification on the user's own images "
        "using real vision models via the Nyquest relay: define a reusable vision task with "
        "an extraction schema, point it at an uploaded image asset, and get structured JSON "
        "output with confidence and risk flags. Nothing is simulated. Runs are DURABLE "
        "background jobs — starting one returns a job that moves queued → running → done "
        "and can be watched on the Runs page."
    ),
    "base_url": "http://127.0.0.1:8704",
    "pages": [
        page("/", "Dashboard", "Overview: stats, relay status, recent runs."),
        page("/assets", "Assets", "Upload and manage the images to analyze.",
             assists={"upload-asset": "the image upload drop zone"}),
        page("/tasks", "Tasks", "Create and manage reusable vision tasks with extraction schemas.",
             assists={"new-task": "the New task button"}),
        page("/run", "Run", "Pick a task and an asset, launch a vision run.",
             assists={"run-extraction": "the Run extraction button"}),
        page("/runs", "Runs", "Every vision run with job status, output, confidence, and cost."),
    ],
    "capabilities": [
        cap("stats", "GET", "/api/stats", risk="read",
            desc="Counts of projects/assets/tasks/runs for the user."),
        cap("list_projects", "GET", "/api/projects", risk="read",
            desc="The user's vision projects."),
        cap("list_assets", "GET", "/api/assets", risk="read",
            desc="The user's uploaded image assets (metadata only, no image data)."),
        cap("get_asset", "GET", "/api/assets/{aid}", risk="read",
            desc="One asset's metadata.", params={"aid": "asset id"}),
        cap("list_tasks", "GET", "/api/tasks", risk="read",
            desc="The user's reusable vision tasks with their extraction schemas."),
        cap("get_task", "GET", "/api/tasks/{tid}", risk="read",
            desc="One vision task: prompt, schema fields, model.", params={"tid": "task id"}),
        cap("list_runs", "GET", "/api/runs", risk="read",
            desc="The user's vision runs, newest first, with status and results."),
        cap("get_run", "GET", "/api/runs/{rid}", risk="read",
            desc="One run: structured output, confidence, risk flags, tokens, cost.",
            params={"rid": "run id"}),
        cap("list_jobs", "GET", "/api/jobs", risk="read",
            desc="The user's background jobs (vision runs) with queued/running/done status."),
        cap("get_job", "GET", "/api/jobs/{jid}", risk="read",
            desc="One background job's current status.", params={"jid": "job id"}),
        cap("create_task", "POST", "/api/tasks", risk="write",
            desc="Create a reusable vision task. schema_fields is a list of objects like "
                 "{'name': str, 'type': str, 'description': str} defining the extraction schema.",
            params={"name": "task name",
                    "category": "task category (default 'structured')",
                    "description": "short description",
                    "prompt": "instruction for the vision model",
                    "schema_fields": "list of extraction field objects",
                    "model": "vision model id (default 'auto')"}),
        cap("run_task", "POST", "/api/run", risk="write",
            desc="Run a vision task on an image asset through the real relay, billed to the "
                 "user's wallet. Starting a run returns a DURABLE background job "
                 "(queued → running → done) the user can watch on the Runs page. "
                 "Confirm task and asset with the user first.",
            params={"task_id": "task id", "asset_id": "asset id",
                    "model": "optional model override"}),
    ],
}
