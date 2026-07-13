"""VisionLab run engine — REAL vision extraction via the Nyquest relay.

Sends the asset image (base64 data URL) + the task's prompt + extraction schema to a
vision-capable model on the relay and parses structured output + a confidence estimate.
Costs are computed from real token usage. Nothing is fabricated: a failed call is a failed
run; an image the model can't read yields low confidence, not invented fields.
"""
import re
import json
import time
import llm
import pricing

DEFAULT_MODEL = "openai/gpt-4o-mini"  # vision-capable + cheap
_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|\b\d{3}-\d{2}-\d{4}\b|\b\d{13,16}\b)")


def _parse(text, fields):
    obj = None
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
        except Exception:
            obj = None
    if not isinstance(obj, dict):
        return {"summary": (text or "").strip()[:600], "fields": {}, "confidence": None}
    summary = obj.get("summary") or ""
    conf = obj.get("confidence")
    try:
        conf = max(0.0, min(1.0, float(conf))) if conf is not None else None
    except Exception:
        conf = None
    raw_fields = obj.get("fields") if isinstance(obj.get("fields"), dict) else {
        k: v for k, v in obj.items() if k not in ("summary", "confidence", "evidence")
    }
    # keep only requested field keys when a schema is defined
    keys = [f.get("name") for f in fields if f.get("name")]
    structured = {k: raw_fields.get(k) for k in keys} if keys else raw_fields
    return {"summary": str(summary)[:600], "fields": structured, "confidence": conf,
            "evidence": obj.get("evidence") if isinstance(obj.get("evidence"), list) else []}


async def run(task, asset, model, relay_key=None):
    if relay_key:
        llm.set_relay_auth(relay_key)
    if not llm.has_key():
        return {"status": "failed", "error": "No relay key configured — real vision needs NYQUEST_API_KEY."}
    data_url = asset.get("data_url")
    if not data_url:
        return {"status": "failed", "error": "Asset has no image data."}
    fields = task.get("schema_fields") or []
    field_desc = "\n".join(f"- {f.get('name')} ({f.get('type','string')}): {f.get('description','')}" for f in fields) or "(free-form — summarize what you see)"
    sys = ("You are a precise vision extraction engine. Look at the image and respond with ONLY a JSON object: "
           '{"summary": "<1-2 sentences>", "fields": {<the requested fields>}, "confidence": <0..1>}. '
           "Use null for any field not clearly present. Do not invent values.")
    user_text = f"{task.get('prompt') or 'Analyze this image.'}\n\nExtract these fields as JSON:\n{field_desc}"
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]},
    ]
    t0 = time.perf_counter()
    try:
        text, usage = await llm.chat(model or DEFAULT_MODEL, messages, temperature=0.0, max_tokens=800)
    except Exception as e:
        return {"status": "failed", "error": str(e)[:400], "latency_ms": int((time.perf_counter() - t0) * 1000)}
    latency = int((time.perf_counter() - t0) * 1000)
    parsed = _parse(text, fields)
    pt = int(usage.get("prompt_tokens") or 0)
    ct = int(usage.get("completion_tokens") or 0)
    cost, _ = pricing.cost_for(usage.get("model") or model, pt, ct)
    # secret / PII flags on any extracted text (real, deterministic)
    blob = json.dumps(parsed["fields"], default=str) + " " + (parsed["summary"] or "")
    risk = ["contains_secret_or_pii"] if _SECRET_RE.search(blob) else []
    return {"status": "completed", "summary": parsed["summary"], "structured": parsed["fields"],
            "evidence": parsed.get("evidence", []), "confidence": parsed["confidence"],
            "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": int(usage.get("total_tokens") or (pt + ct)),
            "cost_usd": cost, "latency_ms": latency, "risk_flags": risk,
            "usage": {"model": usage.get("model"), "prompt_tokens": pt, "completion_tokens": ct}}
