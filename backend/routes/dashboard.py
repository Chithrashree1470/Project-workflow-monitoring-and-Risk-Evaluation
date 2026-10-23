
from flask import Blueprint, render_template

from backend.supabase_client import supabase
from backend.services.project_service import refresh_project_task_metrics

dashboard_bp = Blueprint("dashboard", __name__)


def _get_project_rows(table_name, project_id):
    """Fetch records belonging to one project."""
    try:
        response = (
            supabase
            .table(table_name)
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return response.data or []

    except Exception as error:
        print(
            f"Dashboard lookup error ({table_name}) "
            f"for project {project_id}:",
            error,
        )
        return []


def _get_dynamic_risk(project_id):
    """Load the currently saved dynamic-risk record."""
    try:
        response = (
            supabase
            .table("project_dynamic_risk")
            .select("risk_level, risk_score, risk_trend")
            .eq("project_id", project_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    except Exception as error:
        print(
            f"Dashboard dynamic-risk lookup error "
            f"for project {project_id}:",
            error,
        )
        return None


def _normalise_risk(value, fallback="Low"):
    """Handle plain labels and list-like labels returned by the database."""
    if value is None:
        return fallback

    if isinstance(value, (list, tuple)):
        value = value[0] if value else fallback

    value = str(value).strip()

    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip().strip("'\"")

    return value or fallback


@dashboard_bp.route("/dashboard")
def dashboard():
    try:
        response = (
            supabase
            .table("projects")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        projects = response.data or []

    except Exception as error:
        print("Dashboard error:", error)
        projects = []

    counts = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0,
    }

    for project in projects:
        project_id = project.get("id")

        if project_id is None:
            continue

        # Refresh task execution metrics from the current Tasks table.
        try:
            metrics = refresh_project_task_metrics(project_id)

            if isinstance(metrics, dict):
                project.update(metrics)

        except Exception as error:
            print(
                f"Unable to refresh metrics for project "
                f"{project_id}:",
                error,
            )

        # Calculate displayed team size from the union of the saved
        # project team and employees assigned to current project tasks.
        team_members = _get_project_rows(
            "project_team_members",
            project_id,
        )

        tasks = _get_project_rows(
            "Tasks",
            project_id,
        )

        employee_ids = {
            str(member.get("employee_id")).strip()
            for member in team_members
            if member.get("employee_id") is not None
            and str(member.get("employee_id")).strip()
        }

        for task in tasks:
            employee_id = str(
                task.get("assigned_to") or ""
            ).strip()

            if employee_id:
                employee_ids.add(employee_id)

        project["team_size"] = len(employee_ids)

        # Prefer the saved dynamic risk when available.
        # Fall back to the original project-level prediction.
        dynamic_risk = _get_dynamic_risk(project_id)

        if dynamic_risk and dynamic_risk.get("risk_level") is not None:
            current_risk = dynamic_risk["risk_level"]
        else:
            current_risk = project.get("predicted_risk", "Low")

        current_risk = _normalise_risk(current_risk)

        project["current_risk"] = current_risk
        project["dynamic_risk_score"] = (
            dynamic_risk.get("risk_score")
            if dynamic_risk
            else None
        )
        project["risk_trend"] = (
            dynamic_risk.get("risk_trend")
            if dynamic_risk
            else None
        )

        # The statistics must count the risk displayed in the table.
        if current_risk in counts:
            counts[current_risk] += 1

    return render_template(
        "dashboard.html",
        projects=projects,
        counts=counts,
    )
