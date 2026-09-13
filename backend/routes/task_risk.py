import os
from pathlib import Path

import pandas as pd

from flask import Blueprint, jsonify, request
from dotenv import load_dotenv

from catboost import CatBoostClassifier
from supabase import create_client


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAWOS_ML_DIR = PROJECT_ROOT / "tawos_ml"

MODEL_PATH = (
    TAWOS_ML_DIR
    / "phase1_catboost_with_sprint.pkl"
)

MODEL_VERSION = "phase1_10projects_v1"


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(
    PROJECT_ROOT / ".env"
)

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
# LOAD MODEL ONCE
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

model = CatBoostClassifier()

model.load_model(
    MODEL_PATH
)


# ============================================================
# BLUEPRINT
# ============================================================

task_risk_bp = Blueprint(
    "task_risk",
    __name__,
    url_prefix="/api/task-risk"
)


# ============================================================
# FEATURES
# ============================================================

FEATURES = [
    "issue_type",
    "priority",
    "status",
    "story_points",
    "story_points_missing",
    "timespent",
    "assignee",
    "sprint",
    "task_age_days",
    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days"
]


CATEGORICAL = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]


# ============================================================
# RISK VALUES
# ============================================================

RISK_VALUES = {
    "Low": 0.00,
    "Medium": 0.33,
    "High": 0.67,
    "Critical": 1.00
}


# ============================================================
# PROJECT RISK THRESHOLDS
# ============================================================

def get_project_risk_level(score):

    if score >= 0.75:
        return "Critical"

    elif score >= 0.55:
        return "High"

    elif score >= 0.30:
        return "Medium"

    else:
        return "Low"


# ============================================================
# PROJECT RISK AGGREGATOR
# ============================================================

def calculate_project_dynamic_risk(project_id):

    """
    Calculate the current project risk using the latest
    prediction for every task in the project.

    Also compares the current project risk against the
    previous project risk stored in project_dynamic_risk.
    """

    # --------------------------------------------------------
    # GET CURRENT TASK PREDICTIONS
    # --------------------------------------------------------

    response = (
        supabase
        .table("task_risk_prediction")
        .select(
            "issue_id, risk_score, risk_label"
        )
        .eq(
            "project_id",
            project_id
        )
        .execute()
    )

    predictions = response.data or []

    if not predictions:

        return None


    df = pd.DataFrame(
        predictions
    )


    # --------------------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------------------

    total_tasks = len(df)

    high_task_count = int(
        (
            df["risk_label"]
            .isin(["High", "Critical"])
        )
        .sum()
    )

    critical_task_count = int(
        (
            df["risk_label"]
            == "Critical"
        )
        .sum()
    )


    # --------------------------------------------------------
    # CURRENT PROJECT RISK
    # --------------------------------------------------------

    current_score = float(
        df["risk_score"].mean()
    )

    current_level = (
        get_project_risk_level(
            current_score
        )
    )


    # --------------------------------------------------------
    # GET PREVIOUS PROJECT RISK
    # --------------------------------------------------------

    previous_response = (
        supabase
        .table("project_dynamic_risk")
        .select(
            "risk_score"
        )
        .eq(
            "project_id",
            project_id
        )
        .limit(1)
        .execute()
    )

    previous_data = (
        previous_response.data or []
    )

    previous_score = None

    if previous_data:

        previous_score = float(
            previous_data[0]["risk_score"]
        )


    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    if previous_score is None:

        trend = "Stable"

        risk_change = 0.0

    else:

        risk_change = (
            current_score
            - previous_score
        )

        if risk_change > 0.05:

            trend = "Worsening"

        elif risk_change < -0.05:

            trend = "Improving"

        else:

            trend = "Stable"


    # --------------------------------------------------------
    # BUILD RECORD
    # --------------------------------------------------------

    project_record = {

        "project_id":
            project_id,

        "risk_score":
            current_score,

        "risk_level":
            current_level,

        "total_task_count":
            total_tasks,

        "high_task_count":
            high_task_count,

        "critical_task_count":
            critical_task_count,

        "risk_trend":
            trend,

        "risk_change":
            risk_change,

        "model_version":
            MODEL_VERSION
    }


    # --------------------------------------------------------
    # UPDATE PROJECT DYNAMIC RISK
    # --------------------------------------------------------

    (
        supabase
        .table("project_dynamic_risk")
        .delete()
        .eq(
            "project_id",
            project_id
        )
        .execute()
    )

    (
        supabase
        .table("project_dynamic_risk")
        .insert({
            "project_id": project_id,
            "risk_score": current_score,
            "risk_level": current_level,
            "total_task_count": total_tasks,
            "high_task_count": high_task_count,
            "critical_task_count": critical_task_count,
            "risk_trend": trend,
            "risk_change": risk_change
        })
        .execute()
    )


    return project_record


# ============================================================
# HEALTH
# ============================================================

@task_risk_bp.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status": "ok",

        "model":
            MODEL_VERSION

    })


# ============================================================
# PREDICT TASK RISK
# ============================================================

@task_risk_bp.route(
    "/predict",
    methods=["POST"]
)
def predict_task_risk():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error":
                    "Request body is required."
            }), 400


        # ----------------------------------------------------
        # REQUIRED IDS
        # ----------------------------------------------------

        if "project_id" not in data:

            return jsonify({
                "error":
                    "project_id is required."
            }), 400


        if "issue_id" not in data:

            return jsonify({
                "error":
                    "issue_id is required."
            }), 400


        project_id = int(
            data["project_id"]
        )

        issue_id = int(
            data["issue_id"]
        )


        # ----------------------------------------------------
        # BUILD MODEL INPUT
        # ----------------------------------------------------

        row = {}

        for feature in FEATURES:

            value = data.get(
                feature
            )

            if feature in CATEGORICAL:

                if (
                    value is None
                    or value == ""
                ):

                    value = "Unknown"

                value = str(value)

            else:

                if value is None:

                    if (
                        feature
                        == "story_points_missing"
                    ):

                        value = 1

                    else:

                        value = 0

            row[feature] = value


        X = pd.DataFrame(
            [row],
            columns=FEATURES
        )


        # ----------------------------------------------------
        # MODEL PREDICTION
        # ----------------------------------------------------

        probabilities = (
            model
            .predict_proba(X)[0]
        )

        predicted_class = (
            model
            .predict(X)[0][0]
        )


        # ----------------------------------------------------
        # PROBABILITY MAP
        # ----------------------------------------------------

        class_names = list(
            model.classes_
        )

        probability_map = {

            class_names[i]:
                float(probabilities[i])

            for i in range(
                len(class_names)
            )
        }


        # ----------------------------------------------------
        # CONTINUOUS RISK SCORE
        # ----------------------------------------------------

        risk_score = sum(

            probability_map.get(
                label,
                0
            )
            * score

            for label, score
            in RISK_VALUES.items()

        )


        # ====================================================
        # CURRENT PREDICTION RECORD
        # ====================================================

        record = {

            "project_id":
                project_id,

            "issue_id":
                issue_id,

            "risk_label":
                predicted_class,

            "risk_score":
                float(risk_score),

            "low_probability":
                probability_map.get(
                    "Low",
                    0
                ),

            "medium_probability":
                probability_map.get(
                    "Medium",
                    0
                ),

            "high_probability":
                probability_map.get(
                    "High",
                    0
                ),

            "critical_probability":
                probability_map.get(
                    "Critical",
                    0
                ),

            "model_version":
                MODEL_VERSION
        }


        # ====================================================
        # UPDATE CURRENT PREDICTION
        # ====================================================

        (
            supabase
            .table(
                "task_risk_prediction"
            )
            .delete()
            .eq(
                "issue_id",
                issue_id
            )
            .execute()
        )


        (
            supabase
            .table(
                "task_risk_prediction"
            )
            .insert(
                record
            )
            .execute()
        )


        # ====================================================
        # APPEND TO HISTORY
        # ====================================================

        (
            supabase
            .table(
                "task_risk_history"
            )
            .insert(
                record
            )
            .execute()
        )


        # ====================================================
        # UPDATE PROJECT RISK
        # ====================================================

        project_risk = (
            calculate_project_dynamic_risk(
                project_id
            )
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "project_id":
                project_id,

            "issue_id":
                issue_id,

            "risk_label":
                predicted_class,

            "risk_score":
                round(
                    float(
                        risk_score
                    ),
                    4
                ),

            "probabilities":
                probability_map,

            "model_version":
                MODEL_VERSION,

            "project_risk":
                project_risk

        })


    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500