import json

from flask import Blueprint, render_template

from backend.supabase_client import supabase

project_details_bp = Blueprint("project_details", __name__)


@project_details_bp.route("/project/<project_id>")
def project_details(project_id):
    try:
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
            return "Project not found.", 404

        project = projects[0]

        details = project.get("project_details") or {}

        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        # Existing team/client refresh.
        try:
            team_response = (
                supabase
                .table("project_team_members")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            project_team_members = team_response.data or []
        except Exception as team_error:
            print("Project team lookup error:", team_error)
            project_team_members = details.get("team_members", [])

        try:
            client_response = (
                supabase
                .table("project_clients")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            project_clients = client_response.data or []
        except Exception as client_error:
            print("Project client lookup error:", client_error)
            project_clients = details.get("clients", [])

        if project_team_members:
            details["team_members"] = project_team_members
            details["team_member_ids"] = [
                member.get("employee_id", "")
                for member in project_team_members
                if member.get("employee_id")
            ]

        if project_clients:
            details["clients"] = project_clients
            details["stakeholder_ids"] = [
                client.get("client_id", "")
                for client in project_clients
                if client.get("client_id")
            ]

        # Task CRUD remains in tasks.py. This route only reads the
        # current tasks for the project for the details page.
        try:
            task_response = (
                supabase
                .table("Tasks")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at", desc=False)
                .execute()
            )
            tasks = task_response.data or []
        except Exception as task_error:
            print("Project task lookup error:", task_error)
            tasks = []

        # Dynamic project risk is calculated and stored by task_risk.py.
        # This route only reads that record; it does not duplicate the
        # aggregation logic.
        try:
            risk_response = (
                supabase
                .table("project_dynamic_risk")
                .select("*")
                .eq("project_id", project_id)
                .limit(1)
                .execute()
            )
            dynamic_risk_data = risk_response.data or []
            dynamic_risk = (
                dynamic_risk_data[0]
                if dynamic_risk_data
                else None
            )
        except Exception as risk_error:
            print("Dynamic project risk lookup error:", risk_error)
            dynamic_risk = None

        return render_template(
            "project_details.html",
            project=project,
            details=details,
            tasks=tasks,
            dynamic_risk=dynamic_risk
        )

    except Exception as error:
        print("Project details error:", error)

        return (
            "Unable to load project details.",
            500
        )
