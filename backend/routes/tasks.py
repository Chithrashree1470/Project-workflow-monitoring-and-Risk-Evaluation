import os
import json

from datetime import datetime, timezone

from pathlib import Path

from flask import Blueprint, jsonify, request, session

from dotenv import load_dotenv

from supabase import create_client

from .task_risk import predict_task_risk_internal, calculate_project_dynamic_risk
from backend.services.project_risk import refresh_project_catboost_prediction

from backend.services.project_service import refresh_project_task_metrics



# ============================================================

# ENVIRONMENT

# ============================================================


import re

def _task_list_values(value):
    """Convert employee skills/project_types into a normalised list."""
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                values = parsed
            else:
                values = re.split(r"[,;|\n]+", text)
        except (ValueError, TypeError):
            values = re.split(r"[,;|\n]+", text)

    return [str(item).strip() for item in values if str(item).strip()]


def _project_type_for_task_generation(project):
    """Read the project type already stored in the project record."""
    details = project.get("project_details") or {}

    if isinstance(details, str):
        try:
            details = json.loads(details)
        except (ValueError, TypeError):
            details = {}

    return str(
        project.get("project_type")
        or project.get("type")
        or (details.get("project_type") if isinstance(details, dict) else "")
        or (details.get("type") if isinstance(details, dict) else "")
        or ""
    ).strip()


def _suggest_tasks_for_project_type(project_type):
    """Return five editable starter tasks based on the saved project type."""
    project_key = project_type.casefold()

    if any(word in project_key for word in ("web", "software", "application", "app", "saas")):
        tasks = [
            ("Requirements and UI design", "Requirements analysis, UI/UX", "Design"),
            ("Database design and setup", "SQL, database design", "Development"),
            ("Frontend implementation", "HTML, CSS, JavaScript", "Development"),
            ("Backend and API implementation", "Python, Flask, REST API", "Development"),
            ("Testing and deployment", "Testing, debugging, deployment", "Testing"),
        ]
    elif any(word in project_key for word in ("data", "analytics", "machine learning", "ai", "ml")):
        tasks = [
            ("Define data requirements", "Requirements analysis, data analysis", "Planning"),
            ("Prepare and validate data", "Python, SQL, data cleaning", "Data"),
            ("Develop the data or ML pipeline", "Python, data engineering, machine learning", "Development"),
            ("Evaluate results and validate outputs", "Testing, analytics, model evaluation", "Testing"),
            ("Deploy and document the solution", "Deployment, documentation, monitoring", "Deployment"),
        ]
    elif any(word in project_key for word in ("network", "infrastructure", "cloud", "devops")):
        tasks = [
            ("Confirm infrastructure requirements", "Requirements analysis, infrastructure", "Planning"),
            ("Design the environment and architecture", "Cloud, networking, architecture", "Design"),
            ("Configure infrastructure and access", "Networking, security, configuration", "Implementation"),
            ("Run integration and security checks", "Testing, security, troubleshooting", "Testing"),
            ("Deploy and document the environment", "Deployment, monitoring, documentation", "Deployment"),
        ]
    else:
        # General-purpose tasks for other saved project types.
        tasks = [
            ("Confirm requirements and scope", "Requirements analysis, communication", "Planning"),
            ("Prepare the solution design", "Design, documentation", "Design"),
            ("Implement the main deliverable", "Implementation, problem solving", "Implementation"),
            ("Test and resolve issues", "Testing, debugging, quality assurance", "Testing"),
            ("Complete delivery and documentation", "Documentation, deployment, communication", "Delivery"),
        ]

    return [
        {
            "title": title,
            "description": f"Suggested for the {project_type or 'general'} project. Edit this draft to fit the project.",
            "task_type": task_type,
            "required_skills": _task_list_values(skills),
            "priority": "Medium",
            "status": "TO_DO",
            "estimated_hours": 8,
            "actual_hours": 0,
            "deadline": "",
            "assigned_to": "",
        }
        for title, skills, task_type in tasks
    ]


def _employee_recommendations_for_task(project_type, required_skills):
    """Rank employees by project-type match and matching skills."""
    response = supabase.table("employees").select("*").execute()
    employees = response.data or []

    target_type = (project_type or "").strip().casefold()
    required = {skill.casefold() for skill in required_skills}
    recommendations = []

    for employee in employees:
        employee_types = {
            value.casefold()
            for value in _task_list_values(employee.get("project_types"))
        }
        employee_skills = _task_list_values(employee.get("skills"))
        employee_skill_lookup = {skill.casefold(): skill for skill in employee_skills}

        matching_skills = [
            employee_skill_lookup[skill]
            for skill in required
            if skill in employee_skill_lookup
        ]
        type_match = target_type in employee_types

        # Recommend employees with either a matching skill or project type.
        if not type_match and not matching_skills:
            continue

        recommendations.append({
            "employee_id": employee.get("employee_id"),
            "employee_name": employee.get("employee_name") or employee.get("name") or "",
            "skills": employee_skills,
            "project_types": _task_list_values(employee.get("project_types")),
            "matching_skills": matching_skills,
            "project_type_match": type_match,
            "match_count": len(matching_skills) + (1 if type_match else 0),
        })

    recommendations.sort(
        key=lambda employee: (
            -employee["match_count"],
            str(employee.get("employee_id") or ""),
        )
    )
    return recommendations


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





def active_project_role(project_id):

    """

    Return the role for this specific project.



    Project login stores role data in project_access_<project_id>.

    Keep the older project_role key as a compatibility fallback.

    """

    access = session.get(f"project_access_{project_id}") or {}

    role = access.get("role") if isinstance(access, dict) else None

    role = role or session.get("project_role") or ""

    return str(role).strip().lower()





def invalidate_project_risk(project_id):
    """Compatibility helper; preserve prior aggregate for trend calculation."""
    return None


def refresh_project_risks_after_task_change(project_id):
    """Refresh metrics, project CatBoost, all task predictions, and dynamic risk."""
    project_id = int(project_id)
    project_metrics = refresh_project_task_metrics(project_id)

    # Re-run the existing project-level CatBoost model with refreshed task data.
    project_prediction = refresh_project_catboost_prediction(project_id)

    current_tasks = (
        supabase.table("Tasks")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    current_ids = {str(task.get("task_id")) for task in current_tasks}

    # Refresh task-level CatBoost predictions for all remaining tasks. The
    # project aggregator is called once, after all current predictions exist.
    for task in current_tasks:
        trigger_task_risk_prediction(task, refresh_project=False)

    # Remove prediction rows belonging to tasks that were deleted.
    existing_predictions = (
        supabase.table("task_risk_prediction")
        .select("issue_id")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    for prediction in existing_predictions:
        if str(prediction.get("issue_id")) not in current_ids:
            (supabase.table("task_risk_prediction")
             .delete()
             .eq("project_id", project_id)
             .eq("issue_id", prediction.get("issue_id"))
             .execute())

    project_risk = calculate_project_dynamic_risk(project_id)
    return {
        "project_metrics": project_metrics,
        "project_prediction": project_prediction,
        "project_risk": project_risk,
    }


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



def trigger_task_risk_prediction(task, refresh_project=True):

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



    return predict_task_risk_internal(
        prediction_data,
        refresh_project=refresh_project,
    )


@tasks_bp.route("/project/<project_id>/suggestions", methods=["GET"])
def suggest_project_tasks(project_id):
    """Suggest editable task drafts and employee matches without saving tasks."""
    try:
        role = active_project_role(project_id)
        if role != "manager":
            return jsonify({
                "success": False,
                "error": "Task suggestions and final assignment are available only in manager view.",
                "active_role": role or None
            }), 403

        project_response = (
            supabase.table("projects")
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        projects = project_response.data or []
        if not projects:
            return jsonify({"success": False, "error": "Project not found."}), 404

        project_type = _project_type_for_task_generation(projects[0])
        tasks = _suggest_tasks_for_project_type(project_type)
        requested_count = request.args.get("count", default=5, type=int)
        requested_count = max(1, min(requested_count or 5, 30))
        if tasks and requested_count > len(tasks):
            templates = tasks[:]
            while len(tasks) < requested_count:
                source = templates[len(tasks) % len(templates)]
                duplicate = dict(source)
                duplicate["title"] = f"{source['title']} (Part {len(tasks) + 1})"
                tasks.append(duplicate)
        tasks = tasks[:requested_count]
        for task in tasks:
            task["employee_recommendations"] = _employee_recommendations_for_task(
                project_type, task.get("required_skills", [])
            )

        # Full employee list lets the manager manually select any valid employee.
        employee_response = supabase.table("employees").select("*").execute()
        employees = []
        for employee in (employee_response.data or []):
            employee_id = employee.get("employee_id")
            if not employee_id:
                continue
            employees.append({
                "employee_id": employee_id,
                "employee_name": employee.get("employee_name") or employee.get("name") or "",
                "skills": _task_list_values(employee.get("skills")),
                "project_types": _task_list_values(employee.get("project_types"))
            })

        return jsonify({
            "success": True,
            "project_id": project_id,
            "project_type": project_type,
            "tasks": tasks,
            "employees": employees
        }), 200
    except Exception as error:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(error)}), 500


@tasks_bp.route("", methods=["POST"])

def create_task():



    try:

        data = request.get_json()



        if not data:

            return jsonify({

                "error": "Request body is required."

            }), 400



        project_id = data.get("project_id")

        if project_id is None:

            return jsonify({

                "error": "project_id is required."

            }), 400



        role = active_project_role(project_id)

        if role not in {"manager", "employee"}:

            return jsonify({

                "error": "Edit mode is available only to manager or employee views.",

                "active_role": role or None

            }), 403



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



        # The saved task is now part of the current project input. Refresh
        # metrics and risk models below using the latest Tasks table.
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

        # REFRESH PROJECT METRICS

        # ====================================================



        risk_refresh = refresh_project_risks_after_task_change(project_id)
        project_metrics = risk_refresh["project_metrics"]



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



            "risk": risk_refresh["project_risk"],
            "project_prediction": risk_refresh["project_prediction"],



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

# CALCULATE PROJECT RISK FROM CURRENT TASKS

# ============================================================



@tasks_bp.route("/project/<project_id>/calculate-risk", methods=["POST"])

def calculate_project_risk(project_id):

    try:

        active_role = active_project_role(project_id)



        if active_role not in {"manager", "employee"}:

            return jsonify({

                "success": False,

                "error": (

                    "Risk calculation is available only to manager or employee views. "

                    "Please open Project Login and sign in as Manager or Employee for this project."

                ),

                "active_role": active_role or None,

            }), 403

        response = (

            supabase

            .table("Tasks")

            .select("*")

            .eq("project_id", project_id)

            .order("created_at", desc=False)

            .execute()

        )

        tasks = response.data or []



        if not tasks:

            return jsonify({

                "success": False,

                "error": "Add at least one task before calculating execution risk."

            }), 400



        task_results = []

        for task in tasks:

            prediction_data = {

                "project_id": task.get("project_id"),

                "issue_id": task.get("task_id"),

                "issue_type": task.get("task_type"),

                "priority": task.get("priority"),

                "status": task.get("status"),

                "story_points": task.get("story_points"),

                "story_points_missing": 1 if task.get("story_points") is None else 0,

                "timespent": task.get("actual_hours") or 0,

                "assignee": task.get("assigned_to"),

                "sprint": task.get("sprint"),

                "task_age_days": 0,

                "status_change_count": 0,

                "priority_change_count": 0,

                "assignee_change_count": 0,

                "story_point_change_count": 0,

                "estimate_change_count": 0,

                "changes_last_7_days": 0

            }

            task_results.append(predict_task_risk_internal(prediction_data))



        # All task predictions must be saved before aggregating project risk.

        if not task_results:

            return jsonify({

                "success": False,

                "error": "No task-risk predictions were produced. Check the task-risk model and Flask terminal."

            }), 500



        project_risk = calculate_project_dynamic_risk(project_id)

        if not project_risk:

            return jsonify({

                "success": False,

                "error": "Task predictions ran, but no project risk record was produced. Check Supabase table permissions/schema and the Flask terminal."

            }), 500



        project_metrics = refresh_project_task_metrics(project_id)



        return jsonify({

            "success": True,

            "project_id": project_id,

            "task_risks": task_results,

            "project_risk": project_risk,

            "project_metrics": project_metrics,

            "message": "Task risks calculated and project risk saved."

        }), 200



    except ValueError as error:

        return jsonify({"success": False, "error": str(error)}), 400

    except Exception as error:

        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "error": str(error)}), 500





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



        project_id = existing_task["project_id"]



        role = active_project_role(project_id)

        if role not in {"manager", "employee"}:

            return jsonify({

                "error": "Edit mode is available only to manager or employee views.",

                "active_role": role or None

            }), 403



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



        # Updated task data makes existing risk predictions stale.
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



        risk_refresh = refresh_project_risks_after_task_change(project_id)
        project_metrics = risk_refresh["project_metrics"]



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



            "project_metrics": project_metrics,
            "risk": risk_refresh["project_risk"],
            "project_prediction": risk_refresh["project_prediction"]



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



        project_id = task.get("project_id")



        role = active_project_role(project_id)

        if role not in {"manager", "employee"}:

            return jsonify({

                "error": "Edit mode is available only to manager or employee views.",

                "active_role": role or None

            }), 403



        # ====================================================

        # DELETE TASK

        # ====================================================



        # Remove the deleted task's current prediction; retain its history.
        (
            supabase.table("task_risk_prediction")
            .delete()
            .eq("project_id", project_id)
            .eq("issue_id", int(task["task_id"]))
            .execute()
        )

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



        # The deleted task is removed from the current prediction set.
        # Refresh remaining tasks and both project-risk outputs below.
        # ====================================================

        # REFRESH PROJECT METRICS

        # ====================================================



        risk_refresh = refresh_project_risks_after_task_change(project_id)
        project_metrics = risk_refresh["project_metrics"]



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



            "project_metrics": project_metrics,
            "risk": risk_refresh["project_risk"],
            "project_prediction": risk_refresh["project_prediction"]



        }), 200



    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500
