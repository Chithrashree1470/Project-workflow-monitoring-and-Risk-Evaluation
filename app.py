
import os

from flask import Flask
from dotenv import load_dotenv

from backend.routes.project import project_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.project_details import project_details_bp
from backend.routes.tasks import tasks_bp
from backend.routes.task_risk import task_risk_bp
from backend.routes.access import access_bp

from backend.master_data import master_data_bp
from backend.manager import manager_bp


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. "
        "Add FLASK_SECRET_KEY to your .env file."
    )


# Register each existing Blueprint exactly once.
blueprints = [
    project_bp,
    master_data_bp,
    manager_bp,
    access_bp,
    dashboard_bp,
    project_details_bp,
    tasks_bp,
    task_risk_bp,
]

registered_names = set()

for blueprint in blueprints:
    if blueprint.name in registered_names:
        raise RuntimeError(
            f"Duplicate Blueprint in app.py: {blueprint.name}"
        )

    registered_names.add(blueprint.name)
    app.register_blueprint(blueprint)


if __name__ == "__main__":
    from backend.services.project_risk import (
        MODEL_PATH,
        MODEL_FEATURES,
    )

    print("\nREGISTERED ROUTES:")

    for rule in app.url_map.iter_rules():
        print(rule, "->", rule.endpoint, rule.methods)

    print("=" * 60)
    print("INFRA SYNC AI")
    print("AI-BASED PREDICTIVE WORKFLOW MONITORING")
    print("=" * 60)
    print("Model:", MODEL_PATH)
    print("Features:", len(MODEL_FEATURES))
    print("=" * 60)

    app.run(debug=True)
