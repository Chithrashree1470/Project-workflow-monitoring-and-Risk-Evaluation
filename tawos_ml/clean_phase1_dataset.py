import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "tawos_phase1_history_dataset.csv"
OUTPUT_FILE = DATA_DIR / "tawos_phase1_clean_dataset.csv"

print("=" * 70)
print("CLEANING TAWOS PHASE 1 DATASET")
print("=" * 70)

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print("Original rows   :", len(df))
print("Original columns:", len(df))


# ============================================================
# REMOVE ESTIMATE-DEPENDENT FEATURES
# ============================================================

REMOVE_COLUMNS = [
    "time_original_estimate",
    "has_estimate",
    "overrun_ratio",
    "delay_days"
]

df = df.drop(
    columns=[
        c for c in REMOVE_COLUMNS
        if c in df.columns
    ]
)


# ============================================================
# REMOVE TARGET-CONSTRUCTION INFORMATION
# ============================================================

# actual_duration_days is useful for analysing the target,
# but MUST NOT be used as a model feature.
#
# Keep it in this dataset for analysis.
# The training script must exclude it.


# ============================================================
# CLEAN MISSING VALUES
# ============================================================

categorical_columns = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

for col in categorical_columns:

    if col in df.columns:

        df[col] = (
            df[col]
            .fillna("Unknown")
            .astype(str)
        )


numeric_columns = [
    "story_points",
    "timespent",
    "task_age_days",
    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days"
]

for col in numeric_columns:

    if col in df.columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# Missing numerical values are kept as NaN.
# CatBoost can handle numerical NaN values.


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    ["issue_id", "snapshot_date"]
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# REPORT
# ============================================================

print("\n" + "=" * 70)
print("CLEAN DATASET")
print("=" * 70)

print("Projects :", df["project_id"].nunique())
print("Issues   :", df["issue_id"].nunique())
print("Snapshots:", len(df))
print("Columns  :", len(df.columns))

print("\nRemaining columns:")

for col in df.columns:
    print(" ✓", col)

print("\nTarget distribution:")

print(
    df["task_risk_level"]
    .value_counts()
)

print("\nTarget percentages:")

print(
    (
        df["task_risk_level"]
        .value_counts(normalize=True) * 100
    ).round(2)
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("=" * 70)