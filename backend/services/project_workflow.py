from backend.explainable_ai import explain_prediction

from backend.services.project_input import (
    read_tasks_from_form,
    read_team_members,
    read_clients
)
from backend.supabase_client import supabase

from backend.services.project_skill import (
    update_project_skill_metrics
)

from backend.services.project_risk import (
    model,
    MODEL_FEATURES,
    dataset_default,
    safe_float,
    calculate_timeline,
    make_feature_row,
    calculate_task_summary,
    calculate_ml_risk_score,
    calculate_hybrid_risk,
    risk_score_to_level
)

from backend.services.project_service import save_project


def run_project_prediction(form):

    project_name = form.get(
        "Project_Name", ""
    ).strip()

    if not project_name:
        raise ValueError(
            "Project Name is required."
        )

    start_date = form.get(
        "Start_Date", ""
    ).strip()

    end_date = form.get(
        "End_Date", ""
    ).strip()

    if start_date and end_date and end_date < start_date:
        raise ValueError(
            "End Date cannot be before Start Date."
        )

    project_type = form.get(
        "Project_Type", ""
    ).strip()

    if not project_type:
        if "Project_Type" in MODEL_FEATURES:
            project_type = dataset_default(
                "Project_Type"
            )
        else:
            project_type = "Not Specified"

    # Read project creation data
    team_members = read_team_members()
    clients = read_clients()
    tasks = read_tasks_from_form()

    # Read required project technologies
    required_technologies = [
        technology.strip()
        for technology in form.getlist(
            "Required_Technology"
        )
        if technology and technology.strip()
    ]

    # Remove duplicate technologies
    required_technologies = list(
        dict.fromkeys(required_technologies)
    )

    # Build the original project-risk feature row
    (
        input_df,
        team_experience,
        pm_experience,
        complexity,
        resume_text
    ) = make_feature_row(
        form,
        team_members,
        clients,
        tasks
    )

    task_summary = calculate_task_summary(
        tasks
    )

    project_budget = safe_float(
        form.get(
            "Project_Budget_USD",
            0
        )
    )

    timeline = calculate_timeline(
        start_date,
        end_date
    )

    # ============================================================
    # INITIAL PROJECT-LEVEL RISK PREDICTION
    # ============================================================

    # Original CatBoost class prediction
    prediction = model.predict(
        input_df
    )

    predicted_risk = str(
        prediction[0]
    )

    # Continuous CatBoost risk score
    ml_risk_score, risk_probabilities = (
        calculate_ml_risk_score(
            input_df
        )
    )

    # Existing project-level XAI
    xai_result = explain_prediction(
        model,
        input_df,
        predicted_risk,
        top_n=8
    )

    # Save project
    project_id = save_project(
        project_name=project_name,
        project_type=project_type,
        team_members=team_members,
        clients=clients,
        tasks=tasks,
        team_experience=team_experience,
        pm_experience=pm_experience,
        resume_text=resume_text,
        project_budget=project_budget,
        timeline=timeline,
        complexity=complexity,
        predicted_risk=predicted_risk,
        task_summary=task_summary,
        start_date=start_date,
        end_date=end_date,
        required_technologies=required_technologies
    )

    # ============================================================
    # SKILL METRICS
    # ============================================================

    skill_metrics = update_project_skill_metrics(
        project_id
    )

    skill_gap = skill_metrics["skill_gap"]

    # ============================================================
    # HYBRID PROJECT RISK
    # ============================================================

    hybrid_risk_score = calculate_hybrid_risk(
        ml_risk_score,
        skill_gap
    )

    hybrid_risk_level = risk_score_to_level(
        hybrid_risk_score
    )

    # ============================================================
    # SAVE PROJECT RISK SCORES
    # ============================================================

    risk_update = (
        supabase
        .table("projects")
        .update({
            "ml_risk_score": ml_risk_score,
            "hybrid_risk_score": hybrid_risk_score,
            "hybrid_risk_level": hybrid_risk_level
        })
        .eq("id", project_id)
        .select(
            "id, ml_risk_score, hybrid_risk_score, hybrid_risk_level"
        )
        .execute()
    )

    print(
        "[PROJECT HYBRID RISK] DATABASE UPDATE:",
        risk_update.data
    )

    if not risk_update.data:
        raise RuntimeError(
            f"Failed to save hybrid risk for project {project_id}"
        )

    return {
        "project_id": project_id,
        "project_name": project_name,
        "risk_level": predicted_risk,
        "ml_risk_score": ml_risk_score,

        "risk_probabilities": risk_probabilities,

        "skill_gap": skill_metrics["skill_gap"],

        "hybrid_risk_score": hybrid_risk_score,

        "hybrid_risk_level": hybrid_risk_level,
        "start_date": start_date,
        "end_date": end_date,
        "project_type": project_type,

        "required_technologies":
            required_technologies,

        "skill_coverage":
            skill_metrics["skill_coverage"],

        "skill_gap":
            skill_metrics["skill_gap"],

        "covered_skills":
            skill_metrics["covered_skills"],

        "missing_skills":
            skill_metrics["missing_skills"],

        "team_skills":
            skill_metrics["team_skills"],

        "team_experience": team_experience,

        "project_manager_experience":
            pm_experience,

        "project_budget": project_budget,

        "timeline_months": timeline,

        "complexity_score": complexity,

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

        "risk_confidence":
            xai_result["confidence"],

        "xai":
            xai_result,

        "team_members":
            team_members,

        "clients":
            clients,

        "tasks":
            tasks
    }