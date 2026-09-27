from datetime import datetime, date

from backend.supabase_client import supabase


def refresh_project_task_metrics(project_id):

    """
    Recalculate project execution metrics directly
    from the current Tasks table.
    """

    # ========================================================
    # GET CURRENT TASKS
    # ========================================================

    response = (
        supabase
        .table("Tasks")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )

    tasks = response.data or []

    print(
        f"[PROJECT METRICS] project_id={project_id}, "
        f"tasks_found={len(tasks)}"
    )

    # ========================================================
    # BASIC COUNTS
    # ========================================================

    total_tasks = len(tasks)

    completed_tasks = sum(
        1
        for task in tasks
        if str(
            task.get("status", "")
        ).upper() == "CLOSED"
    )

    pending_tasks = max(
        total_tasks - completed_tasks,
        0
    )

    # ========================================================
    # OVERDUE TASKS
    # ========================================================

    today = date.today()

    overdue_tasks = 0
    total_delay_days = 0

    for task in tasks:

        status = str(
            task.get("status", "")
        ).upper()

        deadline = task.get("deadline")

        # CLOSED tasks cannot be overdue
        if status == "CLOSED":
            continue

        if not deadline:
            continue

        try:

            deadline_date = datetime.strptime(
                str(deadline)[:10],
                "%Y-%m-%d"
            ).date()

        except (ValueError, TypeError):

            continue

        if deadline_date < today:

            overdue_tasks += 1

            delay_days = (
                today - deadline_date
            ).days

            total_delay_days += delay_days

    # ========================================================
    # PERCENTAGES
    # ========================================================

    completion_percentage = (
        completed_tasks / total_tasks * 100
        if total_tasks > 0
        else 0
    )

    delay_percentage = (
        overdue_tasks / total_tasks * 100
        if total_tasks > 0
        else 0
    )

    average_delay_days = (
        total_delay_days / overdue_tasks
        if overdue_tasks > 0
        else 0
    )

    # ========================================================
    # PROJECT PROGRESS
    # ========================================================

    if total_tasks == 0:

        project_progress = "Not Started"

    elif completed_tasks == total_tasks:

        project_progress = "Completed"

    elif completed_tasks > 0:

        project_progress = "In Progress"

    else:

        project_progress = "Not Started"

    # ========================================================
    # EFFORT
    # ========================================================

    estimated_effort_hours = sum(
        float(
            task.get("estimated_hours") or 0
        )
        for task in tasks
    )

    actual_effort_hours = sum(
        float(
            task.get("actual_hours") or 0
        )
        for task in tasks
    )

    # ========================================================
    # PROJECT METRICS
    # ========================================================

    project_metrics = {

        "total_tasks":
            total_tasks,

        "completed_tasks":
            completed_tasks,

        "pending_tasks":
            pending_tasks,

        "overdue_tasks":
            overdue_tasks,

        "completion_percentage":
            round(
                completion_percentage,
                2
            ),

        "delay_percentage":
            round(
                delay_percentage,
                2
            ),

        "estimated_effort_hours":
            round(
                estimated_effort_hours,
                2
            ),

        "actual_effort_hours":
            round(
                actual_effort_hours,
                2
            ),

        "project_progress":
            project_progress
    }

    # ========================================================
    # UPDATE PROJECT TABLE
    # ========================================================

    (
        supabase
        .table("projects")
        .update(project_metrics)
        .eq("id", project_id)
        .execute()
    )

    print(
        "[PROJECT METRICS UPDATED]",
        project_metrics
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        **project_metrics,
        "average_delay_days":
            round(
                average_delay_days,
                2
            )
    }

def save_project(
    project_name,
    project_type,
    team_members,
    clients,
    tasks,
    team_experience,
    pm_experience,
    resume_text,
    project_budget,
    timeline,
    complexity,
    predicted_risk,
    task_summary,
    start_date,
    end_date
):

    # ========================================================
    # PROJECT DETAILS JSON
    # ========================================================

    project_details = {

        "project_name":
            project_name,

        "project_type":
            project_type,

        "start_date":
            start_date,

        "end_date":
            end_date,

        "project_phase":
            "Initiation",

        "team_experience":
            team_experience,

        "project_manager_experience":
            pm_experience,

        "manager_resume":
            resume_text,

        "project_budget":
            project_budget,

        "timeline_months":
            timeline,

        "complexity_score":
            complexity,

        "team_size":
            len(team_members),

        "stakeholder_count":
            len(clients),

        "total_tasks":
            task_summary["total_tasks"],

        "completed_tasks":
            task_summary["completed_tasks"],

        "pending_tasks":
            task_summary["pending_tasks"],

        "overdue_tasks":
            task_summary["overdue_tasks"],

        "completion_percentage":
            task_summary["completion_percentage"],

        "delay_percentage":
            task_summary["delay_percentage"],

        "estimated_effort_hours":
            task_summary["estimated_days"] * 8,

        "actual_effort_hours":
            task_summary["actual_days"] * 8,

        "project_progress":
            task_summary["project_progress"],

        "team_members":
            team_members,

        "clients":
            clients,

        "tasks":
            tasks,

        "team_member_ids": [
            member["employee_id"]
            for member in team_members
        ],

        "stakeholder_ids": [
            client["client_id"]
            for client in clients
        ],

        "predicted_risk":
            predicted_risk,

        "saved_at":
            datetime.now().isoformat()
    }

    # ========================================================
    # PROJECT ROW
    # ========================================================

    project_data = {

        "project_name":
            project_name,

        "project_type":
            project_type,

        "team_size":
            len(team_members),

        "project_budget":
            project_budget,

        "timeline_months":
            timeline,

        "complexity_score":
            complexity,

        "total_tasks":
            task_summary["total_tasks"],

        "completed_tasks":
            task_summary["completed_tasks"],

        "overdue_tasks":
            task_summary["overdue_tasks"],

        "estimated_effort_hours":
            task_summary["estimated_days"] * 8,

        "actual_effort_hours":
            task_summary["actual_days"] * 8,

        "predicted_risk":
            predicted_risk,

        "project_details":
            project_details
    }

    # ========================================================
    # INSERT PROJECT
    # ========================================================

    response = (
        supabase
        .table("projects")
        .insert(project_data)
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Project was not inserted into Supabase."
        )

    project_id = response.data[0]["id"]

    # ========================================================
    # TEAM MEMBERS
    # ========================================================

    if team_members:

        team_rows = []

        for member in team_members:

            team_rows.append({

                "project_id":
                    project_id,

                "employee_id":
                    member["employee_id"],

                "employee_name":
                    member["employee_name"],

                "email":
                    member["email"],

                "role":
                    member["role"],

                "department":
                    member["department"],

                "experience_level":
                    member["experience_level"],

                "years_experience":
                    member["years_experience"],

                "skills":
                    member["skills"]
            })

        (
            supabase
            .table("project_team_members")
            .insert(team_rows)
            .execute()
        )

    # ========================================================
    # CLIENTS
    # ========================================================

    if clients:

        client_rows = []

        for client in clients:

            client_rows.append({

                "project_id":
                    project_id,

                "client_id":
                    client["client_id"],

                "client_name":
                    client["client_name"],

                "organization":
                    client["organization"],

                "role":
                    client["role"],

                "email":
                    client["email"]
            })

        (
            supabase
            .table("project_clients")
            .insert(client_rows)
            .execute()
        )

    # ========================================================
    # RETURN PROJECT ID
    # ========================================================

    return project_id