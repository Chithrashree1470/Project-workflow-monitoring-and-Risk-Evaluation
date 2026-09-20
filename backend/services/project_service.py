from datetime import datetime

from backend.supabase_client import supabase

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
            task_summary[
                "total_tasks"
            ],

        "completed_tasks":
            task_summary[
                "completed_tasks"
            ],

        "pending_tasks":
            task_summary[
                "pending_tasks"
            ],

        "overdue_tasks":
            task_summary[
                "overdue_tasks"
            ],

        "completion_percentage":
            task_summary[
                "completion_percentage"
            ],

        "delay_percentage":
            task_summary[
                "delay_percentage"
            ],

        "estimated_effort_hours":
            task_summary[
                "estimated_days"
            ] * 8,

        "actual_effort_hours":
            task_summary[
                "actual_days"
            ] * 8,

        "project_progress":
            task_summary[
                "project_progress"
            ],

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
            task_summary[
                "total_tasks"
            ],

        "completed_tasks":
            task_summary[
                "completed_tasks"
            ],

        "overdue_tasks":
            task_summary[
                "overdue_tasks"
            ],

        "estimated_effort_hours":
            task_summary[
                "estimated_days"
            ] * 8,

        "actual_effort_hours":
            task_summary[
                "actual_days"
            ] * 8,

        "predicted_risk":
            predicted_risk,

        "project_details":
            project_details

    }

    response = (

        supabase

        .table("projects")

        .insert(
            project_data
        )

        .execute()

    )

    if not response.data:

        raise RuntimeError(
            "Project was not inserted into Supabase."
        )

    project_id = (
        response.data[0]["id"]
    )

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
                    member[
                        "employee_id"
                    ],

                "employee_name":
                    member[
                        "employee_name"
                    ],

                "email":
                    member[
                        "email"
                    ],

                "role":
                    member[
                        "role"
                    ],

                "department":
                    member[
                        "department"
                    ],

                "experience_level":
                    member[
                        "experience_level"
                    ],

                "years_experience":
                    member[
                        "years_experience"
                    ],

                "skills":
                    member[
                        "skills"
                    ]

            })

        supabase.table(
            "project_team_members"
        ).insert(
            team_rows
        ).execute()

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
                    client[
                        "client_id"
                    ],

                "client_name":
                    client[
                        "client_name"
                    ],

                "organization":
                    client[
                        "organization"
                    ],

                "role":
                    client[
                        "role"
                    ],

                "email":
                    client[
                        "email"
                    ]

            })

        supabase.table(
            "project_clients"
        ).insert(
            client_rows
        ).execute()

    return project_id
