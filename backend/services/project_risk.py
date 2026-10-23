import os
import joblib
import pandas as pd

from datetime import datetime
from flask import request
from backend.supabase_client import supabase

from backend.manager import (
    extract_resume_text,
    manager_experience_from_resume
)

from backend.master_data import (
    get_employee_by_id,
    get_client_by_id
)

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "catboost_final_model.pkl"
DATASET_PATH = PROJECT_ROOT / "project_risk_final_clean.csv"

model = joblib.load(MODEL_PATH)
reference_df = pd.read_csv(DATASET_PATH)
MODEL_FEATURES = list(model.feature_names_)
reference_features = reference_df.drop(
    columns=["Project_ID", "Risk_Level"],
    errors="ignore"
)

missing = [
    feature for feature in MODEL_FEATURES
    if feature not in reference_features.columns
]

if missing:
    raise ValueError(
        "Dataset is missing model features: "
        + ", ".join(missing)
    )

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
# PROJECT RISK SCORING
# ============================================================

RISK_VALUES = {
    "Low": 0.00,
    "Medium": 0.33,
    "High": 0.67,
    "Critical": 1.00
}


def calculate_ml_risk_score(input_df):
    """
    Convert the project-level CatBoost probability output
    into a continuous risk score between 0 and 1.
    """

    probabilities = model.predict_proba(input_df)[0]
    class_names = list(model.classes_)

    probability_map = {
        str(class_names[i]): float(probabilities[i])
        for i in range(len(class_names))
    }

    ml_risk_score = sum(
        probability_map.get(label, 0.0) * score
        for label, score in RISK_VALUES.items()
    )

    return round(ml_risk_score, 4), probability_map


def calculate_hybrid_risk(
    ml_risk_score,
    skill_gap,
    skill_weight=0.30
):
    """
    Combine project-level ML risk with skill gap.

    Formula:
        Hybrid Risk =
            ML Risk +
            λ × Skill Gap × (1 - ML Risk)
    """

    ml_risk_score = max(
        0.0,
        min(1.0, float(ml_risk_score))
    )

    skill_gap = max(
        0.0,
        min(1.0, float(skill_gap))
    )

    hybrid_risk = (
        ml_risk_score
        + skill_weight
        * skill_gap
        * (1.0 - ml_risk_score)
    )

    return round(
        min(1.0, hybrid_risk),
        4
    )


def risk_score_to_level(score):
    """
    Convert continuous project risk score
    into a project risk level.
    """

    score = float(score)

    if score < 0.25:
        return "Low"

    if score < 0.50:
        return "Medium"

    if score < 0.75:
        return "High"

    return "Critical"
    
def make_feature_row(
    form,
    team_members,
    clients,
    tasks,
    resume_text=None
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

    if resume_text is None:
        resume_text = extract_resume_text()

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
# SAVE INITIAL PROJECT CATBOOST RISK
# ============================================================

def _save_initial_project_catboost_risk(project_id, predicted_risk, predicted_risk_score, tasks):
    """Seed current risk and history with the initial project CatBoost result.

    This only runs when no current dynamic-risk row exists. Once task-based
    dynamic risk has been calculated, subsequent CatBoost refreshes must not
    overwrite it.
    """
    current_response = (
        supabase.table("project_dynamic_risk")
        .select("project_id, model_version")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    existing_current = (current_response.data or [None])[0]
    # Do not overwrite a task-based dynamic risk. However, if an earlier
    # version saved the initial CatBoost row with a label-only score, update
    # that initial row with the probability-derived score.
    if existing_current and existing_current.get("model_version") != "project_catboost_initial":
        return None

    raw_level = str(predicted_risk or "Low").strip()
    normalized_level = raw_level.replace("_", " ").title()
    if normalized_level.endswith(" Risk"):
        normalized_level = normalized_level[:-5].strip()
    score_by_level = {
        "Low": 0.00,
        "Medium": 0.33,
        "High": 0.67,
        "Critical": 1.00,
    }
    risk_level = normalized_level if normalized_level in score_by_level else "Low"
    # Prefer the probability-derived CatBoost score. The label mapping is only
    # a compatibility fallback for models that do not expose predict_proba.
    risk_score = float(predicted_risk_score) if predicted_risk_score is not None else score_by_level[risk_level]
    risk_score = max(0.0, min(1.0, risk_score))

    unfinished_statuses = {"TODO", "TO_DO", "IN_PROGRESS", "IN_REVIEW"}
    unfinished_task_count = sum(
        1 for task in tasks
        if str(task.get("status") or "").strip().upper() in unfinished_statuses
    )
    total_task_count = len(tasks)
    # These fields count task-level risks, not the project-level CatBoost label.
    high_task_count = 0
    critical_task_count = 0

    initial_record = {
        "project_id": project_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "total_task_count": total_task_count,
        "high_task_count": high_task_count,
        "critical_task_count": critical_task_count,
        "risk_trend": "Stable",
        "risk_change": 0.0,
        "baseline_risk_score": risk_score,
        "baseline_risk_level": risk_level,
        "baseline_risk_change": 0.0,
        "unfinished_task_count": unfinished_task_count,
        "model_version": "project_catboost_initial",
    }

    if existing_current:
        supabase.table("project_dynamic_risk").update(initial_record).eq("project_id", project_id).execute()
    else:
        supabase.table("project_dynamic_risk").insert(initial_record).execute()
    # Record the initial CatBoost result in history only once per project.
    # Re-running the project prediction must not append duplicate initial rows.
    initial_history_response = (
        supabase.table("project_dynamic_risk_history")
        .select("id")
        .eq("project_id", project_id)
        .eq("model_version", "project_catboost_initial")
        .limit(1)
        .execute()
    )
    if not (initial_history_response.data or []):
        history_record = dict(initial_record)
        supabase.table("project_dynamic_risk_history").insert(history_record).execute()

    print(f"[INITIAL PROJECT RISK] Saved CatBoost risk for project {project_id}: {risk_level} ({risk_score:.4f})")
    return initial_record


# ============================================================
# RE-RUN PROJECT-LEVEL CATBOOST FROM CURRENT SUPABASE DATA
# ============================================================

def refresh_project_catboost_prediction(project_id):
    """Rebuild project features from saved project details and current Tasks,
    rerun the existing project-level model, and update projects.predicted_risk.

    The trained model, feature list, feature defaults, and prediction labels are
    unchanged. Current task rows replace the originally submitted task list.
    """
    project_id = int(project_id)
    response = (
        supabase.table("projects")
        .select("*")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )
    projects = response.data or []
    if not projects:
        raise ValueError(f"Project {project_id} was not found.")
    project = projects[0]
    details = project.get("project_details") or {}
    if isinstance(details, str):
        try:
            import json
            details = json.loads(details)
        except (TypeError, ValueError):
            details = {}

    tasks_response = (
        supabase.table("Tasks")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    db_tasks = tasks_response.data or []

    # Convert operational task rows to the fields expected by the existing model.
    from datetime import date
    current_tasks = []
    today = date.today()
    for task in db_tasks:
        status = str(task.get("status") or "").strip().upper()
        deadline = task.get("deadline")
        is_closed = status in {"CLOSED", "COMPLETED", "DONE"}
        overdue = False
        if deadline and not is_closed:
            try:
                overdue = date.fromisoformat(str(deadline)[:10]) < today
            except ValueError:
                overdue = False
        if is_closed:
            model_status = "completed"
        elif overdue:
            model_status = "overdue"
        else:
            model_status = "pending"
        current_tasks.append({
            "status": model_status,
            "estimated_days": safe_float(task.get("estimated_hours")) / 8.0,
            "actual_days": safe_float(task.get("actual_hours")) / 8.0,
        })

    # Reuse stored team/client records when available; fall back to the project's
    # existing JSON snapshot so no new data model is introduced.
    team_response = (
        supabase.table("project_team_members")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    team_members = team_response.data or details.get("team_members") or []

    client_response = (
        supabase.table("project_clients")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    clients = client_response.data or details.get("clients") or []

    form = {
        "Project_Type": project.get("project_type") or details.get("project_type", ""),
        "Project_Budget_USD": project.get("project_budget", details.get("project_budget", 0)),
        "Start_Date": details.get("start_date", ""),
        "End_Date": details.get("end_date", ""),
    }
    resume_text = details.get("manager_resume", "") or ""

    X, team_experience, pm_experience, complexity, _ = make_feature_row(
        form,
        team_members,
        clients,
        current_tasks,
        resume_text=resume_text,
    )

    prediction = model.predict(X)
    predicted_risk = prediction[0]
    if hasattr(predicted_risk, "item"):
        predicted_risk = predicted_risk.item()
    predicted_risk = str(predicted_risk).strip()

    # Calculate a continuous 0-1 score from the project CatBoost class
    # probabilities, rather than assigning a fixed score from the label.
    # Expected score = sum(P(class) * risk value for that class).
    risk_values = {
        "Low": 0.00,
        "Medium": 0.33,
        "High": 0.67,
        "Critical": 1.00,
    }
    predicted_risk_score = None
    if hasattr(model, "predict_proba") and hasattr(model, "classes_"):
        probabilities = model.predict_proba(X)[0]
        probability_score = 0.0
        probability_total = 0.0
        for class_name, probability in zip(model.classes_, probabilities):
            label = str(class_name).strip().replace("_", " ").title()
            if label.endswith(" Risk"):
                label = label[:-5].strip()
            if label in risk_values:
                probability_score += float(probability) * risk_values[label]
                probability_total += float(probability)
        if probability_total > 0:
            predicted_risk_score = max(0.0, min(1.0, probability_score / probability_total))

    # Update the canonical project prediction and refresh the stored snapshot's
    # metrics without altering the trained model or feature engineering.
    task_summary = calculate_task_summary(current_tasks)
    updated_details = dict(details)
    if not updated_details.get("initial_predicted_risk"):
        updated_details["initial_predicted_risk"] = project.get("predicted_risk") or predicted_risk
    updated_details.update({
        "initial_predicted_risk_score": (
            updated_details.get("initial_predicted_risk_score")
            if updated_details.get("initial_predicted_risk_score") is not None
            else predicted_risk_score
        ),
        "team_experience": team_experience,
        "project_manager_experience": pm_experience,
        "complexity_score": complexity,
        "total_tasks": task_summary["total_tasks"],
        "completed_tasks": task_summary["completed_tasks"],
        "pending_tasks": task_summary["pending_tasks"],
        "overdue_tasks": task_summary["overdue_tasks"],
        "completion_percentage": task_summary["completion_percentage"],
        "delay_percentage": task_summary["delay_percentage"],
        "estimated_effort_hours": task_summary["estimated_days"] * 8,
        "actual_effort_hours": task_summary["actual_days"] * 8,
        "project_progress": task_summary["project_progress"],
        # Keep the complete current Tasks rows in the project snapshot.
        "tasks": db_tasks,
        "predicted_risk": predicted_risk,
        "risk_refreshed_at": datetime.now().isoformat(),
    })
    update_payload = {
        "predicted_risk": predicted_risk,
        "total_tasks": task_summary["total_tasks"],
        "completed_tasks": task_summary["completed_tasks"],
        "overdue_tasks": task_summary["overdue_tasks"],
        "estimated_effort_hours": task_summary["estimated_days"] * 8,
        "actual_effort_hours": task_summary["actual_days"] * 8,
        "project_details": updated_details,
    }
    supabase.table("projects").update(update_payload).eq("id", project_id).execute()

    # Persist the initial project-level CatBoost risk to both risk tables once.
    # Later task-based dynamic-risk calculations replace the current record.
    _save_initial_project_catboost_risk(
        project_id=project_id,
        predicted_risk=predicted_risk,
        predicted_risk_score=predicted_risk_score,
        tasks=db_tasks,
    )

    return {
        "project_id": project_id,
        "predicted_risk": predicted_risk,
        "risk_score": predicted_risk_score,
        "total_tasks": task_summary["total_tasks"],
        "completed_tasks": task_summary["completed_tasks"],
        "pending_tasks": task_summary["pending_tasks"],
        "overdue_tasks": task_summary["overdue_tasks"],
    }
