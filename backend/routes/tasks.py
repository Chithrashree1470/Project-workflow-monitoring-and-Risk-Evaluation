import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY missing")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# BLUEPRINT
# ============================================================

tasks_bp = Blueprint(
    "tasks",
    __name__,
    url_prefix="/api/tasks"
)


# ============================================================
# CONSTANTS
# ============================================================

TASK_FIELDS = [
    "project_id",
    "assigned_to",
    "created_by",
    "title",
    "description",
    "task_type",
    "priority",
    "weight",
    "estimated_hours",
    "actual_hours",
    "start_date",
    "deadline",
    "completed_at",
    "status"
]

ALLOWED_STATUSES = [
    "TODO",
    "IN_PROGRESS",
    "DONE"
]

ALLOWED_PRIORITIES = [
    "Low",
    "Medium",
    "High",
    "Critical"
]


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clean_task_data(data, partial=False):
    """
    Extract only fields belonging to the Tasks table.
    """

    if not data:
        return {}

    task_data = {}

    for field in TASK_FIELDS:

        if field in data:
            value = data[field]

            # Convert empty strings to None
            if value == "":
                value = None

            task_data[field] = value

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not partial:

        required_fields = [
            "project_id",
            "created_by",
            "title",
            "priority",
            "status",
            "deadline",
            "estimated_hours"
        ]

        missing = [
            field
            for field in required_fields
            if not task_data.get(field)
        ]

        if missing:
            raise ValueError(
                "Missing required fields: "
                + ", ".join(missing)
            )

    if "status" in task_data and task_data["status"]:

        if task_data["status"] not in ALLOWED_STATUSES:
            raise ValueError(
                f"Invalid status. Allowed values: "
                f"{', '.join(ALLOWED_STATUSES)}"
            )

    if "priority" in task_data and task_data["priority"]:

        if task_data["priority"] not in ALLOWED_PRIORITIES:
            raise ValueError(
                f"Invalid priority. Allowed values: "
                f"{', '.join(ALLOWED_PRIORITIES)}"
            )

    return task_data


def create_history(
    task_id,
    updated_by,
    change_type,
    previous_status=None,
    new_status=None,
    remarks=None
):
    """
    Insert a TaskHistory record.
    """

    history = {
        "task_id": task_id,
        "updated_by": updated_by,
        "change_type": change_type,
        "previous_status": previous_status,
        "new_status": new_status,
        "remarks": remarks,
        "updated_at": utc_now()
    }

    return (
        supabase
        .table("TaskHistory")
        .insert(history)
        .execute()
    )


def trigger_task_risk_prediction(task):
    """
    Placeholder for dynamic task-risk prediction.

    The actual ML prediction remains inside task_risk.py.
    The frontend can call /api/task-risk/predict after
    successful task creation/update.
    """

    return {
        "project_id": task.get("project_id"),
        "issue_id": task.get("task_id")
    }


# ============================================================
# CREATE TASK
# ============================================================

@tasks_bp.route("", methods=["POST"])
def create_task():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Request body is required."
            }), 400

        task_data = clean_task_data(
            data,
            partial=False
        )

        # ----------------------------------------------------
        # Default values
        # ----------------------------------------------------

        if task_data.get("weight") is None:

            weight_map = {
                "Low": 1,
                "Medium": 2,
                "High": 4,
                "Critical": 6
            }

            task_data["weight"] = weight_map.get(
                task_data.get("priority"),
                1
            )

        if task_data.get("actual_hours") is None:
            task_data["actual_hours"] = None

        # ----------------------------------------------------
        # Insert task
        # ----------------------------------------------------

        response = (
            supabase
            .table("Tasks")
            .insert(task_data)
            .execute()
        )

        if not response.data:
            return jsonify({
                "error": "Task could not be created."
            }), 500

        task = response.data[0]

        # ----------------------------------------------------
        # Task history
        # ----------------------------------------------------

        create_history(
            task_id=task["task_id"],
            updated_by=task_data["created_by"],
            change_type="TASK_CREATED",
            previous_status=None,
            new_status=task.get("status"),
            remarks="Task created"
        )

        return jsonify({
            "message": "Task created successfully.",
            "task": task
        }), 201

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# GET ALL TASKS FOR A PROJECT
# ============================================================

@tasks_bp.route("/project/<project_id>", methods=["GET"])
def get_project_tasks(project_id):

    try:

        response = (
            supabase
            .table("Tasks")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=False)
            .execute()
        )

        return jsonify({
            "project_id": project_id,
            "tasks": response.data or [],
            "count": len(response.data or [])
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# GET SINGLE TASK
# ============================================================

@tasks_bp.route("/<task_id>", methods=["GET"])
def get_task(task_id):

    try:

        response = (
            supabase
            .table("Tasks")
            .select("*")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error": "Task not found."
            }), 404

        return jsonify({
            "task": response.data[0]
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# UPDATE TASK
# ============================================================

@tasks_bp.route("/<task_id>", methods=["PUT"])
def update_task(task_id):

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Request body is required."
            }), 400

        # ----------------------------------------------------
        # Get existing task
        # ----------------------------------------------------

        existing_response = (
            supabase
            .table("Tasks")
            .select("*")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )

        if not existing_response.data:

            return jsonify({
                "error": "Task not found."
            }), 404

        existing_task = existing_response.data[0]

        # ----------------------------------------------------
        # Clean update data
        # ----------------------------------------------------

        update_data = clean_task_data(
            data,
            partial=True
        )

        if not update_data:

            return jsonify({
                "error": "No valid task fields provided."
            }), 400

        # ----------------------------------------------------
        # Detect important changes
        # ----------------------------------------------------

        updated_by = data.get(
            "updated_by",
            data.get("created_by")
        )

        previous_status = existing_task.get("status")
        new_status = update_data.get(
            "status",
            previous_status
        )

        # ----------------------------------------------------
        # Update completed_at automatically
        # ----------------------------------------------------

        if (
            new_status == "DONE"
            and previous_status != "DONE"
            and "completed_at" not in update_data
        ):

            update_data["completed_at"] = utc_now()

        elif (
            new_status != "DONE"
            and previous_status == "DONE"
        ):

            update_data["completed_at"] = None

        # ----------------------------------------------------
        # Update task
        # ----------------------------------------------------

        response = (
            supabase
            .table("Tasks")
            .update(update_data)
            .eq("task_id", task_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error": "Task could not be updated."
            }), 500

        updated_task = response.data[0]

        # ----------------------------------------------------
        # Task history
        # ----------------------------------------------------

        if (
            "status" in update_data
            and previous_status != new_status
        ):

            if new_status == "DONE":

                change_type = "TASK_COMPLETED"

            elif (
                previous_status == "DONE"
                and new_status != "DONE"
            ):

                change_type = "TASK_REOPENED"

            else:

                change_type = "STATUS_CHANGE"

            if updated_by:

                create_history(
                    task_id=task_id,
                    updated_by=updated_by,
                    change_type=change_type,
                    previous_status=previous_status,
                    new_status=new_status,
                    remarks="Task status updated"
                )

        if (
            "assigned_to" in update_data
            and
            update_data.get("assigned_to")
            != existing_task.get("assigned_to")
        ):

            if updated_by:

                create_history(
                    task_id=task_id,
                    updated_by=updated_by,
                    change_type="ASSIGNMENT_CHANGE",
                    remarks="Task assignment updated"
                )

        if (
            "priority" in update_data
            and
            update_data.get("priority")
            != existing_task.get("priority")
        ):

            if updated_by:

                create_history(
                    task_id=task_id,
                    updated_by=updated_by,
                    change_type="PRIORITY_CHANGE",
                    remarks="Task priority updated"
                )

        return jsonify({
            "message": "Task updated successfully.",
            "task": updated_task
        }), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# DELETE TASK
# ============================================================

@tasks_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):

    try:

        # ----------------------------------------------------
        # Get task first
        # ----------------------------------------------------

        existing_response = (
            supabase
            .table("Tasks")
            .select("*")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )

        if not existing_response.data:

            return jsonify({
                "error": "Task not found."
            }), 404

        task = existing_response.data[0]

        # ----------------------------------------------------
        # Delete current task risk prediction
        # ----------------------------------------------------

        (
            supabase
            .table("task_risk_prediction")
            .delete()
            .eq("issue_id", task_id)
            .execute()
        )

        # ----------------------------------------------------
        # Delete task
        # ----------------------------------------------------

        response = (
            supabase
            .table("Tasks")
            .delete()
            .eq("task_id", task_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error": "Task could not be deleted."
            }), 500

        return jsonify({
            "message": "Task deleted successfully.",
            "task_id": task_id,
            "project_id": task.get("project_id")
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500