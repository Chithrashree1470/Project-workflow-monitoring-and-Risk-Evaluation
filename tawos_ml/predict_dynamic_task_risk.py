import os
import pandas as pd
import numpy as np

from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from catboost import CatBoostClassifier


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "tawos_phase1_10history_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "phase1_catboost_with_sprint.pkl"
)

MODEL_VERSION = "phase1_10projects_v1"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(
    BASE_DIR.parent / ".env"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

if not SUPABASE_URL:
    raise ValueError(
        "SUPABASE_URL is missing from .env"
    )

if not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_KEY is missing from .env"
    )


# ============================================================
# CONNECT SUPABASE
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("TAWOS - DYNAMIC TASK RISK PREDICTION")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(
    DATA_PATH,
    low_memory=False
)

print(
    "Rows    :",
    len(df)
)

print(
    "Issues  :",
    df["issue_id"].nunique()
)

print(
    "Projects:",
    df["project_id"].nunique()
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


missing = [
    col
    for col in FEATURES + [
        "issue_id",
        "project_id"
    ]
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Missing columns: {missing}"
    )


# ============================================================
# CLEAN CATEGORICAL FEATURES
# ============================================================

for col in CATEGORICAL:

    df[col] = (
        df[col]
        .fillna("Unknown")
        .astype(str)
    )


# ============================================================
# USE LATEST SNAPSHOT PER ISSUE
#
# For the MVP we want one CURRENT prediction per task.
# Historical snapshots are kept in the dataset but are not
# all uploaded as current task predictions.
# ============================================================

df = df.sort_values(
    [
        "issue_id",
        "snapshot_date",
        "snapshot_number"
    ]
)

current_df = (
    df
    .groupby(
        "issue_id",
        as_index=False
    )
    .tail(1)
    .copy()
)

print(
    "\nCurrent tasks:",
    len(current_df)
)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading CatBoost model...")

model = CatBoostClassifier()

model.load_model(
    MODEL_PATH
)

print(
    "Model:",
    MODEL_PATH
)


# ============================================================
# PREPARE FEATURES
# ============================================================

X = current_df[
    FEATURES
].copy()


# ============================================================
# PREDICT
# ============================================================

print("\nGenerating predictions...")

probabilities = model.predict_proba(
    X
)

predictions = (
    model
    .predict(X)
    .ravel()
)


# ============================================================
# CLASS ORDER
# ============================================================

class_names = [
    "Low",
    "Medium",
    "High",
    "Critical"
]


# ============================================================
# CONTINUOUS RISK SCORE
#
# Low       = 0.00
# Medium    = 0.33
# High      = 0.67
# Critical  = 1.00
# ============================================================

risk_values = np.array([
    0.00,
    0.33,
    0.67,
    1.00
])


risk_scores = (
    probabilities
    @ risk_values
)


# ============================================================
# BUILD PREDICTION DATAFRAME
# ============================================================

prediction_df = pd.DataFrame({

    "project_id":
        current_df[
            "project_id"
        ].astype(int),

    "issue_id":
        current_df[
            "issue_id"
        ].astype(int),

    "risk_label":
        predictions,

    "risk_score":
        risk_scores,

    "low_probability":
        probabilities[:, 0],

    "medium_probability":
        probabilities[:, 1],

    "high_probability":
        probabilities[:, 2],

    "critical_probability":
        probabilities[:, 3]
})


prediction_df[
    "model_version"
] = MODEL_VERSION


print("\nRisk distribution:")

print(
    prediction_df[
        "risk_label"
    ].value_counts()
)


print("\nRisk score statistics:")

print(
    prediction_df[
        "risk_score"
    ].describe()
)


# ============================================================
# UPLOAD TASK PREDICTIONS
# ============================================================

print("\nUploading task predictions...")

task_records = (
    prediction_df
    .replace({
        np.nan: None
    })
    .to_dict(
        orient="records"
    )
)


# ============================================================
# MVP: CLEAR PREVIOUS CURRENT PREDICTIONS
#
# Since this is a temporary MVP database, we replace the
# current prediction set on every run.
# ============================================================

print(
    "Clearing previous task predictions..."
)

delete_response = (
    supabase
    .table(
        "task_risk_prediction"
    )
    .delete()
    .neq(
        "id",
        0
    )
    .execute()
)


# ============================================================
# INSERT IN BATCHES
# ============================================================

BATCH_SIZE = 500

for start in range(
    0,
    len(task_records),
    BATCH_SIZE
):

    batch = task_records[
        start:
        start + BATCH_SIZE
    ]

    (
        supabase
        .table(
            "task_risk_prediction"
        )
        .insert(batch)
        .execute()
    )

    print(
        f"Uploaded "
        f"{min(start + BATCH_SIZE, len(task_records))}"
        f"/{len(task_records)}"
    )


# ============================================================
# PROJECT AGGREGATION
# ============================================================

print("\nCalculating project dynamic risk...")


project_risk = (
    prediction_df
    .groupby(
        "project_id"
    )
    .agg(

        risk_score=(
            "risk_score",
            "mean"
        ),

        total_task_count=(
            "issue_id",
            "count"
        ),

        high_task_count=(
            "risk_label",
            lambda x:
                (x == "High").sum()
                +
                (x == "Critical").sum()
        ),

        critical_task_count=(
            "risk_label",
            lambda x:
                (x == "Critical").sum()
        )

    )
    .reset_index()
)


# ============================================================
# MAP SCORE → RISK LEVEL
# ============================================================

def score_to_level(score):

    if score < 0.25:
        return "Low"

    elif score < 0.50:
        return "Medium"

    elif score < 0.75:
        return "High"

    else:
        return "Critical"


project_risk[
    "risk_level"
] = (
    project_risk[
        "risk_score"
    ]
    .apply(score_to_level)
)


print("\nProject dynamic risk:")

print(
    project_risk.to_string(
        index=False
    )
)


# ============================================================
# UPLOAD PROJECT RISK
# ============================================================

project_records = (
    project_risk
    .replace({
        np.nan: None
    })
    .to_dict(
        orient="records"
    )
)


print(
    "\nClearing previous project dynamic risks..."
)

(
    supabase
    .table(
        "project_dynamic_risk"
    )
    .delete()
    .neq(
        "id",
        0
    )
    .execute()
)


print(
    "Uploading project dynamic risks..."
)

(
    supabase
    .table(
        "project_dynamic_risk"
    )
    .insert(
        project_records
    )
    .execute()
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC RISK PIPELINE COMPLETE")
print("=" * 70)

print(
    "\nTask predictions:",
    len(prediction_df)
)

print(
    "Projects:",
    len(project_risk)
)

print(
    "\nTask predictions stored in:"
)

print(
    "task_risk_prediction"
)

print(
    "\nProject risks stored in:"
)

print(
    "project_dynamic_risk"
)

print(
    "\nModel version:",
    MODEL_VERSION
)