import os
from datetime import datetime, timezone
from pathlib import Path
from backend.services.project_service import refresh_project_task_metrics
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from supabase import create_client
from .task_risk import predict_task_risk_internal
from backend.services.project_service import (
    refresh_project_task_metrics
)

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
    "status",
    "story_points",
    "sprint"
]

ALLOWED_STATUSES = [
    "TO_DO",
    "IN_PROGRESS",
    "IN_REVIEW",
    "CLOSED"
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
    Trigger the task-risk prediction using the current task data.
    """

    task_id = task["task_id"]

    prediction_data = {
        "project_id": task["project_id"],
        "issue_id": task_id,

        "issue_type": task.get("task_type"),
        "priority": task.get("priority"),
        "status": task.get("status"),

        "story_points": task.get("story_points"),
        "story_points_missing": (
            1 if task.get("story_points") is None else 0
        ),

        "timespent": task.get("actual_hours") or 0,

        "assignee": task.get("assigned_to"),
        "sprint": task.get("sprint"),

        # Initial values.
        # These will be calculated properly from TaskHistory
        # once the task has changes.
        "task_age_days": 0,
        "status_change_count": 0,
        "priority_change_count": 0,
        "assignee_change_count": 0,
        "story_point_change_count": 0,
        "estimate_change_count": 0,
        "changes_last_7_days": 0
    }

    response = (
        supabase
        .table("task_risk_prediction")
        .select("issue_id")
        .eq("issue_id", task_id)
        .limit(1)
        .execute()
    )

    # The prediction endpoint itself handles the actual model
    # prediction. This helper only prepares the data.
    return prediction_data

# ============================================================
# CREATE TASK
# ============================================================

@tasks_bp.route("", methods=["POST"])
def create_task():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error":
                    "Request body is required."
            }), 400

        # ====================================================
        # CLEAN TASK DATA
        # ====================================================

        task_data = clean_task_data(
            data,
            partial=False
        )

        # ====================================================
        # DEFAULT WEIGHT
        # ====================================================

        if task_data.get("weight") is None:

            weight_map = {
                "Low": 1,
                "Medium": 2,
                "High": 4,
                "Critical": 6
            }

            task_data["weight"] = (
                weight_map.get(
                    task_data.get("priority"),
                    1
                )
            )

        if task_data.get("actual_hours") is None:

            task_data["actual_hours"] = None

        # ====================================================
        # INSERT TASK
        # ====================================================

        response = (
            supabase
            .table("Tasks")
            .insert(task_data)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Task could not be created."
            }), 500

        task = response.data[0]

        project_id = task["project_id"]

        print(
            f"[TASK CREATED] "
            f"task_id={task['task_id']} "
            f"project_id={project_id}"
        )

        # ====================================================
        # TASK HISTORY
        # ====================================================

        create_history(
            task_id=task["task_id"],
            updated_by=task_data["created_by"],
            change_type="TASK_CREATED",
            previous_status=None,
            new_status=task.get("status"),
            remarks="Task created"
        )

        # ====================================================
        # INITIAL TASK RISK
        # ====================================================

        prediction_data = {

            "project_id":
                task["project_id"],

            "issue_id":
                task["task_id"],

            "issue_type":
                task.get("task_type"),

            "priority":
                task.get("priority"),

            "status":
                task.get("status"),

            "story_points":
                task.get("story_points"),

            "story_points_missing":
                (
                    1
                    if task.get("story_points") is None
                    else 0
                ),

            "timespent":
                (
                    task.get("actual_hours")
                    or 0
                ),

            "assignee":
                task.get("assigned_to"),

            "sprint":
                task.get("sprint"),

            "task_age_days":
                0,

            "status_change_count":
                0,

            "priority_change_count":
                0,

            "assignee_change_count":
                0,

            "story_point_change_count":
                0,

            "estimate_change_count":
                0,

            "changes_last_7_days":
                0
        }

        risk_result = (
            predict_task_risk_internal(
                prediction_data
            )
        )

        # ====================================================
        # REFRESH PROJECT METRICS
        # ====================================================

        project_metrics = (
            refresh_project_task_metrics(
                project_id
            )
        )

        print(
            "[CREATE] PROJECT METRICS:",
            project_metrics
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "message":
                "Task created successfully.",

            "task":
                task,

            "risk":
                risk_result,

            "project_metrics":
                project_metrics

        }), 201

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        import traceback

        traceback.print_exc()

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
                "error":
                    "Request body is required."
            }), 400

        # ====================================================
        # GET EXISTING TASK
        # ====================================================

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
                "error":
                    "Task not found."
            }), 404

        existing_task = (
            existing_response.data[0]
        )

        project_id = (
            existing_task["project_id"]
        )

        # ====================================================
        # CLEAN UPDATE
        # ====================================================

        update_data = clean_task_data(
            data,
            partial=True
        )

        if not update_data:

            return jsonify({
                "error":
                    "No valid task fields provided."
            }), 400

        # ====================================================
        # STATUS INFORMATION
        # ====================================================

        updated_by = data.get(
            "updated_by",
            data.get("created_by")
        )

        previous_status = (
            existing_task.get("status")
        )

        new_status = update_data.get(
            "status",
            previous_status
        )

        # ====================================================
        # COMPLETED_AT
        # ====================================================

        if (
            new_status == "CLOSED"
            and previous_status != "CLOSED"
            and "completed_at"
            not in update_data
        ):

            update_data["completed_at"] = (
                utc_now()
            )

        elif (
            new_status != "CLOSED"
            and previous_status == "CLOSED"
        ):

            update_data["completed_at"] = None

        # ====================================================
        # UPDATE TASK
        # ====================================================

        response = (
            supabase
            .table("Tasks")
            .update(update_data)
            .eq("task_id", task_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Task could not be updated."
            }), 500

        updated_task = response.data[0]

        # ====================================================
        # TASK HISTORY - STATUS
        # ====================================================

        if (
            "status" in update_data
            and previous_status != new_status
        ):

            if new_status == "CLOSED":

                change_type = (
                    "TASK_COMPLETED"
                )

            elif (
                previous_status == "CLOSED"
                and new_status != "CLOSED"
            ):

                change_type = (
                    "TASK_REOPENED"
                )

            else:

                change_type = (
                    "STATUS_CHANGE"
                )

            if updated_by:

                create_history(
                    task_id=task_id,
                    updated_by=updated_by,
                    change_type=change_type,
                    previous_status=previous_status,
                    new_status=new_status,
                    remarks="Task status updated"
                )

        # ====================================================
        # TASK HISTORY - ASSIGNMENT
        # ====================================================

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

        # ====================================================
        # TASK HISTORY - PRIORITY
        # ====================================================

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

        # ====================================================
        # REFRESH PROJECT METRICS
        # ====================================================

        project_metrics = (
            refresh_project_task_metrics(
                project_id
            )
        )

        print(
            "[UPDATE] PROJECT METRICS:",
            project_metrics
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "message":
                "Task updated successfully.",

            "task":
                updated_task,

            "project_metrics":
                project_metrics

        }), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# DELETE TASK
# ============================================================

@tasks_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):

    try:

        # ====================================================
        # GET TASK
        # ====================================================

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
                "error":
                    "Task not found."
            }), 404

        task = existing_response.data[0]

        project_id = (
            task.get("project_id")
        )

        # ====================================================
        # DELETE TASK
        # ====================================================

        response = (
            supabase
            .table("Tasks")
            .delete()
            .eq("task_id", task_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Task could not be deleted."
            }), 500

        # ====================================================
        # REFRESH PROJECT METRICS
        # ====================================================

        project_metrics = (
            refresh_project_task_metrics(
                project_id
            )
        )

        print(
            "[DELETE] PROJECT METRICS:",
            project_metrics
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "message":
                "Task deleted successfully.",

            "task_id":
                task_id,

            "project_id":
                project_id,

            "project_metrics":
                project_metrics

        }), 200

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

    try:

        # ====================================================
        # GET TASK
        # ====================================================

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
                "error":
                    "Task not found."
            }), 404

        task = existing_response.data[0]

        project_id = (
            task.get("project_id")
        )

        # ====================================================
        # DELETE TASK
        # ====================================================

        response = (
            supabase
            .table("Tasks")
            .delete()
            .eq("task_id", task_id)
            .execute()
        )

        if not response.data:

            return jsonify({
                "error":
                    "Task could not be deleted."
            }), 500

        # ====================================================
        # REFRESH PROJECT METRICS
        # ====================================================

        project_metrics = (
            refresh_project_task_metrics(
                project_id
            )
        )

        print(
            "[DELETE] PROJECT METRICS:",
            project_metrics
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "message":
                "Task deleted successfully.",

            "task_id":
                task_id,

            "project_id":
                project_id,

            "project_metrics":
                project_metrics

        }), 200

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

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

        # Task-risk records are owned by task_risk.py.
        # Do not query that table here because its issue_id is an
        # integer model identifier, while Tasks.task_id is a UUID.

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
        
        # ----------------------------------------------------
        # REFRESH PROJECT EXECUTION METRICS
        # ----------------------------------------------------

        project_metrics = refresh_project_task_metrics(
            task["project_id"]
        )

        return jsonify({
            "message": "Task deleted successfully.",
            "task_id": task_id,
            "project_id": task["project_id"],
            "project_metrics": project_metrics
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500