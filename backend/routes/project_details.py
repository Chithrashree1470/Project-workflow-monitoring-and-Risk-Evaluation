import json

from flask import Blueprint, render_template
from backend.services.project_service import (
    refresh_project_task_metrics
)
from backend.supabase_client import supabase

project_details_bp = Blueprint("project_details", __name__)


@project_details_bp.route("/project/<project_id>")
def project_details(project_id):
    try:
        # =========================================================
        # GET PROJECT
        # =========================================================

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


        # =========================================================
        # GET TEAM MEMBERS
        # =========================================================

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
            print(
                "Project team lookup error:",
                team_error
            )

            project_team_members = details.get(
                "team_members",
                []
            )


        # =========================================================
        # GET CLIENTS
        # =========================================================

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
            print(
                "Project client lookup error:",
                client_error
            )

            project_clients = details.get(
                "clients",
                []
            )


        # =========================================================
        # REFRESH TEAM DETAILS
        # =========================================================

        if project_team_members:

            details["team_members"] = project_team_members

            details["team_member_ids"] = [
                member.get("employee_id", "")
                for member in project_team_members
                if member.get("employee_id")
            ]


        # =========================================================
        # REFRESH CLIENT DETAILS
        # =========================================================

        if project_clients:

            details["clients"] = project_clients

            details["stakeholder_ids"] = [
                client.get("client_id", "")
                for client in project_clients
                if client.get("client_id")
            ]


        # =========================================================
        # GET TASKS
        # =========================================================

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

            print(
                "Project task lookup error:",
                task_error
            )

            tasks = []

        # =========================================================
        # REFRESH PROJECT EXECUTION METRICS
        # =========================================================

        try:

            refreshed_metrics = (
                refresh_project_task_metrics(
                    project_id
                )
            )

            print(
                "[PROJECT DETAILS] REFRESHED METRICS:",
                refreshed_metrics
            )

            # Update the project object used by Jinja
            project.update({
                "total_tasks":
                    refreshed_metrics["total_tasks"],

                "completed_tasks":
                    refreshed_metrics["completed_tasks"],

                "pending_tasks":
                    refreshed_metrics["pending_tasks"],

                "overdue_tasks":
                    refreshed_metrics["overdue_tasks"],

                "completion_percentage":
                    refreshed_metrics[
                        "completion_percentage"
                    ],

                "delay_percentage":
                    refreshed_metrics[
                        "delay_percentage"
                    ],

                "estimated_effort_hours":
                    refreshed_metrics[
                        "estimated_effort_hours"
                    ],

                "actual_effort_hours":
                    refreshed_metrics[
                        "actual_effort_hours"
                    ],

                "project_progress":
                    refreshed_metrics[
                        "project_progress"
                    ]
            })

        except Exception as metrics_error:

            print(
                "Project metrics refresh error:",
                metrics_error
            )

        # =========================================================
        # GET DYNAMIC PROJECT RISK
        # =========================================================
        #
        # This table contains the CURRENT dynamic risk after
        # tasks have been created/updated.
        #
        # We do NOT calculate risk here.
        # task_risk.py remains responsible for calculation.
        # =========================================================

        try:

            risk_response = (
                supabase
                .table("project_dynamic_risk")
                .select("*")
                .eq("project_id", project_id)
                .order("calculated_at", desc=True)
                .limit(1)
                .execute()
            )

            dynamic_risk_data = (
                risk_response.data or []
            )

            dynamic_risk = (
                dynamic_risk_data[0]
                if dynamic_risk_data
                else None
            )

        except Exception as risk_error:

            print(
                "Dynamic project risk lookup error:",
                risk_error
            )

            dynamic_risk = None


        # =========================================================
        # DETERMINE RISK TO DISPLAY
        # =========================================================
        #
        # NEW PROJECT:
        #     No dynamic risk yet
        #     -> use initial predicted_risk
        #
        # EXISTING PROJECT WITH TASKS:
        #     Dynamic risk exists
        #     -> use dynamic risk_level
        #
        # This keeps the initial risk and dynamic risk separate
        # in the database while giving the frontend one current
        # risk value to display.
        # =========================================================

        if dynamic_risk:

            current_risk = (
                dynamic_risk.get("risk_level")
                or project.get("predicted_risk")
            )

        else:

            current_risk = project.get(
                "predicted_risk"
            )


        # =========================================================
        # ADD CURRENT RISK TO PROJECT OBJECT
        # =========================================================
        #
        # project_details.html can now simply use:
        #
        #     {{ project.current_risk }}
        #
        # =========================================================

        project["current_risk"] = current_risk


        # =========================================================
        # RENDER PAGE
        # =========================================================

        return render_template(
            "project_details.html",
            project=project,
            details=details,
            tasks=tasks,
            dynamic_risk=dynamic_risk
        )


    except Exception as error:

        print(
            "Project details error:",
            error
        )

        return (
            "Unable to load project details.",
            500
        )