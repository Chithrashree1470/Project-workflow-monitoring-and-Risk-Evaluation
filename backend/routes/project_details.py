import json

from flask import Blueprint, render_template, session, request

from backend.services.project_service import refresh_project_task_metrics
from backend.supabase_client import supabase
from backend.master_data import get_employee_by_id

project_details_bp = Blueprint("project_details", __name__)


def _load_project(project_id):
    response = (
        supabase
        .table("projects")
        .select("*")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )

    projects = response.data or []
    if not projects:
        return None, {}

    project = projects[0]
    details = project.get("project_details") or {}

    if isinstance(details, str):
        try:
            details = json.loads(details)
        except Exception:
            details = {}

    return project, details



def _load_children(project_id, details):
    # --------------------------------------------------------
    # LOAD EXISTING PROJECT TEAM
    # --------------------------------------------------------
    try:
        team = (
            supabase
            .table("project_team_members")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        print("Project team lookup error:", error)
        team = details.get("team_members", [])

    # --------------------------------------------------------
    # LOAD CLIENTS
    # --------------------------------------------------------
    try:
        clients = (
            supabase
            .table("project_clients")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        print("Project client lookup error:", error)
        clients = details.get("clients", [])

    # --------------------------------------------------------
    # LOAD CURRENT PROJECT TASKS
    # --------------------------------------------------------
    try:
        all_tasks = (
            supabase
            .table("Tasks")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
    except Exception as error:
        print("Project task lookup error:", error)
        all_tasks = []

    # --------------------------------------------------------
    # INCLUDE EMPLOYEES ASSIGNED TO PROJECT TASKS
    # --------------------------------------------------------
    known_employee_ids = {
        str(member.get("employee_id")).strip()
        for member in team
        if member.get("employee_id")
    }

    for task in all_tasks:
        employee_id = str(task.get("assigned_to") or "").strip()

        if not employee_id or employee_id in known_employee_ids:
            continue

        try:
            employee = get_employee_by_id(employee_id)

            if not employee:
                print(
                    f"Assigned employee {employee_id} "
                    "was not found in the employees table."
                )
                continue

            team.append({
                "project_id": project_id,
                "employee_id": employee.get(
                    "employee_id", employee_id
                ),
                "employee_name": employee.get(
                    "employee_name",
                    employee.get("name", "")
                ),
                "email": employee.get("email", ""),
                "role": employee.get("role", ""),
                "department": employee.get("department", ""),
                "experience_level": employee.get(
                    "experience_level", ""
                ),
                "years_experience": employee.get(
                    "years_experience", 0
                ),
                "skills": employee.get("skills", "")
            })

            known_employee_ids.add(employee_id)

        except Exception as error:
            print(
                f"Unable to load assigned employee {employee_id}:",
                error
            )

    return team, clients, all_tasks


def _load_task_predictions(project_id):
    try:
        rows = (
            supabase
            .table("task_risk_prediction")
            .select("issue_id, risk_label, risk_score")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
        return {str(row.get("issue_id")): row for row in rows}
    except Exception as error:
        print("Task prediction lookup error:", error)
        return {}


def _load_dynamic_risk(project_id):
    """
    Load the current dynamic risk record.

    Do not order by calculated_at: deployments may not have that
    optional column. The risk calculator replaces the current row
    for a project, so selecting the matching row is sufficient.
    """
    try:
        rows = (
            supabase
            .table("project_dynamic_risk")
            .select("*")
            .eq("project_id", project_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
    except Exception as error:
        print("Dynamic risk lookup error:", error)
        return None


def _normalise_risk_label(value, fallback="Low"):
    """Convert DB values such as ['Low'] or "['Low']" to 'Low'."""
    if value is None:
        return fallback

    if isinstance(value, (list, tuple)):
        value = value[0] if value else fallback

    label = str(value).strip()

    if label.startswith("[") and label.endswith("]"):
        label = label[1:-1].strip()
    label = label.strip("'\\\" ").strip()

    return label or fallback


@project_details_bp.route("/project/<project_id>")
def project_details(project_id):
    try:
        project, details = _load_project(project_id)
        if not project:
            return "Project not found.", 404

        team_members, clients, all_tasks = _load_children(
            project_id,
            details,
        )

        # Always derive execution metrics from the current Tasks table.
        metrics = refresh_project_task_metrics(project_id)
        project.update(metrics)

        dynamic_risk = _load_dynamic_risk(project_id)
        task_predictions = _load_task_predictions(project_id)

        # This project workspace uses direct view switching instead of a
        # username/password prompt, as requested. If no view is selected,
        # open the Manager workspace by default.
        access_key = f"project_access_{project_id}"
        access = session.get(access_key) or {}
        requested_view = (request.args.get("view") or "").strip().lower()

        if requested_view in {"manager", "employee", "client"}:
            role = requested_view
            if role == "employee":
                subject_id = (
                    team_members[0].get("employee_id")
                    if team_members else None
                )
            elif role == "client":
                subject_id = (
                    clients[0].get("client_id")
                    if clients else None
                )
            else:
                subject_id = None
            session[access_key] = {
                "role": role,
                "subject_id": subject_id,
            }
        else:
            role = access.get("role") or "manager"
            subject_id = access.get("subject_id")
            if role not in {"manager", "employee", "client"}:
                role, subject_id = "manager", None
            session[access_key] = {
                "role": role,
                "subject_id": subject_id,
            }

        # Employee view shows only tasks assigned to that employee.
        if role == "employee":
            visible_tasks = [
                task
                for task in all_tasks
                if str(task.get("assigned_to")) == str(subject_id)
            ]
        else:
            visible_tasks = all_tasks

        # Before execution risk exists, show the original project-level
        # CatBoost prediction. After Generate Risk, show the dynamic risk.
        raw_current_risk = (
            dynamic_risk.get("risk_level")
            if dynamic_risk
            else project.get("predicted_risk")
        )
        project["current_risk"] = _normalise_risk_label(
            raw_current_risk,
            fallback="Low",
        )

        details = {
            **details,
            "team_members": team_members,
            "clients": clients,
            "tasks": visible_tasks,
            "all_tasks": all_tasks,
            "team_member_ids": [
                member.get("employee_id")
                for member in team_members
                if member.get("employee_id")
            ],
            "stakeholder_ids": [
                client.get("client_id")
                for client in clients
                if client.get("client_id")
            ],
            "stakeholder_count": len(clients),
        }

        return render_template(
            "project_details.html",
            project=project,
            details=details,
            tasks=visible_tasks,
            all_tasks=all_tasks,
            dynamic_risk=dynamic_risk,
            task_predictions=task_predictions,
            role=role,
            subject_id=subject_id,
        )

    except Exception as error:
        import traceback
        traceback.print_exc()
        return "Unable to load project details: " + str(error), 500
