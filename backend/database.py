"""SQLite persistence for ZoidLab VisionLab (Foundry Package 10 — AI Vision Lab).

MVP vertical slice on the shared platform architecture: projects, assets (image bytes
stored as base64 for real relay-vision calls), reusable vision tasks + extraction schemas,
and runs with structured output + evidence. Owner = Nyquest user id; seed (owner NULL) is
shared. Real vision extraction goes through the Nyquest relay (llm.py); costs are computed
from real token usage.
"""
import os
import json
import uuid
import hashlib
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "visionlab.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, d=None):
    try:
        return json.loads(v) if v is not None else d
    except Exception:
        return d


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS vision_projects (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
                status TEXT DEFAULT 'active', risk_level TEXT DEFAULT 'low', created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_vp_owner ON vision_projects(owner_user_id);
            CREATE TABLE IF NOT EXISTS vision_assets (
                id TEXT PRIMARY KEY, owner_user_id TEXT, project_id TEXT, name TEXT, mime TEXT, kind TEXT DEFAULT 'image',
                data_url TEXT, sha256 TEXT, size_bytes INTEGER, risk_flags TEXT, tags TEXT, created_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_va_owner ON vision_assets(owner_user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_va_project ON vision_assets(project_id);
            CREATE TABLE IF NOT EXISTS vision_tasks (
                id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, category TEXT,
                description TEXT, prompt TEXT, schema_fields TEXT, model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0',
                created_at TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_vt_owner ON vision_tasks(owner_user_id);
            CREATE TABLE IF NOT EXISTS vision_runs (
                id TEXT PRIMARY KEY, owner_user_id TEXT, task_id TEXT, task_name TEXT, asset_id TEXT, asset_name TEXT,
                model TEXT, status TEXT DEFAULT 'queued', summary TEXT, structured TEXT, evidence TEXT, confidence REAL,
                prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER, cost_usd REAL, latency_ms INTEGER,
                risk_flags TEXT, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_vr_owner ON vision_runs(owner_user_id, created_at);
            """
        )


def _vis(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


# --- projects ---
def list_projects(v=None):
    with _conn() as c:
        rows = c.execute(f"""SELECT p.*, (SELECT COUNT(*) FROM vision_assets a WHERE a.project_id=p.id) assets
                             FROM vision_projects p WHERE {_vis()} ORDER BY p.updated_at DESC""", (v,)).fetchall()
    return [dict(r) for r in rows]


def get_project(pid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM vision_projects WHERE id=? AND {_vis()}", (pid, v)).fetchone()
    return dict(r) if r else None


def create_project(d, owner):
    pid = new_id("vproj"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO vision_projects (id,owner_user_id,name,slug,description,status,risk_level,created_at,updated_at)
                     VALUES (?,?,?,?,?,'active',?,?,?)""",
                  (pid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("risk_level", "low"), now, now))
    return get_project(pid, owner)


# --- assets ---
def create_asset(d, owner):
    aid = new_id("asset"); now = now_iso()
    data_url = d.get("data_url") or ""
    raw = data_url.split(",", 1)[1] if "," in data_url else data_url
    sha = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:32] if raw else ""
    size = int(len(raw) * 3 / 4) if raw else 0
    with _conn() as c:
        c.execute("""INSERT INTO vision_assets (id,owner_user_id,project_id,name,mime,kind,data_url,sha256,size_bytes,risk_flags,tags,created_at)
                     VALUES (?,?,?,?,?,'image',?,?,?,?,?,?)""",
                  (aid, owner, d.get("project_id"), d.get("name", "asset"), d.get("mime", "image/png"),
                   data_url, sha, size, _j(d.get("risk_flags", [])), _j(d.get("tags", [])), now))
    return get_asset(aid, owner, with_data=False)


def get_asset(aid, v=None, with_data=True):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM vision_assets WHERE id=? AND {_vis()}", (aid, v)).fetchone()
    if not r:
        return None
    d = dict(r); d["risk_flags"] = _pj(d.get("risk_flags"), []); d["tags"] = _pj(d.get("tags"), [])
    if not with_data:
        d.pop("data_url", None)
    return d


def list_assets(v=None, project_id=None, limit=200):
    q = f"""SELECT id,owner_user_id,project_id,name,mime,kind,sha256,size_bytes,risk_flags,tags,created_at
            FROM vision_assets WHERE {_vis()}"""
    args = [v]
    if project_id and project_id != "all":
        q += " AND project_id=?"; args.append(project_id)
    q += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["risk_flags"] = _pj(d.get("risk_flags"), []); d["tags"] = _pj(d.get("tags"), []); out.append(d)
    return out


def delete_asset(aid, owner):
    a = get_asset(aid, owner, with_data=False)
    if not a or (a.get("owner_user_id") and a["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM vision_assets WHERE id=?", (aid,))
    return True


# --- tasks ---
def _task_out(r):
    if not r:
        return None
    d = dict(r); d["schema_fields"] = _pj(d.get("schema_fields"), []); return d


def list_tasks(v=None):
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM vision_tasks WHERE {_vis()} ORDER BY updated_at DESC", (v,)).fetchall()
    return [_task_out(r) for r in rows]


def get_task(tid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM vision_tasks WHERE id=? AND {_vis()}", (tid, v)).fetchone()
    return _task_out(r)


def create_task(d, owner):
    tid = new_id("vtask"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO vision_tasks (id,owner_user_id,name,slug,category,description,prompt,schema_fields,model,version,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,'1.0.0',?,?)""",
                  (tid, owner, d["name"], _slug(d["name"]), d.get("category", "structured"),
                   d.get("description", ""), d.get("prompt", ""), _j(d.get("schema_fields", [])),
                   d.get("model", "auto"), now, now))
    return get_task(tid, owner)


def delete_task(tid, owner):
    t = get_task(tid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _conn() as c:
        c.execute("DELETE FROM vision_tasks WHERE id=?", (tid,))
    return True


# --- runs ---
def create_run(task, asset, model, owner, correlation_id):
    rid = new_id("vrun")
    with _conn() as c:
        c.execute("""INSERT INTO vision_runs (id,owner_user_id,task_id,task_name,asset_id,asset_name,model,status,correlation_id,created_at)
                     VALUES (?,?,?,?,?,?,?,'running',?,?)""",
                  (rid, owner, task["id"], task["name"], asset["id"], asset.get("name"), model, correlation_id, now_iso()))
    return rid


def finish_run(rid, res):
    with _conn() as c:
        c.execute("""UPDATE vision_runs SET status=?, summary=?, structured=?, evidence=?, confidence=?,
                     prompt_tokens=?, completion_tokens=?, total_tokens=?, cost_usd=?, latency_ms=?, risk_flags=?, error=?, finished_at=?
                     WHERE id=?""",
                  (res.get("status", "failed"), res.get("summary"), _j(res.get("structured")), _j(res.get("evidence", [])),
                   res.get("confidence"), res.get("prompt_tokens"), res.get("completion_tokens"), res.get("total_tokens"),
                   res.get("cost_usd"), res.get("latency_ms"), _j(res.get("risk_flags", [])), res.get("error"), now_iso(), rid))


def _run_out(r):
    if not r:
        return None
    d = dict(r)
    d["structured"] = _pj(d.get("structured"), None); d["evidence"] = _pj(d.get("evidence"), [])
    d["risk_flags"] = _pj(d.get("risk_flags"), []); return d


def list_runs(v=None, limit=100):
    with _conn() as c:
        rows = c.execute(f"""SELECT id,owner_user_id,task_id,task_name,asset_id,asset_name,model,status,confidence,
                             total_tokens,cost_usd,latency_ms,created_at FROM vision_runs WHERE {_vis()}
                             ORDER BY created_at DESC LIMIT ?""", (v, limit)).fetchall()
    return [dict(r) for r in rows]


def get_run(rid, v=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM vision_runs WHERE id=? AND {_vis()}", (rid, v)).fetchone()
    return _run_out(r)


def stats(v=None):
    with _conn() as c:
        proj = c.execute(f"SELECT COUNT(*) n FROM vision_projects WHERE {_vis()}", (v,)).fetchone()["n"]
        assets = c.execute(f"SELECT COUNT(*) n FROM vision_assets WHERE {_vis()}", (v,)).fetchone()["n"]
        runs = c.execute(f"SELECT COUNT(*) n FROM vision_runs WHERE {_vis()}", (v,)).fetchone()["n"]
        row = c.execute(f"""SELECT COALESCE(AVG(confidence),0) conf, COALESCE(SUM(cost_usd),0) cost,
                            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed FROM vision_runs WHERE {_vis()}""", (v,)).fetchone()
    return {"projects": proj, "assets": assets, "runs": runs,
            "avg_confidence": round(row["conf"] or 0, 3), "spend_usd": round(row["cost"] or 0, 4),
            "failed_runs": row["failed"] or 0}
