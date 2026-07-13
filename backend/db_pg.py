"""Postgres data layer for VisionLab with per-tenant Row-Level Security (§3.2).

Tenant isolation is enforced by the database, not just the app: every tenant table carries
owner_user_id, has FORCE ROW LEVEL SECURITY, and a policy that only exposes rows whose owner
matches `app.current_owner` (set per transaction) or is NULL (shared seed). Even a bug in an
app query cannot cross tenants. Image bytes live in MinIO (see storage.py); this table keeps
only the object key + checksum. Public API mirrors the former sqlite database.py.
"""
import os
import uuid
import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

import storage

# App connections use the RLS-enforced role (app_rls); DDL + cross-tenant admin use the
# superuser (foundry), which bypasses RLS by design.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app_rls@127.0.0.1:5433/visionlab")
DATABASE_URL_ADMIN = os.environ.get("DATABASE_URL_ADMIN", "postgresql://foundry@127.0.0.1:5433/visionlab")
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": False})


def admin_conn():
    return psycopg.connect(DATABASE_URL_ADMIN, row_factory=dict_row)


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(p):
    return f"{p}_{uuid.uuid4().hex[:12]}"


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


class _tx:
    """Transaction scoped to a tenant: sets app.current_owner so RLS applies."""
    def __init__(self, owner):
        self.owner = owner or ""

    def __enter__(self):
        self.conn = _pool.getconn()
        self.cur = self.conn.cursor(row_factory=dict_row)
        self.cur.execute("SELECT set_config('app.current_owner', %s, true)", (self.owner,))
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.cur.close()
            _pool.putconn(self.conn)


_TENANT_TABLES = ["vision_projects", "vision_assets", "vision_tasks", "vision_runs", "jobs"]


def init():
    with admin_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT, name TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS vision_projects (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, description TEXT,
            status TEXT DEFAULT 'active', risk_level TEXT DEFAULT 'low', created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS vision_assets (
            id TEXT PRIMARY KEY, owner_user_id TEXT, project_id TEXT, name TEXT, mime TEXT, kind TEXT DEFAULT 'image',
            object_key TEXT, sha256 TEXT, size_bytes BIGINT, risk_flags JSONB, tags JSONB, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS vision_tasks (
            id TEXT PRIMARY KEY, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT, category TEXT,
            description TEXT, prompt TEXT, schema_fields JSONB, model TEXT DEFAULT 'auto', version TEXT DEFAULT '1.0.0',
            created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS vision_runs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, task_id TEXT, task_name TEXT, asset_id TEXT, asset_name TEXT,
            model TEXT, status TEXT DEFAULT 'queued', summary TEXT, structured JSONB, evidence JSONB, confidence REAL,
            prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER, cost_usd DOUBLE PRECISION, latency_ms INTEGER,
            risk_flags JSONB, error TEXT, correlation_id TEXT, created_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, status TEXT, error TEXT,
            attempts INTEGER DEFAULT 0, celery_id TEXT, timeout_s INTEGER, created_at TEXT, started_at TEXT, finished_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS dead_letters (
            id TEXT PRIMARY KEY, owner_user_id TEXT, kind TEXT, resource_id TEXT, error TEXT, created_at TEXT)""")
        for t in _TENANT_TABLES:
            c.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            c.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
            c.execute(f"DROP POLICY IF EXISTS {t}_isolation ON {t}")
            c.execute(f"""CREATE POLICY {t}_isolation ON {t}
                USING (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))
                WITH CHECK (owner_user_id IS NULL OR owner_user_id = current_setting('app.current_owner', true))""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_va_owner ON vision_assets(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_vr_owner ON vision_runs(owner_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_user_id, created_at)")
        # the RLS-enforced app role gets DML on every table (users has no RLS; the rest do)
        c.execute("GRANT USAGE ON SCHEMA public TO app_rls")
        c.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO app_rls")


def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _pool.connection() as c:
        c.execute("""INSERT INTO users (id,email,name,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)
                     ON CONFLICT (id) DO UPDATE SET email=COALESCE(EXCLUDED.email,users.email),
                       name=COALESCE(EXCLUDED.name,users.name), updated_at=EXCLUDED.updated_at""",
                  (uid, email, name, now, now))


# --- projects ---
def list_projects(v=None):
    with _tx(v) as cur:
        cur.execute("""SELECT p.*, (SELECT COUNT(*) FROM vision_assets a WHERE a.project_id=p.id) AS assets
                       FROM vision_projects p ORDER BY p.updated_at DESC""")
        return cur.fetchall()


def get_project(pid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM vision_projects WHERE id=%s", (pid,))
        return cur.fetchone()


def create_project(d, owner):
    pid = new_id("vproj"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO vision_projects (id,owner_user_id,name,slug,description,status,risk_level,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,'active',%s,%s,%s)""",
                    (pid, owner, d["name"], _slug(d["name"]), d.get("description", ""), d.get("risk_level", "low"), now, now))
    return get_project(pid, owner)


# --- assets (bytes in MinIO) ---
def create_asset(d, owner):
    aid = new_id("asset"); now = now_iso()
    meta = storage.put_data_url(owner, d.get("data_url") or "")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO vision_assets (id,owner_user_id,project_id,name,mime,kind,object_key,sha256,size_bytes,risk_flags,tags,created_at)
                       VALUES (%s,%s,%s,%s,%s,'image',%s,%s,%s,%s,%s,%s)""",
                    (aid, owner, d.get("project_id"), d.get("name", "asset"), meta["mime"], meta["object_key"],
                     meta["sha256"], meta["size_bytes"], Json(d.get("risk_flags", [])), Json(d.get("tags", [])), now))
    return get_asset(aid, owner, with_data=False)


def get_asset(aid, v=None, with_data=True):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM vision_assets WHERE id=%s", (aid,))
        r = cur.fetchone()
    if not r:
        return None
    d = dict(r)
    if with_data and d.get("object_key"):
        try:
            d["data_url"] = storage.get_data_url(d["object_key"], d.get("mime") or "image/png")
        except Exception:
            d["data_url"] = None
    return d


def list_assets(v=None, project_id=None, limit=200):
    q = "SELECT id,owner_user_id,project_id,name,mime,kind,sha256,size_bytes,risk_flags,tags,created_at FROM vision_assets"
    args = []
    if project_id and project_id != "all":
        q += " WHERE project_id=%s"; args.append(project_id)
    q += " ORDER BY created_at DESC LIMIT %s"; args.append(limit)
    with _tx(v) as cur:
        cur.execute(q, args)
        return cur.fetchall()


def delete_asset(aid, owner):
    a = get_asset(aid, owner, with_data=False)
    if not a or (a.get("owner_user_id") and a["owner_user_id"] != owner):
        return False
    if a.get("object_key"):
        storage.delete(a["object_key"])
    with _tx(owner) as cur:
        cur.execute("DELETE FROM vision_assets WHERE id=%s", (aid,))
    return True


# --- tasks ---
def list_tasks(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM vision_tasks ORDER BY updated_at DESC")
        return cur.fetchall()


def get_task(tid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM vision_tasks WHERE id=%s", (tid,))
        return cur.fetchone()


def create_task(d, owner):
    tid = new_id("vtask"); now = now_iso()
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO vision_tasks (id,owner_user_id,name,slug,category,description,prompt,schema_fields,model,version,created_at,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'1.0.0',%s,%s)""",
                    (tid, owner, d["name"], _slug(d["name"]), d.get("category", "structured"),
                     d.get("description", ""), d.get("prompt", ""), Json(d.get("schema_fields", [])),
                     d.get("model", "auto"), now, now))
    return get_task(tid, owner)


def delete_task(tid, owner):
    t = get_task(tid, owner)
    if not t or (t.get("owner_user_id") and t["owner_user_id"] != owner):
        return False
    with _tx(owner) as cur:
        cur.execute("DELETE FROM vision_tasks WHERE id=%s", (tid,))
    return True


# --- runs ---
def create_run(task, asset, model, owner, correlation_id):
    rid = new_id("vrun")
    with _tx(owner) as cur:
        cur.execute("""INSERT INTO vision_runs (id,owner_user_id,task_id,task_name,asset_id,asset_name,model,status,correlation_id,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s)""",
                    (rid, owner, task["id"], task["name"], asset["id"], asset.get("name"), model, correlation_id, now_iso()))
    return rid


def finish_run(rid, res, owner=None):
    with _tx(owner) as cur:
        cur.execute("""UPDATE vision_runs SET status=%s, summary=%s, structured=%s, evidence=%s, confidence=%s,
                       prompt_tokens=%s, completion_tokens=%s, total_tokens=%s, cost_usd=%s, latency_ms=%s, risk_flags=%s, error=%s, finished_at=%s
                       WHERE id=%s""",
                    (res.get("status", "failed"), res.get("summary"), Json(res.get("structured")), Json(res.get("evidence", [])),
                     res.get("confidence"), res.get("prompt_tokens"), res.get("completion_tokens"), res.get("total_tokens"),
                     res.get("cost_usd"), res.get("latency_ms"), Json(res.get("risk_flags", [])), res.get("error"), now_iso(), rid))


def set_run_status(rid, status, owner=None):
    with _tx(owner) as cur:
        cur.execute("UPDATE vision_runs SET status=%s WHERE id=%s", (status, rid))


def list_runs(v=None, limit=100):
    with _tx(v) as cur:
        cur.execute("""SELECT id,owner_user_id,task_id,task_name,asset_id,asset_name,model,status,confidence,
                       total_tokens,cost_usd,latency_ms,created_at FROM vision_runs ORDER BY created_at DESC LIMIT %s""", (limit,))
        return cur.fetchall()


def get_run(rid, v=None):
    with _tx(v) as cur:
        cur.execute("SELECT * FROM vision_runs WHERE id=%s", (rid,))
        return cur.fetchone()


def stats(v=None):
    with _tx(v) as cur:
        cur.execute("SELECT COUNT(*) n FROM vision_projects"); proj = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM vision_assets"); assets = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM vision_runs"); runs = cur.fetchone()["n"]
        cur.execute("""SELECT COALESCE(AVG(confidence),0) conf, COALESCE(SUM(cost_usd),0) cost,
                       COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),0) failed FROM vision_runs""")
        row = cur.fetchone()
    return {"projects": proj, "assets": assets, "runs": runs,
            "avg_confidence": round(row["conf"] or 0, 3), "spend_usd": round(row["cost"] or 0, 4),
            "failed_runs": row["failed"] or 0}
