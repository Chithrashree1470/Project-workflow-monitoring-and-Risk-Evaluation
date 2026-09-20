from flask import request

from backend.master_data import (
    get_employee_by_id,
    get_client_by_id
)
from backend.services.project_risk import safe_float

def read_tasks_from_form():

    task_names = request.form.getlist(
        "Task_Name"
    )

    assignee_ids = request.form.getlist(
        "Task_Assignee_ID"
    )

    stakeholder_ids = request.form.getlist(
        "Task_Stakeholder_ID"
    )

    estimated_days = request.form.getlist(
        "Task_Estimated_Days"
    )

    actual_days = request.form.getlist(
        "Task_Actual_Days"
    )

    statuses = request.form.getlist(
        "Task_Status"
    )

    tasks = []

    for index, task_name in enumerate(task_names):

        task_name = (
            task_name or ""
        ).strip()

        if not task_name:
            continue

        assignee = (
            assignee_ids[index]
            if index < len(assignee_ids)
            else ""
        )

        stakeholder = (
            stakeholder_ids[index]
            if index < len(stakeholder_ids)
            else ""
        )

        estimated = (
            estimated_days[index]
            if index < len(estimated_days)
            else 0
        )

        actual = (
            actual_days[index]
            if index < len(actual_days)
            else 0
        )

        status = (
            statuses[index]
            if index < len(statuses)
            else "Pending"
        )

        tasks.append({

            "task_name":
                task_name,

            "assignee_id":
                assignee.strip(),

            "stakeholder_id":
                stakeholder.strip(),

            "estimated_days":
                safe_float(estimated),

            "actual_days":
                safe_float(actual),

            "status":
                status.strip()

        })

    return tasks


# ============================================================
# TEAM MEMBERS
# ============================================================

def read_team_members():
    employee_ids = request.form.getlist(
        "Employee_ID"
    )

    members = []
    seen_ids = set()

    for employee_id in employee_ids:
        employee_id = (employee_id or "").strip()

        if not employee_id or employee_id in seen_ids:
            continue

        employee = get_employee_by_id(employee_id)

        if not employee:
            raise ValueError(
                f"Employee ID '{employee_id}' was not found in the employee master table."
            )

        seen_ids.add(employee_id)

        members.append({
            "employee_id": employee_id,
            "employee_name": (
                employee.get("employee_name")
                or employee.get("name")
                or ""
            ).strip(),
            "email": (
                employee.get("email")
                or ""
            ).strip(),
            "role": (
                employee.get("role")
                or ""
            ).strip(),
            "department": (
                employee.get("department")
                or ""
            ).strip(),
            "experience_level": (
                employee.get("experience_level")
                or "Junior"
            ).strip(),
            "years_experience": safe_float(
                employee.get("years_experience", 0)
            ),
            "skills": (
                employee.get("skills")
                or ""
            ).strip()
        })

    return members



# ============================================================
# CLIENTS
# ============================================================

def read_clients():
    client_ids = request.form.getlist(
        "Client_ID"
    )

    clients = []
    seen_ids = set()

    for client_id in client_ids:
        client_id = (client_id or "").strip()

        if not client_id or client_id in seen_ids:
            continue

        client = get_client_by_id(client_id)

        if not client:
            raise ValueError(
                f"Client ID '{client_id}' was not found in the client master table."
            )

        seen_ids.add(client_id)

        clients.append({
            "client_id": client_id,
            "client_name": (
                client.get("client_name")
                or client.get("name")
                or ""
            ).strip(),
            "organization": (
                client.get("organization")
                or ""
            ).strip(),
            "role": (
                client.get("role")
                or ""
            ).strip(),
            "email": (
                client.get("email")
                or ""
            ).strip()
        })

    return clients
