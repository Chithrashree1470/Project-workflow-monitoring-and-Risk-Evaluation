import pandas as pd
import numpy as np

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

V2_PATH = (
    BASE_DIR
    / "dynamic_training_dataset_v2.csv"
)

V3_PATH = (
    BASE_DIR
    / "dynamic_training_dataset_v3.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("BUILDING TRIMMED DYNAMIC SNAPSHOT DATASET V3")
print("=" * 70)


# ============================================================
# LOAD V2
# ============================================================

print("\nLoading V2 dataset...")

dynamic = pd.read_csv(V2_PATH)

print("Rows    :", len(dynamic))
print("Projects:", dynamic["project_id"].nunique())
print("Columns :", len(dynamic.columns))


# ============================================================
# DATE CONVERSION
# ============================================================

print("\nConverting dates...")

dynamic["snapshot_date"] = pd.to_datetime(
    dynamic["snapshot_date"],
    errors="coerce",
    utc=True
)

dynamic = dynamic.dropna(
    subset=[
        "project_id",
        "snapshot_date",
        "dynamic_risk_level"
    ]
)

dynamic = dynamic.sort_values(
    ["project_id", "snapshot_date"]
).reset_index(drop=True)


# ============================================================
# REMOVE DUPLICATE SNAPSHOTS
# ============================================================

before = len(dynamic)

dynamic = dynamic.drop_duplicates(
    subset=[
        "project_id",
        "snapshot_date"
    ]
).reset_index(drop=True)

print(
    "Duplicate snapshots removed:",
    before - len(dynamic)
)


# ============================================================
# SAFE DIVISION
# ============================================================

def safe_divide(a, b):

    return (
        a
        / b.replace(0, np.nan)
    ).replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(0)


# ============================================================
# CREATE SELECTED V3 FEATURES
# ============================================================
#
# We intentionally keep only selected derived features.
#
# These were among the more useful features in the previous
# V3 experiment.
#
# V2 already contains many temporal features, so we avoid
# adding redundant versions of the same measurements.
# ============================================================

print("\nCreating selected V3 features...")


def process_project(group):

    group = group.sort_values(
        "snapshot_date"
    ).copy()


    # --------------------------------------------------------
    # 1. COMPLETED TASK RATIO
    # --------------------------------------------------------

    group["completed_ratio"] = safe_divide(
        group["completed_tasks"],
        group["total_tasks"]
    )


    # --------------------------------------------------------
    # 2. REASSIGNMENT RATE
    # --------------------------------------------------------

    group["reassignment_rate"] = safe_divide(
        group["reassignment_count"],
        group["total_tasks"]
    )


    # --------------------------------------------------------
    # 3. REOPEN RATE
    # --------------------------------------------------------

    group["reopen_rate"] = safe_divide(
        group["reopen_count"],
        group["total_tasks"]
    )


    # --------------------------------------------------------
    # 4. TRANSITION RATE
    # --------------------------------------------------------

    group["transition_rate"] = safe_divide(
        group["transition_count"],
        group["total_tasks"]
    )


    # --------------------------------------------------------
    # 5. COMPLETION VELOCITY - 4 WEEKS
    # --------------------------------------------------------

    group["completion_velocity_4w"] = (
        group["completion_percentage"]
        .diff(4)
    )


    # --------------------------------------------------------
    # 6. COMPLETED TASK CHANGE - 4 WEEKS
    # --------------------------------------------------------

    group["completed_tasks_change_4w"] = (
        group["completed_tasks"]
        .diff(4)
    )


    # --------------------------------------------------------
    # 7. PENDING RATIO
    # --------------------------------------------------------

    group["pending_ratio_v3"] = safe_divide(
        group["pending_tasks"],
        group["total_tasks"]
    )


    # --------------------------------------------------------
    # 8. PENDING RATIO CHANGE - 4 WEEKS
    # --------------------------------------------------------

    group["pending_ratio_change_4w"] = (
        group["pending_ratio_v3"]
        .diff(4)
    )


    # --------------------------------------------------------
    # 9. REASSIGNMENT RATE CHANGE - 4 WEEKS
    # --------------------------------------------------------

    group["reassignment_rate_change_4w"] = (
        group["reassignment_rate"]
        .diff(4)
    )


    # --------------------------------------------------------
    # 10. REOPEN RATE CHANGE - 4 WEEKS
    # --------------------------------------------------------

    group["reopen_rate_change_4w"] = (
        group["reopen_rate"]
        .diff(4)
    )


    # --------------------------------------------------------
    # 11. COMPLETION ACCELERATION
    # --------------------------------------------------------

    completion_velocity = (
        group["completion_percentage"]
        .diff(1)
    )

    group["completion_acceleration"] = (
        completion_velocity.diff(1)
    )


    # --------------------------------------------------------
    # 12. COMPLETION PER PROJECT DAY
    # --------------------------------------------------------

    group["completion_per_day"] = safe_divide(
        group["completion_percentage"],
        group["project_age_days"]
    )


    # --------------------------------------------------------
    # 13. TASK GROWTH VS COMPLETION
    # --------------------------------------------------------

    group["task_growth_vs_completion"] = (
        group["total_tasks_change_4w"]
        -
        group["completed_tasks_change_4w"]
    )


    # --------------------------------------------------------
    # 14. TRANSITIONS PER ASSIGNEE
    # --------------------------------------------------------

    group["transitions_per_assignee"] = safe_divide(
        group["transition_count"],
        group["assignee_count"]
    )


    # --------------------------------------------------------
    # 15. RISK PRESSURE SCORE
    # --------------------------------------------------------
    #
    # Combines several current-state risk signals.
    #
    # This is a derived feature, NOT the target.
    # --------------------------------------------------------

    high_priority_ratio = safe_divide(
        group["high_priority_task_count"],
        group["total_tasks"]
    )

    critical_ratio = safe_divide(
        group["critical_task_count"],
        group["total_tasks"]
    )

    group["risk_pressure_score"] = (
        group["pending_ratio_v3"]
        +
        group["reassignment_rate"]
        +
        group["reopen_rate"]
        +
        high_priority_ratio
        +
        critical_ratio
    )


    return group


# ============================================================
# PROCESS PROJECTS
# ============================================================

projects = dynamic["project_id"].unique()

processed = []

for index, project_id in enumerate(projects):

    group = dynamic[
        dynamic["project_id"] == project_id
    ].copy()

    processed.append(
        process_project(group)
    )

    if (
        (index + 1) % 20 == 0
        or index + 1 == len(projects)
    ):

        print(
            f"Processed projects: "
            f"{index + 1}/{len(projects)}"
        )


dynamic = pd.concat(
    processed,
    ignore_index=True
)


# ============================================================
# CLEAN INVALID VALUES
# ============================================================

print("\nCleaning invalid values...")

numeric_columns = dynamic.select_dtypes(
    include=[np.number]
).columns

dynamic[numeric_columns] = (
    dynamic[numeric_columns]
    .replace(
        [np.inf, -np.inf],
        np.nan
    )
    .fillna(0)
)


# ============================================================
# REMOVE SNAPSHOTS WITHOUT HISTORY
# ============================================================
#
# At least one previous snapshot is required for the newly
# created temporal features.
# ============================================================

before = len(dynamic)

dynamic = dynamic[
    dynamic.groupby("project_id")
    .cumcount() >= 1
].copy()

dynamic = dynamic.reset_index(
    drop=True
)

print(
    "Rows removed because no previous snapshot:",
    before - len(dynamic)
)


# ============================================================
# MODEL FEATURES
# ============================================================

EXCLUDED_COLUMNS = [

    "project_id",
    "snapshot_date",

    # Future information
    "future_completed_30d",
    "future_delayed_30d",
    "future_delayed_rate",

    # Target
    "dynamic_risk_level"
]


FEATURES = [
    column
    for column in dynamic.columns
    if column not in EXCLUDED_COLUMNS
]


# ============================================================
# DATASET SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC DATASET V3 CREATED")
print("=" * 70)

print(
    "\nProjects :",
    dynamic["project_id"].nunique()
)

print(
    "Snapshots:",
    len(dynamic)
)

print(
    "Columns  :",
    len(dynamic.columns)
)

print(
    "Features :",
    len(FEATURES)
)


# ============================================================
# RISK DISTRIBUTION
# ============================================================

print("\nRisk distribution:")

print(
    dynamic["dynamic_risk_level"]
    .value_counts()
)


print("\nRisk percentages:")

print(
    dynamic["dynamic_risk_level"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)


# ============================================================
# FUTURE DELAY RATE
# ============================================================

print("\nFuture delayed rate:")

print(
    dynamic["future_delayed_rate"]
    .describe()
)


# ============================================================
# NEW FEATURES
# ============================================================

NEW_FEATURES = [

    "completed_ratio",
    "reassignment_rate",
    "reopen_rate",
    "transition_rate",
    "completion_velocity_4w",
    "completed_tasks_change_4w",
    "pending_ratio_v3",
    "pending_ratio_change_4w",
    "reassignment_rate_change_4w",
    "reopen_rate_change_4w",
    "completion_acceleration",
    "completion_per_day",
    "task_growth_vs_completion",
    "transitions_per_assignee",
    "risk_pressure_score"
]


print("\nSelected V3 derived features:")

for feature in NEW_FEATURES:

    print(
        " ✓",
        feature
    )


# ============================================================
# SAVE
# ============================================================

dynamic.to_csv(
    V3_PATH,
    index=False
)


# ============================================================
# OUTPUT
# ============================================================

print("\nOutput:")
print(V3_PATH)

print("\n" + "=" * 70)
print("READY FOR V3 DYNAMIC CATBOOST TRAINING")
print("=" * 70)