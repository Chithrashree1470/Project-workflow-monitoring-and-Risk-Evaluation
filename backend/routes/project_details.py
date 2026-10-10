import json

from flask import Blueprint, render_template, request, jsonify

from backend.routes import project
from backend.services.project_service import (
    refresh_project_task_metrics
)
from backend.services.project_skill import update_project_skill_metrics
from backend.supabase_client import supabase

from backend.services.project_skill import (
    update_project_skill_metrics
)


from backend.master_data import (
    get_employee_by_id
)

project_details_bp = Blueprint(
    "project_details",
    __name__
)


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

        details = project.get(
            "project_details"
        ) or {}

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

            project_team_members = (
                team_response.data or []
            )

        except Exception as team_error:

            print(
                "Project team lookup error:",
                team_error
            )

            project_team_members = (
                details.get(
                    "team_members",
                    []
                )
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

            project_clients = (
                client_response.data or []
            )

        except Exception as client_error:

            print(
                "Project client lookup error:",
                client_error
            )

            project_clients = (
                details.get(
                    "clients",
                    []
                )
            )


        # =========================================================
        # REFRESH TEAM DETAILS
        # =========================================================

        if project_team_members:

            details["team_members"] = (
                project_team_members
            )

            details["team_member_ids"] = [
                member.get(
                    "employee_id",
                    ""
                )
                for member in project_team_members
                if member.get("employee_id")
            ]


        # =========================================================
        # REFRESH CLIENT DETAILS
        # =========================================================

        if project_clients:

            details["clients"] = (
                project_clients
            )

            details["stakeholder_ids"] = [
                client.get(
                    "client_id",
                    ""
                )
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
                .order(
                    "created_at",
                    desc=False
                )
                .execute()
            )

            tasks = (
                task_response.data or []
            )

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
                "[PROJECT DETAILS] "
                "REFRESHED METRICS:",
                refreshed_metrics
            )

            project.update({

                "total_tasks":
                    refreshed_metrics[
                        "total_tasks"
                    ],

                "pending_tasks":
                    refreshed_metrics[
                        "pending_tasks"
                    ],

                "completed_tasks":
                    refreshed_metrics[
                        "completed_tasks"
                    ],

                "overdue_tasks":
                    refreshed_metrics[
                        "overdue_tasks"
                    ],

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

        try:

            risk_response = (
                supabase
                .table("project_dynamic_risk")
                .select("*")
                .eq("project_id", project_id)
                .order(
                    "calculated_at",
                    desc=True
                )
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

        if dynamic_risk:

            current_risk = (
                dynamic_risk.get(
                    "risk_level"
                )
                or project.get(
                    "predicted_risk"
                )
            )

        else:

            current_risk = (
                project.get(
                    "predicted_risk"
                )
            )


        # =========================================================
        # ADD CURRENT RISK TO PROJECT OBJECT
        # =========================================================

        project["current_risk"] = (
            current_risk
        )
        skill_metrics = update_project_skill_metrics(project_id)
        project["skill_coverage"] = skill_metrics["skill_coverage"]
        project["skill_gap"] = skill_metrics["skill_gap"]

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


# =============================================================
# ADD EMPLOYEE TO PROJECT
# =============================================================

@project_details_bp.route(
    "/api/project/<project_id>/employees",
    methods=["POST"]
)
def add_project_employee(project_id):

    try:

        # =====================================================
        # CHECK WHETHER PROJECT EXISTS
        # =====================================================

        project_response = (
            supabase
            .table("projects")
            .select("id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )

        if not project_response.data:
            return jsonify({
                "success": False,
                "message": "Project not found."
            }), 404

        # =====================================================
        # GET REQUEST DATA
        # =====================================================

        data = request.get_json(silent=True) or {}

        employee_id = str(
            data.get("employee_id") or ""
        ).strip()

        if not employee_id:
            return jsonify({
                "success": False,
                "message": "Employee ID is required."
            }), 400

        # =====================================================
        # GET EMPLOYEE
        # =====================================================

        employee = get_employee_by_id(employee_id)

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee ID not found."
            }), 404

        # =====================================================
        # CHECK EXISTING ASSIGNMENT
        # =====================================================

        existing = (
            supabase
            .table("project_team_members")
            .select("id")
            .eq("project_id", project_id)
            .eq("employee_id", employee_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            return jsonify({
                "success": False,
                "message": (
                    "Employee is already assigned "
                    "to this project."
                )
            }), 409

        # =====================================================
        # CREATE TEAM MEMBER ROW
        # =====================================================

        row = {
            "project_id": project_id,
            "employee_id": employee_id,
            "employee_name": employee.get(
                "employee_name",
                employee.get("name", "")
            ),
            "email": employee.get(
                "email",
                ""
            ),
            "role": employee.get(
                "role",
                ""
            ),
            "department": employee.get(
                "department",
                ""
            ),
            "experience_level": employee.get(
                "experience_level",
                "Junior"
            ),
            "years_experience": employee.get(
                "years_experience",
                0
            ),
            "skills": employee.get(
                "skills",
                ""
            )
        }

        # =====================================================
        # INSERT EMPLOYEE
        # =====================================================

        insert_response = (
            supabase
            .table("project_team_members")
            .insert(row)
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError(
                "Employee could not be added to the project."
            )

        # =====================================================
        # RECALCULATE AND SAVE SKILL METRICS
        # =====================================================

        skill_metrics = (
            update_project_skill_metrics(
                project_id
            )
        )

        return jsonify({
            "success": True,
            "employee": row,
            "skill_metrics": skill_metrics,
            "message": "Employee assigned."
        }), 201

    except Exception as error:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500
       
# =============================================================
# REMOVE EMPLOYEE FROM PROJECT
# =============================================================

@project_details_bp.route(
    "/api/project/<project_id>/employees/<employee_id>",
    methods=["DELETE"]
)

def remove_project_employee(
    project_id,
    employee_id
):

    try:

        # =====================================================
        # REMOVE EMPLOYEE FROM PROJECT
        # =====================================================

        response = (
            supabase
            .table("project_team_members")
            .delete()
            .eq("project_id", project_id)
            .eq("employee_id", employee_id)
            .execute()
        )

        # =====================================================
        # CHECK WHETHER EMPLOYEE WAS FOUND
        # =====================================================

        if not response.data:
            return jsonify({
                "success": False,
                "message": (
                    "Employee assignment not found."
                )
            }), 404

        # =====================================================
        # RECALCULATE AND SAVE SKILL METRICS
        # =====================================================

        skill_metrics = (
            update_project_skill_metrics(
                project_id
            )
        )

        return jsonify({
            "success": True,
            "skill_metrics": skill_metrics
        }), 200

    except Exception as error:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500