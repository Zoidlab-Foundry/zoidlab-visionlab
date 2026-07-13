"""Seed VisionLab with a demo project + reusable vision tasks (real extraction schemas).
No runs are seeded — runs come only from real relay vision calls the user triggers, so
nothing here fabricates extraction results."""
import db_pg as db

_TASKS = [
    {"name": "Invoice extraction", "category": "receipt/invoice",
     "prompt": "Read this invoice and extract the key billing fields.",
     "schema_fields": [
        {"name": "vendor", "type": "string", "description": "who issued the invoice"},
        {"name": "invoice_number", "type": "string", "description": ""},
        {"name": "invoice_date", "type": "date", "description": ""},
        {"name": "total", "type": "currency", "description": "grand total"},
        {"name": "line_items", "type": "array", "description": "description + amount per line"},
     ]},
    {"name": "Menu extraction", "category": "structured",
     "prompt": "Read this restaurant menu image and extract the dishes.",
     "schema_fields": [
        {"name": "restaurant", "type": "string", "description": "if shown"},
        {"name": "sections", "type": "array", "description": "menu sections"},
        {"name": "dishes", "type": "array", "description": "each dish name + price + description"},
     ]},
    {"name": "Screenshot review", "category": "screenshot",
     "prompt": "Analyze this UI screenshot: describe what it shows and any issues.",
     "schema_fields": [
        {"name": "screen", "type": "string", "description": "what screen/app this is"},
        {"name": "primary_action", "type": "string", "description": "the main CTA"},
        {"name": "issues", "type": "array", "description": "usability or visual issues"},
     ]},
    {"name": "Diagram analysis", "category": "diagram",
     "prompt": "Interpret this network/architecture diagram.",
     "schema_fields": [
        {"name": "components", "type": "array", "description": "nodes/devices shown"},
        {"name": "connections", "type": "array", "description": "how components connect"},
        {"name": "summary", "type": "string", "description": "what the diagram represents"},
     ]},
]


def run():
    if db.list_projects(None) or db.list_tasks(None):
        return 0
    db.create_project({"name": "Vision Demo", "description": "Sample vision-analysis project — "
                       "upload an image and run a task to see real extraction."}, owner=None)
    for t in _TASKS:
        db.create_task(t, owner=None)
    return len(_TASKS)
