import os

from flask import Flask
from dotenv import load_dotenv

from backend.routes.project import project_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.project_details import project_details_bp
from backend.routes.tasks import tasks_bp
from backend.routes.task_risk import task_risk_bp
from backend.master_data import master_data_bp
from backend.manager import manager_bp

load_dotenv()
print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
print("SUPABASE_KEY exists:", bool(os.getenv("SUPABASE_KEY")))

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "infrasync-ai-secret-key"
)

app.register_blueprint(project_bp)
app.register_blueprint(master_data_bp)
app.register_blueprint(manager_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(project_details_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(task_risk_bp)

if __name__ == "__main__":
    from backend.services.project_risk import MODEL_PATH, MODEL_FEATURES
    print("\nREGISTERED ROUTES:")
    for rule in app.url_map.iter_rules():
        print(rule, "->", rule.endpoint, rule.methods)
    print("=" * 60)
    print("INFRA SYNC AI")
    print("AI-BASED PREDICTIVE WORKFLOW MONITORING")
    print("=" * 60)
    print("Model:", MODEL_PATH)
    print("Features:", len(MODEL_FEATURES))
    print("Supabase: Connected")
    print("=" * 60)
    app.run(debug=True)
