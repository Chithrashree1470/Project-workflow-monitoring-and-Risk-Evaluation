import json
import traceback

from flask import Blueprint, render_template, session, request, jsonify

from backend.supabase_client import supabase
from backend.master_data import get_employee_by_id

from backend.services.project_service import (
    refresh_project_task_metrics,
)
from backend.services.project_skill import (
    update_project_skill_metrics,
)

project_details_bp = Blueprint(
    "project_details",
    __name__,
)


def _load_project(project_id):
    response = (
        supabase.table("projects")
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
        except (ValueError, TypeError):
            details = {}

    if not isinstance(details, dict):
        details = {}

    return project, details


def _load_children(project_id, details):
    # Load project team members.
    try:
        team = (
            supabase.table("project_team_members")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        print("Project team lookup error:", error)
        team = details.get("team_members", [])

    # Load project clients.
    try:
        clients = (
            supabase.table("project_clients")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception as error:
        print("Project client lookup error:", error)
        clients = details.get("clients", [])

    # Load project tasks.
    try:
        all_tasks = (
            supabase.table("Tasks")
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

    # Include employees assigned to tasks in the displayed team.
    # This does not create a project_team_members database record.
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
                continue

            team.append({
                "project_id": project_id,
                "employee_id": employee.get(
                    "employee_id", employee_id
                ),
                "employee_name": employee.get(
                    "employee_name",
                    employee.get("name", ""),
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
                "skills": employee.get("skills", ""),
            })

            known_employee_ids.add(employee_id)

        except Exception as error:
            print(
                f"Unable to load assigned employee {employee_id}:",
                error,
            )

    return team, clients, all_tasks


def _load_task_predictions(project_id):
    try:
        rows = (
            supabase.table("task_risk_prediction")
            .select("issue_id, risk_label, risk_score")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )

        return {
            str(row.get("issue_id")): row
            for row in rows
        }

    except Exception as error:
        print("Task prediction lookup error:", error)
        return {}


def _load_dynamic_risk(project_id):
    # Do not depend on the optional calculated_at column.
    try:
        rows = (
            supabase.table("project_dynamic_risk")
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
    if value is None:
        return fallback

    if isinstance(value, (list, tuple)):
        value = value[0] if value else fallback

    label = str(value).strip()

    if label.startswith("[") and label.endswith("]"):
        label = label[1:-1].strip()

    label = label.strip("'\" ").strip()

    return label or fallback


@project_details_bp.route("/project/<project_id>")
def project_details(project_id):
    try:
        # Load project and its stored details.
        project, details = _load_project(project_id)

        if not project:
            return "Project not found.", 404

        # Load team, clients, and tasks.
        team_members, clients, all_tasks = _load_children(
            project_id,
            details,
        )

        # Refresh execution metrics from the current Tasks table.
        try:
            metrics = refresh_project_task_metrics(project_id)

            if metrics:
                project.update(metrics)

        except Exception as error:
            print("Project metrics refresh error:", error)

        # Load current risk and task predictions.
        dynamic_risk = _load_dynamic_risk(project_id)
        task_predictions = _load_task_predictions(project_id)

        # Preserve the existing manager/employee/client view switching.
        access_key = f"project_access_{project_id}"
        access = session.get(access_key) or {}

        requested_view = (
            request.args.get("view") or ""
        ).strip().lower()

        if requested_view in {"manager", "employee", "client"}:
            role = requested_view

            if role == "employee":
                subject_id = (
                    team_members[0].get("employee_id")
                    if team_members
                    else None
                )
            elif role == "client":
                subject_id = (
                    clients[0].get("client_id")
                    if clients
                    else None
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
                role = "manager"
                subject_id = None

            session[access_key] = {
                "role": role,
                "subject_id": subject_id,
            }

        # Employee view only displays tasks assigned to that employee.
        if role == "employee":
            visible_tasks = [
                task
                for task in all_tasks
                if str(task.get("assigned_to") or "")
                == str(subject_id or "")
            ]
        else:
            visible_tasks = all_tasks

        # Display dynamic risk when available; otherwise use the
        # original project-level prediction.
        raw_current_risk = (
            dynamic_risk.get("risk_level")
            if dynamic_risk
            else project.get("predicted_risk")
        )

        # Use hybrid risk as a fallback if the primary value is absent.
        if not raw_current_risk:
            raw_current_risk = (
                project.get("hybrid_risk_level")
            )

        project["current_risk"] = _normalise_risk_label(
            raw_current_risk,
            fallback="Low",
        )

        # Recalculate hybrid-skill coverage and skill gaps.
        try:
            skill_metrics = update_project_skill_metrics(
                project_id
            ) or {}

            project["skill_coverage"] = skill_metrics.get(
                "skill_coverage",
                project.get("skill_coverage"),
            )
            project["skill_gap"] = skill_metrics.get(
                "skill_gap",
                project.get("skill_gap"),
            )

        except Exception as error:
            print("Project skill metrics error:", error)

        # Build details expected by the project-details template.
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
        traceback.print_exc()

        return (
            "Unable to load project details: " + str(error),
            500,
        )


# =============================================================
# ADD EMPLOYEE TO PROJECT
# =============================================================

@project_details_bp.route(
    "/api/project/<project_id>/employees",
    methods=["POST"],
)
def add_project_employee(project_id):
    try:
        # Verify that the project exists.
        project_response = (
            supabase.table("projects")
            .select("id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )

        if not project_response.data:
            return jsonify({
                "success": False,
                "message": "Project not found.",
            }), 404

        # Validate the employee ID.
        data = request.get_json(silent=True) or {}
        employee_id = str(
            data.get("employee_id") or ""
        ).strip()

        if not employee_id:
            return jsonify({
                "success": False,
                "message": "Employee ID is required.",
            }), 400

        employee = get_employee_by_id(employee_id)

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee ID not found.",
            }), 404

        # Prevent duplicate project-team assignments.
        existing = (
            supabase.table("project_team_members")
            .select("employee_id")
            .eq("project_id", project_id)
            .eq("employee_id", employee_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            return jsonify({
                "success": False,
                "message": "Employee is already assigned to this project.",
            }), 409

        # Save the employee's project-team record.
        row = {
            "project_id": project_id,
            "employee_id": employee_id,
            "employee_name": employee.get(
                "employee_name",
                employee.get("name", ""),
            ),
            "email": employee.get("email", ""),
            "role": employee.get("role", ""),
            "department": employee.get("department", ""),
            "experience_level": employee.get(
                "experience_level", "Junior"
            ),
            "years_experience": employee.get(
                "years_experience", 0
            ),
            "skills": employee.get("skills", ""),
        }

        insert_response = (
            supabase.table("project_team_members")
            .insert(row)
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError(
                "Employee could not be added to the project."
            )

        # Recalculate hybrid-skill metrics after the team changes.
        skill_metrics = update_project_skill_metrics(project_id)

        return jsonify({
            "success": True,
            "employee": row,
            "skill_metrics": skill_metrics,
            "message": "Employee assigned successfully.",
        }), 201

    except Exception as error:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(error),
        }), 500


# =============================================================
# REMOVE EMPLOYEE FROM PROJECT
# =============================================================

@project_details_bp.route(
    "/api/project/<project_id>/employees/<employee_id>",
    methods=["DELETE"],
)
def remove_project_employee(project_id, employee_id):
    try:
        response = (
            supabase.table("project_team_members")
            .delete()
            .eq("project_id", project_id)
            .eq("employee_id", employee_id)
            .execute()
        )

        if not response.data:
            return jsonify({
                "success": False,
                "message": "Employee assignment not found.",
            }), 404

        # Recalculate hybrid-skill metrics after removal.
        skill_metrics = update_project_skill_metrics(project_id)

        return jsonify({
            "success": True,
            "skill_metrics": skill_metrics,
            "message": "Employee removed from project.",
        }), 200

    except Exception as error:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(error),
        }), 500