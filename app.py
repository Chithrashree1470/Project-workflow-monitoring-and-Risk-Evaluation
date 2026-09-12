from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)
app.secret_key = "infrasync-ai-secret-key"


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


# ============================================================
# FILE PATHS
# ============================================================

MODEL_PATH = os.path.join(
    BASE_DIR,
    "catboost_final_model.pkl"
)

CSV_PATH = os.path.join(
    BASE_DIR,
    "project_risk_final_clean.csv"
)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None

try:

    if SUPABASE_URL and SUPABASE_KEY:

        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

        print("\n==========================================")
        print("SUPABASE CONNECTED SUCCESSFULLY")
        print("==========================================")

    else:

        print("\nWARNING: Supabase credentials not found.")

except Exception as e:

    print("\nSUPABASE CONNECTION ERROR:")
    print(e)


# ============================================================
# LOAD MODEL
# ============================================================

print("\n==========================================")
print("AI-BASED PREDICTIVE WORKFLOW MONITORING")
print("==========================================")

try:

    model = joblib.load(
        MODEL_PATH
    )

    print("Model loaded successfully:")
    print(type(model))

except Exception as e:

    print("MODEL LOADING ERROR:", e)

    model = None


# ============================================================
# LOAD DATASET
# ============================================================

try:

    training_df = pd.read_csv(
        CSV_PATH
    )

    print("\nTraining dataset loaded")
    print("Rows    :", len(training_df))
    print("Columns :", len(training_df.columns))

except Exception as e:

    print("\nDATASET LOADING ERROR:", e)

    training_df = pd.DataFrame()


# ============================================================
# MODEL FEATURES
# ============================================================

def get_model_feature_names():

    if model is not None:

        if hasattr(
            model,
            "feature_names_"
        ):

            names = model.feature_names_

            if names:

                return list(names)

        if hasattr(
            model,
            "feature_names_in_"
        ):

            return list(
                model.feature_names_in_
            )

    if not training_df.empty:

        columns = list(
            training_df.columns
        )

        if "Project_ID" in columns:

            columns.remove("Project_ID")

        if "Risk_Level" in columns:

            columns.remove("Risk_Level")

        return columns

    return []


MODEL_FEATURES = get_model_feature_names()


print("\n==========================================")
print(
    "MODEL FEATURES :",
    len(MODEL_FEATURES)
)
print("==========================================")

for i, feature in enumerate(
    MODEL_FEATURES,
    start=1
):

    print(
        f"{i:02d}. {feature}"
    )


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):

    if value is None:

        return ""

    return str(value).strip()


def safe_float(
    value,
    default=0.0
):

    if value is None:

        return default

    value = str(value).strip()

    if value == "":

        return default

    try:

        number = float(value)

        return max(
            number,
            0.0
        )

    except Exception:

        return default


def safe_int(
    value,
    default=0
):

    if value is None:

        return default

    value = str(value).strip()

    if value == "":

        return default

    try:

        number = int(
            float(value)
        )

        return max(
            number,
            0
        )

    except Exception:

        return default


# ============================================================
# FORM VALUE
# ============================================================

def form_value(*names):

    for name in names:

        value = request.form.get(
            name
        )

        if value is not None:

            return value

    return ""


# ============================================================
# AUTOMATIC COMPLEXITY CALCULATION
# ============================================================

def calculate_complexity_score(
    project_type,
    methodology,
    team_size,
    project_budget,
    timeline_months,
    stakeholder_count,
    team_experience,
    project_manager_experience,
    project_phase,
    requirement_stability,
    change_request_frequency,
    technology_familiarity,
    resource_availability,
    total_tasks,
    completed_tasks,
    overdue_tasks,
    estimated_effort_days,
    actual_effort_days
):

    # ========================================================
    # CATEGORICAL SCORES
    # ========================================================

    project_type_scores = {

        "Construction": 0.75,
        "Healthcare": 0.70,
        "IT": 0.60,
        "Manufacturing": 0.70,
        "Marketing": 0.35,
        "R&D": 0.85
    }

    methodology_scores = {

        "Agile": 0.55,
        "Hybrid": 0.65,
        "Kanban": 0.45,
        "Scrum": 0.55,
        "Waterfall": 0.40
    }

    team_experience_scores = {

        "Junior": 0.90,
        "Mixed": 0.65,
        "Senior": 0.35,
        "Expert": 0.20
    }

    pm_experience_scores = {

        "Junior PM": 0.90,
        "Mid-level PM": 0.60,
        "Senior PM": 0.30,
        "Certified PM": 0.20
    }

    phase_scores = {

        "Initiation": 0.35,
        "Planning": 0.55,
        "Execution": 0.80,
        "Monitoring": 0.70,
        "Closure": 0.30
    }

    requirement_scores = {

        "Stable": 0.20,
        "Moderate": 0.55,
        "Volatile": 0.90
    }

    technology_scores = {

        "New": 0.90,
        "Familiar": 0.50,
        "Expert": 0.20
    }

    resource_scores = {

        "Low": 0.90,
        "Medium": 0.55,
        "High": 0.20
    }


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    project_type = clean_text(
        project_type
    )

    methodology = clean_text(
        methodology
    )

    team_experience = clean_text(
        team_experience
    )

    project_manager_experience = clean_text(
        project_manager_experience
    )

    project_phase = clean_text(
        project_phase
    )

    requirement_stability = clean_text(
        requirement_stability
    )

    technology_familiarity = clean_text(
        technology_familiarity
    )

    resource_availability = clean_text(
        resource_availability
    )


    # ========================================================
    # CATEGORICAL FACTORS
    # ========================================================

    type_factor = project_type_scores.get(
        project_type,
        0.55
    )

    methodology_factor = methodology_scores.get(
        methodology,
        0.55
    )

    team_experience_factor = team_experience_scores.get(
        team_experience,
        0.55
    )

    pm_factor = pm_experience_scores.get(
        project_manager_experience,
        0.55
    )

    phase_factor = phase_scores.get(
        project_phase,
        0.55
    )

    requirement_factor = requirement_scores.get(
        requirement_stability,
        0.55
    )

    technology_factor = technology_scores.get(
        technology_familiarity,
        0.55
    )

    resource_factor = resource_scores.get(
        resource_availability,
        0.55
    )


    # ========================================================
    # NORMALIZATION
    # ========================================================

    def scale(
        value,
        low,
        high
    ):

        if high <= low:

            return 0.5

        value = max(
            float(value),
            0.0
        )

        return max(
            0.0,
            min(
                1.0,
                (value - low) /
                (high - low)
            )
        )


    # ========================================================
    # NUMERIC FACTORS
    # ========================================================

    team_factor = scale(
        team_size,
        1,
        40
    )

    budget_factor = scale(
        project_budget,
        0,
        250000
    )

    timeline_factor = scale(
        timeline_months,
        0,
        12
    )

    stakeholder_factor = scale(
        stakeholder_count,
        1,
        40
    )

    change_factor = scale(
        change_request_frequency,
        0,
        20
    )

    task_factor = scale(
        total_tasks,
        1,
        200
    )


    # ========================================================
    # OVERDUE TASK FACTOR
    # ========================================================

    if total_tasks > 0:

        overdue_factor = (
            overdue_tasks /
            total_tasks
        )

    else:

        overdue_factor = 0.0

    overdue_factor = max(
        0.0,
        min(
            1.0,
            overdue_factor
        )
    )


    # ========================================================
    # COMPLETION FACTOR
    # ========================================================

    if total_tasks > 0:

        completion = (
            completed_tasks /
            total_tasks
        )

    else:

        completion = 0.0

    completion = max(
        0.0,
        min(
            1.0,
            completion
        )
    )

    completion_complexity = (
        1.0 - completion
    )


    # ========================================================
    # ESTIMATED EFFORT
    # ========================================================

    estimated_effort_factor = scale(
        estimated_effort_days,
        0,
        1000
    )


    # ========================================================
    # ACTUAL / ESTIMATED EFFORT
    # ========================================================

    if (
        actual_effort_days > 0
        and
        estimated_effort_days > 0
    ):

        effort_ratio = (
            actual_effort_days /
            estimated_effort_days
        )

        actual_effort_factor = max(
            0.0,
            min(
                1.0,
                effort_ratio / 2.0
            )
        )

    elif actual_effort_days > 0:

        actual_effort_factor = scale(
            actual_effort_days,
            0,
            1000
        )

    else:

        actual_effort_factor = 0.5


    # ========================================================
    # WEIGHTED COMPLEXITY
    # ========================================================

    weighted_score = (

        type_factor * 0.06

        + methodology_factor * 0.04

        + team_factor * 0.06

        + budget_factor * 0.06

        + timeline_factor * 0.08

        + stakeholder_factor * 0.05

        + team_experience_factor * 0.05

        + pm_factor * 0.05

        + phase_factor * 0.04

        + requirement_factor * 0.08

        + change_factor * 0.08

        + technology_factor * 0.08

        + resource_factor * 0.08

        + task_factor * 0.05

        + overdue_factor * 0.04

        + completion_complexity * 0.03

        + estimated_effort_factor * 0.04

        + actual_effort_factor * 0.03
    )


    # ========================================================
    # CONVERT 0-1 TO 1-10
    # ========================================================

    complexity_score = round(
        1 + (
            weighted_score * 9
        )
    )

    complexity_score = max(
        1,
        min(
            10,
            complexity_score
        )
    )

    return complexity_score


# ============================================================
# DATASET HELPERS
# ============================================================

def get_dataset_mode(column):

    if training_df.empty:

        return ""

    if column not in training_df.columns:

        return ""

    series = (
        training_df[column]
        .dropna()
    )

    if len(series) == 0:

        return ""

    mode = series.mode()

    if len(mode) > 0:

        return mode.iloc[0]

    return series.iloc[0]


def get_dataset_median(column):

    if training_df.empty:

        return 0.0

    if column not in training_df.columns:

        return 0.0

    series = pd.to_numeric(
        training_df[column],
        errors="coerce"
    ).dropna()

    if len(series) == 0:

        return 0.0

    return float(
        series.median()
    )


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

def get_categorical_features():

    categorical = set()

    if model is not None:

        if hasattr(
            model,
            "get_cat_feature_indices"
        ):

            try:

                indices = (
                    model
                    .get_cat_feature_indices()
                )

                for index in indices:

                    if (
                        index <
                        len(MODEL_FEATURES)
                    ):

                        categorical.add(
                            MODEL_FEATURES[index]
                        )

            except Exception:

                pass


    if not training_df.empty:

        for feature in MODEL_FEATURES:

            if feature not in training_df.columns:

                continue

            dtype = (
                training_df[feature]
                .dtype
            )

            if (
                dtype == "object"
                or
                str(dtype).startswith(
                    "category"
                )
            ):

                categorical.add(
                    feature
                )

    return categorical


CATEGORICAL_FEATURES = (
    get_categorical_features()
)


# ============================================================
# BUILD PROJECT INPUT
# ============================================================

def build_project_input():

    # ========================================================
    # PROJECT NAME
    # ========================================================

    project_name = clean_text(
        form_value(
            "Project_Name",
            "project_name"
        )
    )


    # ========================================================
    # PROJECT TYPE
    # ========================================================

    project_type = clean_text(
        form_value(
            "Project_Type",
            "project_type"
        )
    )

    if project_type.lower() in [
        "other",
        "others"
    ]:

        custom_type = clean_text(
            form_value(
                "Project_Type_Other",
                "Other_Project_Type",
                "other_project_type"
            )
        )

        if custom_type:

            project_type = custom_type


    # ========================================================
    # METHODOLOGY
    # ========================================================

    methodology = clean_text(
        form_value(
            "Methodology_Used",
            "methodology"
        )
    )

    if methodology.lower() in [
        "other",
        "others"
    ]:

        custom_methodology = clean_text(
            form_value(
                "Methodology_Used_Other",
                "Other_Methodology",
                "other_methodology"
            )
        )

        if custom_methodology:

            methodology = custom_methodology


    # ========================================================
    # NUMERIC INPUTS
    # ========================================================

    team_size = safe_int(
        form_value(
            "Team_Size",
            "team_size"
        )
    )

    project_budget = safe_float(
        form_value(
            "Project_Budget_USD",
            "project_budget"
        )
    )

    stakeholder_count = safe_int(
        form_value(
            "Stakeholder_Count",
            "stakeholder_count"
        )
    )

    change_request_frequency = safe_int(
        form_value(
            "Change_Request_Frequency",
            "change_request_frequency"
        )
    )

    total_tasks = safe_int(
        form_value(
            "Total_Tasks",
            "total_tasks"
        )
    )

    completed_tasks = safe_int(
        form_value(
            "Completed_Tasks",
            "completed_tasks"
        )
    )

    overdue_tasks = safe_int(
        form_value(
            "Overdue_Tasks",
            "overdue_tasks"
        )
    )

    estimated_effort_days = safe_float(
        form_value(
            "Estimated_Effort_Days",
            "estimated_effort_days"
        )
    )

    actual_effort_days = safe_float(
        form_value(
            "Actual_Effort_Days",
            "actual_effort_days"
        )
    )


    # ========================================================
    # TASK VALIDATION
    # ========================================================

    completed_tasks = min(
        completed_tasks,
        total_tasks
    )

    overdue_tasks = min(
        overdue_tasks,
        total_tasks
    )


    # ========================================================
    # CATEGORICAL INPUTS
    # ========================================================

    team_experience = clean_text(
        form_value(
            "Team_Experience_Level",
            "team_experience"
        )
    )

    project_manager_experience = clean_text(
        form_value(
            "Project_Manager_Experience",
            "project_manager_experience"
        )
    )

    project_phase = clean_text(
        form_value(
            "Project_Phase",
            "project_phase"
        )
    )

    requirement_stability = clean_text(
        form_value(
            "Requirement_Stability",
            "requirement_stability"
        )
    )

    technology_familiarity = clean_text(
        form_value(
            "Technology_Familiarity",
            "technology_familiarity"
        )
    )

    resource_availability = clean_text(
        form_value(
            "Resource_Availability",
            "resource_availability"
        )
    )


    # ========================================================
    # DATES
    # ========================================================

    start_date = clean_text(
        form_value(
            "Start_Date",
            "start_date"
        )
    )

    end_date = clean_text(
        form_value(
            "End_Date",
            "end_date"
        )
    )


    # ========================================================
    # TIMELINE
    # ========================================================

    estimated_timeline_months = 0.0

    try:

        if start_date and end_date:

            start = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            )

            end = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            )

            days = (
                end - start
            ).days

            if days >= 0:

                estimated_timeline_months = round(
                    days / 30.4375,
                    2
                )

    except Exception:

        estimated_timeline_months = 0.0


    # ========================================================
    # DERIVED VALUES
    # ========================================================

    pending_tasks = max(
        total_tasks - completed_tasks,
        0
    )


    if total_tasks > 0:

        completion_percentage = (
            completed_tasks /
            total_tasks
        ) * 100

    else:

        completion_percentage = 0.0


    completion_percentage = max(
        0.0,
        min(
            100.0,
            completion_percentage
        )
    )


    if total_tasks > 0:

        delay_percentage = (
            overdue_tasks /
            total_tasks
        ) * 100

    else:

        delay_percentage = 0.0


    delay_percentage = max(
        0.0,
        min(
            100.0,
            delay_percentage
        )
    )


    if completion_percentage <= 33:

        project_progress = "Not Started"

    elif completion_percentage > 66:

        project_progress = "Completed"

    else:

        project_progress = "In Progress"


    # ========================================================
    # EFFORT HOURS
    # ========================================================

    estimated_effort_hours = (
        estimated_effort_days * 8
    )

    actual_effort_hours = (
        actual_effort_days * 8
    )


    # ========================================================
    # AUTOMATIC COMPLEXITY
    # ========================================================

    complexity_score = calculate_complexity_score(

        project_type=
            project_type,

        methodology=
            methodology,

        team_size=
            team_size,

        project_budget=
            project_budget,

        timeline_months=
            estimated_timeline_months,

        stakeholder_count=
            stakeholder_count,

        team_experience=
            team_experience,

        project_manager_experience=
            project_manager_experience,

        project_phase=
            project_phase,

        requirement_stability=
            requirement_stability,

        change_request_frequency=
            change_request_frequency,

        technology_familiarity=
            technology_familiarity,

        resource_availability=
            resource_availability,

        total_tasks=
            total_tasks,

        completed_tasks=
            completed_tasks,

        overdue_tasks=
            overdue_tasks,

        estimated_effort_days=
            estimated_effort_days,

        actual_effort_days=
            actual_effort_days
    )


    print(
        "\nAutomatically calculated Complexity:",
        complexity_score
    )


    # ========================================================
    # KNOWN MODEL VALUES
    # ========================================================

    known_values = {

        "Project_Type":
            project_type,

        "Methodology_Used":
            methodology,

        "Team_Size":
            team_size,

        "Project_Budget_USD":
            project_budget,

        "Estimated_Timeline_Months":
            estimated_timeline_months,

        "Complexity_Score":
            complexity_score,

        "Stakeholder_Count":
            stakeholder_count,

        "Team_Experience_Level":
            team_experience,

        "Project_Manager_Experience":
            project_manager_experience,

        "Project_Phase":
            project_phase,

        "Requirement_Stability":
            requirement_stability,

        "Change_Request_Frequency":
            change_request_frequency,

        "Technology_Familiarity":
            technology_familiarity,

        "Resource_Availability":
            resource_availability,

        "Total_Tasks":
            total_tasks,

        "Completed_Tasks":
            completed_tasks,

        "Overdue_Tasks":
            overdue_tasks,

        "Pending_Tasks":
            pending_tasks,

        "Completion_Percentage":
            completion_percentage,

        "Delay_Percentage":
            delay_percentage,

        "Estimated_Effort_Hours":
            estimated_effort_hours,

        "Actual_Effort_Hours":
            actual_effort_hours,

        "Project_Progress":
            project_progress
    }


    # ========================================================
    # BUILD MODEL INPUT
    # ========================================================

    final_values = {}

    for feature in MODEL_FEATURES:

        if feature in known_values:

            value = known_values[
                feature
            ]

        else:

            if feature in CATEGORICAL_FEATURES:

                value = get_dataset_mode(
                    feature
                )

            else:

                value = get_dataset_median(
                    feature
                )

        final_values[
            feature
        ] = value


    # ========================================================
    # DATAFRAME
    # ========================================================

    input_df = pd.DataFrame(
        [final_values],
        columns=MODEL_FEATURES
    )


    # ========================================================
    # DATA TYPES
    # ========================================================

    for feature in MODEL_FEATURES:

        if feature in CATEGORICAL_FEATURES:

            input_df[feature] = (
                input_df[feature]
                .fillna("")
                .astype(str)
            )

        else:

            input_df[feature] = pd.to_numeric(
                input_df[feature],
                errors="coerce"
            )

            if input_df[
                feature
            ].isna().any():

                input_df.loc[
                    input_df[
                        feature
                    ].isna(),
                    feature
                ] = get_dataset_median(
                    feature
                )


    # ========================================================
    # FINAL CLEANING
    # ========================================================

    input_df = input_df.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )


    for feature in MODEL_FEATURES:

        if feature in CATEGORICAL_FEATURES:

            input_df[feature] = (
                input_df[feature]
                .fillna("")
                .astype(str)
            )

        else:

            input_df[feature] = (
                input_df[feature]
                .fillna(
                    get_dataset_median(
                        feature
                    )
                )
            )


    return (

        input_df,

        project_name,

        completion_percentage,

        delay_percentage,

        pending_tasks,

        project_progress,

        estimated_timeline_months,

        total_tasks,

        completed_tasks,

        overdue_tasks,

        estimated_effort_hours,

        actual_effort_hours,

        project_type,

        team_size,

        project_budget,

        complexity_score
    )


# ============================================================
# SAVE TO SUPABASE
# ============================================================

def save_to_supabase(
    project_name,
    project_type,
    team_size,
    project_budget,
    timeline_months,
    complexity_score,
    total_tasks,
    completed_tasks,
    overdue_tasks,
    estimated_effort_hours,
    actual_effort_hours,
    predicted_risk,
    probabilities
):

    if supabase is None:

        raise Exception(
            "Supabase is not connected. "
            "Check SUPABASE_URL and SUPABASE_KEY."
        )


    data = {

        "project_name":
            project_name,

        "project_type":
            project_type,

        "team_size":
            int(team_size),

        "project_budget":
            float(project_budget),

        "timeline_months":
            float(timeline_months),

        "complexity_score":
            int(complexity_score),

        "total_tasks":
            int(total_tasks),

        "completed_tasks":
            int(completed_tasks),

        "overdue_tasks":
            int(overdue_tasks),

        "estimated_effort_hours":
            float(estimated_effort_hours),

        "predicted_risk":
            predicted_risk,

        "critical_confidence":
            float(
                probabilities.get(
                    "Critical",
                    0
                )
            ),

        "high_confidence":
            float(
                probabilities.get(
                    "High",
                    0
                )
            ),

        "low_confidence":
            float(
                probabilities.get(
                    "Low",
                    0
                )
            ),

        "medium_confidence":
            float(
                probabilities.get(
                    "Medium",
                    0
                )
            )
    }


    response = (
        supabase
        .table("projects")
        .insert(data)
        .execute()
    )


    print("\n==========================================")
    print("SUPABASE SAVE SUCCESSFUL")
    print("==========================================")

    print(data)

    return response


# ============================================================
# PREDICT
# ============================================================

@app.route(
    "/predict",
    methods=["POST"]
)
def predict():

    try:

        if model is None:

            return (
                "Model is not loaded. "
                "Check catboost_final_model.pkl",
                500
            )


        # ====================================================
        # BUILD INPUT
        # ====================================================

        result = build_project_input()


        (
            input_df,
            project_name,
            completion_percentage,
            delay_percentage,
            pending_tasks,
            project_progress,
            estimated_timeline_months,
            total_tasks,
            completed_tasks,
            overdue_tasks,
            estimated_effort_hours,
            actual_effort_hours,
            project_type,
            team_size,
            project_budget,
            complexity_score
        ) = result


        # ====================================================
        # VALIDATION
        # ====================================================

        if not project_name:

            return (
                "Project Name is required.",
                400
            )


        if not project_type:

            return (
                "Project Type is required.",
                400
            )


        # ====================================================
        # MODEL PREDICTION
        # ====================================================

        print("\n==========================================")
        print("PREDICTION INPUT")
        print("==========================================")

        print(
            input_df.to_string(
                index=False
            )
        )


        prediction = model.predict(
            input_df
        )


        predicted_risk = prediction[0]


        if isinstance(
            predicted_risk,
            (
                list,
                np.ndarray
            )
        ):

            predicted_risk = predicted_risk[0]


        predicted_risk = str(
            predicted_risk
        )


        # ====================================================
        # PROBABILITIES
        # ====================================================

        probabilities = {}


        if hasattr(
            model,
            "predict_proba"
        ):

            try:

                proba = (
                    model
                    .predict_proba(
                        input_df
                    )[0]
                )


                if hasattr(
                    model,
                    "classes_"
                ):

                    classes = (
                        model.classes_
                    )

                else:

                    classes = [
                        "Low",
                        "Medium",
                        "High",
                        "Critical"
                    ][:len(proba)]


                for cls, probability in zip(
                    classes,
                    proba
                ):

                    probabilities[
                        str(cls)
                    ] = round(
                        float(
                            probability
                        ) * 100,
                        2
                    )


            except Exception as e:

                print(
                    "Probability error:",
                    e
                )


        # ====================================================
        # AI CONFIDENCE
        # ====================================================

        if probabilities:

            ai_confidence = max(
                probabilities.values()
            )

        else:

            ai_confidence = 0.0


        # ====================================================
        # SAVE
        # ====================================================

        try:

            save_to_supabase(

                project_name=
                    project_name,

                project_type=
                    project_type,

                team_size=
                    team_size,

                project_budget=
                    project_budget,

                timeline_months=
                    estimated_timeline_months,

                complexity_score=
                    complexity_score,

                total_tasks=
                    total_tasks,

                completed_tasks=
                    completed_tasks,

                overdue_tasks=
                    overdue_tasks,

                estimated_effort_hours=
                    estimated_effort_hours,

                actual_effort_hours=
                    actual_effort_hours,

                predicted_risk=
                    predicted_risk,

                probabilities=
                    probabilities
            )


        except Exception as e:

            print(
                "\nSUPABASE SAVE ERROR:"
            )

            print(e)

            return (
                "Prediction was successful, "
                "but saving to Supabase failed: "
                + str(e),
                500
            )


        # ====================================================
        # RESULT
        # ====================================================

        result_data = {

            "project_name":
                project_name,

            "risk_level":
                predicted_risk,

            "ai_confidence":
                ai_confidence,

            "probabilities":
                probabilities,

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

            "pending_tasks":
                pending_tasks,

            "project_progress":
                project_progress,

            "estimated_timeline_months":
                estimated_timeline_months,

            "complexity_score":
                complexity_score,

            "total_tasks":
                total_tasks,

            "completed_tasks":
                completed_tasks,

            "overdue_tasks":
                overdue_tasks,

            "estimated_effort_hours":
                estimated_effort_hours,

            "actual_effort_hours":
                actual_effort_hours
        }


        session[
            "result"
        ] = result_data


        return redirect(
            url_for("result")
        )


    except Exception as e:

        print(
            "\nPrediction error:",
            str(e)
        )

        return (
            f"Prediction error: {str(e)}",
            400
        )


# ============================================================
# RESULT
# ============================================================

@app.route(
    "/result"
)
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
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "project_form.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route(
    "/dashboard"
)
def dashboard():

    projects = []


    try:

        if supabase is None:

            raise Exception(
                "Supabase is not connected."
            )


        response = (
            supabase
            .table("projects")
            .select("*")
            .execute()
        )


        projects = (
            response.data or []
        )


        if (
            projects
            and
            "created_at" in projects[0]
        ):

            projects.sort(
                key=lambda item:
                    str(
                        item.get(
                            "created_at",
                            ""
                        )
                    ),
                reverse=True
            )


        print("\n==========================================")
        print("DASHBOARD DATA")
        print("==========================================")

        print(
            "Projects loaded:",
            len(projects)
        )


    except Exception as e:

        print(
            "\nDASHBOARD SUPABASE ERROR:"
        )

        print(e)

        projects = []


    # ========================================================
    # COUNTS
    # ========================================================

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


        for risk_name in counts:

            if (
                risk.lower()
                ==
                risk_name.lower()
            ):

                counts[
                    risk_name
                ] += 1

                break


    return render_template(
        "dashboard.html",
        projects=projects,
        counts=counts
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print("\n==========================================")
    print("STARTING FLASK APPLICATION")
    print("==========================================")

    print(
        "Model   :",
        os.path.basename(
            MODEL_PATH
        )
    )

    print(
        "Features:",
        len(
            MODEL_FEATURES
        )
    )

    print(
        "Supabase:",
        "Connected"
        if supabase
        else "NOT CONNECTED"
    )

    print("==========================================\n")


    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )