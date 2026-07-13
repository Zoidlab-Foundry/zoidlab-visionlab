"""VisionLab package export — a portable vision task workflow, wrapped in the canonical
Foundry base envelope (blueprint §6.2 / Tier-3 Appendix C)."""
import envelope


def to_package(task, owner=None, sample_runs=None):
    payload = {
        "schema_version": "1.0",
        "package_type": "nyquest_vision_package",
        "foundry_package": "vision",
        "resource_version": task.get("version", "1.0.0"),
        "task": {"name": task.get("name"), "category": task.get("category"),
                 "prompt": task.get("prompt"), "model": task.get("model")},
        "extraction_schema": {"fields": task.get("schema_fields", [])},
        "provider_config": {"model": task.get("model")},
        "governance": {"human_review": True},
        "dependencies": [],
        "sample_outputs": sample_runs or [],
        "credential_refs": [],
    }
    return envelope.wrap("vision", "vision_task", task.get("id"), task.get("version", "1.0.0"),
                         payload, nyquest_user_id=owner)
