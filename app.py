import os
import json
import re
import joblib
import numpy as np
import pandas as pd

from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)

from dotenv import load_dotenv
from supabase import create_client
from catboost import Pool


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "infrasync-ai-secret-key"
)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be present in .env"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# MODEL
# ============================================================

MODEL_PATH = "catboost_final_model.pkl"
DATASET_PATH = "project_risk_final_clean.csv"

model = joblib.load(MODEL_PATH)

reference_df = pd.read_csv(DATASET_PATH)

MODEL_FEATURES = list(model.feature_names_)

reference_features = reference_df.drop(
    columns=[
        "Project_ID",
        "Risk_Level"
    ],
    errors="ignore"
)


missing = [
    feature
    for feature in MODEL_FEATURES
    if feature not in reference_features.columns
]

if missing:
    raise ValueError(
        "Dataset is missing model features: "
        + ", ".join(missing)
    )


# ============================================================
# DISPLAY NAMES
# ============================================================

DISPLAY = {
    feature: feature.replace("_", " ")
    for feature in MODEL_FEATURES
}


# ============================================================
# CATEGORICAL HELPERS
# ============================================================

def is_categorical(feature):

    return (
        reference_features[feature].dtype == "object"
    )


def dataset_default(feature):

    series = (
        reference_features[feature]
        .dropna()
    )

    if is_categorical(feature):

        if series.empty:
            return ""

        return str(
            series.mode().iloc[0]
        )

    if series.empty:
        return 0.0

    return float(
        series.median()
    )


# ============================================================
# SAFE VALUES
# ============================================================

def safe_float(value, default=0.0):

    try:

        number = float(value)

        if number < 0:
            return 0.0

        return number

    except (
        TypeError,
        ValueError
    ):

        return default


def safe_int(value, default=0):

    try:

        number = int(
            float(value)
        )

        if number < 0:
            return 0

        return number

    except (
        TypeError,
        ValueError
    ):

        return default


# ============================================================
# TIMELINE
# ============================================================

def calculate_timeline(
    start_date,
    end_date
):

    if not start_date or not end_date:
        return 0.0

    try:

        start = datetime.strptime(
            start_date,
            "%Y-%m-%d"
        )

        end = datetime.strptime(
            end_date,
            "%Y-%m-%d"
        )

        if end < start:
            raise ValueError(
                "End Date cannot be before Start Date."
            )

        days = (
            end - start
        ).days

        return round(
            days / 30.44,
            2
        )

    except ValueError as error:

        if "End Date" in str(error):
            raise

        return 0.0


# ============================================================
# READ TASKS
# ============================================================

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



# ============================================================
# EMPLOYEE / CLIENT MASTER DATA
# ============================================================

# These two tables are the master records used by the project form.
# The manager enters only an ID; the application retrieves the
# remaining employee/client information automatically.
EMPLOYEE_MASTER_TABLE = "employees"
CLIENT_MASTER_TABLE = "clients"


def get_employee_by_id(employee_id):
    employee_id = (employee_id or "").strip()

    if not employee_id:
        return None

    response = (
        supabase
        .table(EMPLOYEE_MASTER_TABLE)
        .select("*")
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def get_client_by_id(client_id):
    client_id = (client_id or "").strip()

    if not client_id:
        return None

    response = (
        supabase
        .table(CLIENT_MASTER_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


# ============================================================
# TEAM EXPERIENCE CALCULATION
# ============================================================

def calculate_team_experience(
    team_members
):

    if not team_members:
        return "Junior"

    scores = {

        "Intern": 0.0,
        "Junior": 1.0,
        "Mid": 2.0,
        "Senior": 3.0

    }

    values = []

    for member in team_members:

        level = (
            member
            .get(
                "experience_level",
                "Junior"
            )
            .strip()
        )

        years = safe_float(
            member.get(
                "years_experience",
                0
            )
        )

        if years > 0:

            if years < 1:
                score = 0.0

            elif years < 3:
                score = 1.0

            elif years < 7:
                score = 2.0

            else:
                score = 3.0

        else:

            score = scores.get(
                level,
                1.0
            )

        values.append(score)

    average = (
        sum(values)
        /
        len(values)
    )

    if average < 0.75:
        return "Junior"

    if average < 1.75:
        return "Mixed"

    if average < 2.5:
        return "Senior"

    return "Expert"


# ============================================================
# MANAGER RESUME EXTRACTION
# ============================================================

def extract_resume_text():

    uploaded = request.files.get(
        "Manager_Resume"
    )

    if not uploaded:
        return ""

    if not uploaded.filename:
        return ""

    filename = (
        uploaded.filename
        .lower()
    )

    try:

        if filename.endswith(".txt"):

            return (
                uploaded
                .read()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )

        if filename.endswith(".pdf"):

            from pypdf import PdfReader

            reader = PdfReader(
                uploaded
            )

            text = []

            for page in reader.pages:

                text.append(
                    page.extract_text()
                    or ""
                )

            return "\n".join(text)

        if filename.endswith(".docx"):

            from docx import Document

            document = Document(
                uploaded
            )

            return "\n".join(

                paragraph.text

                for paragraph
                in document.paragraphs

            )

    except Exception as error:

        print(
            "Resume extraction error:",
            error
        )

    return ""


# ============================================================
# MANAGER EXPERIENCE FROM RESUME
# ============================================================

def manager_experience_from_resume(
    resume_text
):

    if not resume_text:
        return "Mid-level PM"

    text = (
        resume_text
        .lower()
    )

    certified_terms = [
        "pmp",
        "prince2",
        "project management professional",
        "certified project manager",
        "capm"
    ]

    if any(
        term in text
        for term in certified_terms
    ):

        return "Certified PM"

    years = []

    patterns = [

        r"(\d+(?:\.\d+)?)\+?\s*years",
        r"(\d+(?:\.\d+)?)\+?\s*yrs"

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text
        )

        for match in matches:

            try:

                years.append(
                    float(match)
                )

            except ValueError:
                pass

    maximum_years = (
        max(years)
        if years
        else 0
    )

    if maximum_years < 2:
        return "Junior PM"

    if maximum_years < 5:
        return "Mid-level PM"

    return "Senior PM"


# ============================================================
# COMPLEXITY
# ============================================================

def calculate_complexity(
    team_members,
    clients,
    tasks,
    budget,
    timeline
):

    team_size = len(team_members)

    stakeholder_count = len(clients)

    total_tasks = len(tasks)

    completed = sum(
        1
        for task in tasks
        if task["status"].lower()
        == "completed"
    )

    overdue = sum(
        1
        for task in tasks
        if task["status"].lower()
        == "overdue"
    )

    completion = (
        completed / total_tasks
        if total_tasks
        else 0
    )

    overdue_rate = (
        overdue / total_tasks
        if total_tasks
        else 0
    )

    # --------------------------------------------------------
    # TEAM EXPERIENCE
    # --------------------------------------------------------

    team_experience = (
        calculate_team_experience(
            team_members
        )
    )

    experience_factor = {

        "Junior": 1.0,
        "Mixed": 0.65,
        "Senior": 0.35,
        "Expert": 0.15

    }.get(
        team_experience,
        0.65
    )

    # --------------------------------------------------------
    # PROJECT SIZE
    # --------------------------------------------------------

    team_factor = min(
        team_size / 20,
        1
    )

    stakeholder_factor = min(
        stakeholder_count / 15,
        1
    )

    task_factor = min(
        total_tasks / 200,
        1
    )

    budget_factor = min(
        budget / 100000,
        1
    )

    timeline_factor = min(
        timeline / 24,
        1
    )

    # --------------------------------------------------------
    # COMPLEXITY
    # --------------------------------------------------------

    weighted_score = (

          budget_factor * 0.15

        + timeline_factor * 0.15

        + team_factor * 0.15

        + stakeholder_factor * 0.10

        + experience_factor * 0.15

        + task_factor * 0.10

        + overdue_rate * 0.10

        + (1 - completion) * 0.10

    )

    return round(

        max(
            1,
            min(
                10,
                1
                +
                weighted_score * 9
            )
        ),

        2

    )


# ============================================================
# TASK SUMMARY
# ============================================================

def calculate_task_summary(
    tasks
):

    total = len(tasks)

    completed = sum(
        1
        for task in tasks
        if task["status"].lower()
        == "completed"
    )

    overdue = sum(
        1
        for task in tasks
        if task["status"].lower()
        == "overdue"
    )

    pending = max(
        total - completed,
        0
    )

    estimated = sum(
        safe_float(
            task["estimated_days"]
        )
        for task in tasks
    )

    actual = sum(
        safe_float(
            task["actual_days"]
        )
        for task in tasks
    )

    completion = (
        completed / total * 100
        if total
        else 0
    )

    delay = (
        overdue / total * 100
        if total
        else 0
    )

    if completion > 66:
        progress = "Completed"

    elif completion > 33:
        progress = "In Progress"

    else:
        progress = "Not Started"

    return {

        "total_tasks":
            total,

        "completed_tasks":
            completed,

        "pending_tasks":
            pending,

        "overdue_tasks":
            overdue,

        "estimated_days":
            round(
                estimated,
                2
            ),

        "actual_days":
            round(
                actual,
                2
            ),

        "completion_percentage":
            round(
                completion,
                2
            ),

        "delay_percentage":
            round(
                delay,
                2
            ),

        "project_progress":
            progress

    }


# ============================================================
# BUILD MODEL ROW
# ============================================================

def make_feature_row(
    form,
    team_members,
    clients,
    tasks
):

    start_date = (
        form.get(
            "Start_Date",
            ""
        ).strip()
    )

    end_date = (
        form.get(
            "End_Date",
            ""
        ).strip()
    )

    timeline = calculate_timeline(
        start_date,
        end_date
    )

    budget = safe_float(
        form.get(
            "Project_Budget_USD",
            0
        )
    )

    task_summary = (
        calculate_task_summary(
            tasks
        )
    )

    team_size = len(
        team_members
    )

    stakeholder_count = len(
        clients
    )

    total_tasks = (
        task_summary[
            "total_tasks"
        ]
    )

    completed_tasks = (
        task_summary[
            "completed_tasks"
        ]
    )

    pending_tasks = (
        task_summary[
            "pending_tasks"
        ]
    )

    overdue_tasks = (
        task_summary[
            "overdue_tasks"
        ]
    )

    completion = (
        task_summary[
            "completion_percentage"
        ]
    )

    delay = (
        task_summary[
            "delay_percentage"
        ]
    )

    estimated_days = (
        task_summary[
            "estimated_days"
        ]
    )

    actual_days = (
        task_summary[
            "actual_days"
        ]
    )

    team_experience = (
        calculate_team_experience(
            team_members
        )
    )

    resume_text = (
        extract_resume_text()
    )

    pm_experience = (
        manager_experience_from_resume(
            resume_text
        )
    )

    complexity = calculate_complexity(

        team_members,

        clients,

        tasks,

        budget,

        timeline

    )

    # --------------------------------------------------------
    # MODEL VALUES
    # --------------------------------------------------------

    available_values = {

        "Project_Type":
            form.get(
                "Project_Type",
                dataset_default(
                    "Project_Type"
                )
            ),

        "Team_Size":
            team_size,

        "Project_Budget_USD":
            budget,

        "Estimated_Timeline_Months":
            timeline,

        "Complexity_Score":
            complexity,

        "Stakeholder_Count":
            stakeholder_count,

        "Team_Experience_Level":
            team_experience,

        "Project_Manager_Experience":
            pm_experience,

        "Project_Phase":
            "Initiation",

        "Total_Tasks":
            total_tasks,

        "Completed_Tasks":
            completed_tasks,

        "Pending_Tasks":
            pending_tasks,

        "Overdue_Tasks":
            overdue_tasks,

        "Completion_Percentage":
            completion,

        "Delay_Percentage":
            delay,

        "Estimated_Effort_Hours":
            estimated_days * 8,

        "Actual_Effort_Hours":
            actual_days * 8,

        "Project_Progress":
            (
                task_summary[
                    "project_progress"
                ]
            )

    }

    row = {}

    for feature in MODEL_FEATURES:

        if feature in available_values:

            value = (
                available_values[
                    feature
                ]
            )

            if is_categorical(
                feature
            ):

                row[feature] = str(
                    value
                )

            else:

                row[feature] = safe_float(
                    value
                )

    # --------------------------------------------------------
    # FEATURES THAT ARE STILL REQUIRED BY THE OLD MODEL
    #
    # These are NOT displayed to the manager.
    #
    # They are temporarily filled using dataset medians/modes
    # because the current trained model still contains them.
    #
    # To completely remove them, retrain the model.
    # --------------------------------------------------------

    hidden_features = [

        "Requirement_Stability",

        "Technology_Familiarity",

        "Resource_Availability",

        "Change_Request_Frequency"

    ]

    for feature in hidden_features:

        if feature in MODEL_FEATURES:

            row[feature] = (
                dataset_default(
                    feature
                )
            )

    # --------------------------------------------------------
    # REMAINING MODEL FEATURES
    # --------------------------------------------------------

    for feature in MODEL_FEATURES:

        if feature not in row:

            row[feature] = (
                dataset_default(
                    feature
                )
            )

    X = pd.DataFrame(
        [row],
        columns=MODEL_FEATURES
    )

    for feature in MODEL_FEATURES:

        if is_categorical(
            feature
        ):

            X[feature] = (
                X[feature]
                .astype(str)
            )

        else:

            X[feature] = pd.to_numeric(
                X[feature],
                errors="raise"
            )

    return (
        X,
        team_experience,
        pm_experience,
        complexity,
        resume_text
    )


# ============================================================
# SAVE PROJECT
# ============================================================

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


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "project_form.html"
    )


# ============================================================
# PREDICT
# ============================================================

@app.route("/api/employee/<employee_id>")
def api_employee(employee_id):
    try:
        employee = get_employee_by_id(employee_id)

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee ID not found."
            }), 404

        return jsonify({
            "success": True,
            "employee": {
                "employee_id": employee.get("employee_id", ""),
                "employee_name": employee.get("employee_name", employee.get("name", "")),
                "email": employee.get("email", ""),
                "role": employee.get("role", ""),
                "department": employee.get("department", ""),
                "experience_level": employee.get("experience_level", ""),
                "years_experience": employee.get("years_experience", 0),
                "skills": employee.get("skills", "")
            }
        })

    except Exception as error:
        print("Employee lookup error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to look up employee."
        }), 500


@app.route("/api/client/<client_id>")
def api_client(client_id):
    try:
        client = get_client_by_id(client_id)

        if not client:
            return jsonify({
                "success": False,
                "message": "Client ID not found."
            }), 404

        return jsonify({
            "success": True,
            "client": {
                "client_id": client.get("client_id", ""),
                "client_name": client.get("client_name", client.get("name", "")),
                "organization": client.get("organization", ""),
                "role": client.get("role", ""),
                "email": client.get("email", "")
            }
        })

    except Exception as error:
        print("Client lookup error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to look up client."
        }), 500


@app.route("/api/manager-experience", methods=["POST"])
def api_manager_experience():
    try:
        resume_text = extract_resume_text()
        experience = manager_experience_from_resume(resume_text)

        return jsonify({
            "success": True,
            "experience": experience
        })

    except Exception as error:
        print("Manager experience error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to analyze the resume."
        }), 500


@app.route(
    "/predict",
    methods=["POST"]
)
def predict():

    try:

        project_name = (
            request.form.get(
                "Project_Name",
                ""
            ).strip()
        )

        if not project_name:

            raise ValueError(
                "Project Name is required."
            )

        start_date = (
            request.form.get(
                "Start_Date",
                ""
            ).strip()
        )

        end_date = (
            request.form.get(
                "End_Date",
                ""
            ).strip()
        )

        if (
            start_date
            and end_date
            and end_date < start_date
        ):

            raise ValueError(
                "End Date cannot be before Start Date."
            )

        project_type = (
            request.form.get(
                "Project_Type",
                ""
            ).strip()
        )

        if not project_type:

            if "Project_Type" in MODEL_FEATURES:

                project_type = (
                    dataset_default(
                        "Project_Type"
                    )
                )

            else:

                project_type = "Not Specified"

        team_members = (
            read_team_members()
        )

        clients = (
            read_clients()
        )

        tasks = (
            read_tasks_from_form()
        )

        (
            input_df,
            team_experience,
            pm_experience,
            complexity,
            resume_text
        ) = make_feature_row(

            request.form,

            team_members,

            clients,

            tasks

        )

        task_summary = (
            calculate_task_summary(
                tasks
            )
        )

        project_budget = safe_float(
            request.form.get(
                "Project_Budget_USD",
                0
            )
        )

        timeline = calculate_timeline(
            start_date,
            end_date
        )

        # ====================================================
        # PREDICT
        # ====================================================

        print()
        print("=" * 60)
        print("PREDICTION INPUT")
        print("=" * 60)

        print(
            input_df.to_string(
                index=False
            )
        )

        prediction = (
            model.predict(
                input_df
            )
        )

        predicted_risk = str(
            prediction[0]
        )

        if isinstance(
            prediction[0],
            (
                list,
                np.ndarray
            )
        ):

            predicted_risk = str(
                prediction[0][0]
            )

        print()
        print(
            "PREDICTED RISK:",
            predicted_risk
        )

        # ====================================================
        # SAVE
        # ====================================================

        try:

            project_id = save_project(

                project_name=
                    project_name,

                project_type=
                    project_type,

                team_members=
                    team_members,

                clients=
                    clients,

                tasks=
                    tasks,

                team_experience=
                    team_experience,

                pm_experience=
                    pm_experience,

                resume_text=
                    resume_text,

                project_budget=
                    project_budget,

                timeline=
                    timeline,

                complexity=
                    complexity,

                predicted_risk=
                    predicted_risk,

                task_summary=
                    task_summary,

                start_date=
                    start_date,

                end_date=
                    end_date

            )

            print()
            print(
                "PROJECT SAVED:",
                project_id
            )

        except Exception as error:

            print()
            print(
                "SUPABASE SAVE ERROR:"
            )
            print(error)

            raise

        # ====================================================
        # RESULT
        # ====================================================

        result_data = {

            "project_id":
                project_id,

            "project_name":
                project_name,

            "risk_level":
                predicted_risk,

            "start_date":
                start_date,

            "end_date":
                end_date,

            "project_type":
                project_type,

            "team_experience":
                team_experience,

            "project_manager_experience":
                pm_experience,

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
                tasks

        }

        session["result"] = result_data

        return render_template(
            "result.html",
            result=result_data
        )

    except Exception as error:

        print()
        print(
            "Prediction error:",
            error
        )

        return (
            "Prediction error: "
            + str(error),
            400
        )


# ============================================================
# RESULT
# ============================================================

@app.route("/result")
def result():

    result_data = session.get(
        "result"
    )

    if not result_data:

        return redirect(
            url_for("home")
        )

    return render_template(
        "result.html",
        result=result_data
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    try:

        response = (

            supabase

            .table("projects")

            .select("*")

            .order(
                "id",
                desc=True
            )

            .execute()

        )

        projects = (
            response.data or []
        )

    except Exception as error:

        print(
            "Dashboard error:",
            error
        )

        projects = []

    counts = {

        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0

    }

    for project in projects:

        risk = str(
            project.get(
                "predicted_risk",
                ""
            )
        ).strip()

        if risk in counts:

            counts[risk] += 1

    return render_template(

        "dashboard.html",

        projects=projects,

        counts=counts

    )


# ============================================================
# PROJECT DETAILS
# ============================================================

@app.route(
    "/project/<project_id>"
)
def project_details(
    project_id
):

    try:

        response = (

            supabase

            .table("projects")

            .select("*")

            .eq(
                "id",
                project_id
            )

            .limit(1)

            .execute()

        )

        projects = (
            response.data or []
        )

        if not projects:

            return (
                "Project not found.",
                404
            )

        project = projects[0]

        details = (
            project.get(
                "project_details"
            )
            or {}
        )

        if isinstance(
            details,
            str
        ):

            try:

                details = json.loads(
                    details
                )

            except Exception:

                details = {}

        # Refresh team/client IDs and master details from their
        # separate tables so project details always show the
        # actual records connected to this project.
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

        return render_template(

            "project_details.html",

            project=project,

            details=details

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


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "INFRA SYNC AI"
    )
    print(
        "AI-BASED PREDICTIVE WORKFLOW MONITORING"
    )
    print("=" * 60)

    print(
        "Model:",
        MODEL_PATH
    )

    print(
        "Features:",
        len(MODEL_FEATURES)
    )

    print(
        "Supabase: Connected"
    )

    print("=" * 60)

    app.run(
        debug=True
    )