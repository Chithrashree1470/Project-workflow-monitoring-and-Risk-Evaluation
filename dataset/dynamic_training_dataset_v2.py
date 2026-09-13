import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "dynamic_training_dataset.csv"
OUTPUT_FILE = BASE_DIR / "dynamic_training_dataset_v2.csv"


print("=" * 70)
print("BUILDING DYNAMIC SNAPSHOT DATASET V2")
print("=" * 70)


# ============================================================
# LOAD EXISTING SNAPSHOT DATASET
# ============================================================

print("\nLoading existing dynamic dataset...")

df = pd.read_csv(INPUT_FILE)

print("Rows    :", len(df))
print("Columns :", len(df))
print("Projects:", df["project_id"].nunique())


# ============================================================
# DATE CONVERSION
# ============================================================

df["snapshot_date"] = pd.to_datetime(
    df["snapshot_date"],
    errors="coerce",
    utc=True
)

df = df.dropna(
    subset=[
        "project_id",
        "snapshot_date"
    ]
)


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    ["project_id", "snapshot_date"]
).reset_index(drop=True)


# ============================================================
# ORIGINAL SNAPSHOT FEATURES
# ============================================================

# These are the cumulative/current-state variables from V1.

TREND_COLUMNS = [
    "completion_percentage",
    "total_tasks",
    "pending_tasks",
    "transition_count",
    "reassignment_count",
    "reopen_count"
]


# ============================================================
# CREATE TEMPORAL FEATURES
# ============================================================

print("\nCreating temporal/trend features...")


# ------------------------------------------------------------
# 1-WEEK CHANGES
# ------------------------------------------------------------

for column in TREND_COLUMNS:

    print(f"Processing 1-week trend: {column}")

    previous = (
        df.groupby("project_id")[column]
        .shift(1)
    )

    df[f"{column}_change_1w"] = (
        df[column] - previous
    )


# ------------------------------------------------------------
# 4-WEEK CHANGES
# ------------------------------------------------------------

for column in TREND_COLUMNS:

    print(f"Processing 4-week trend: {column}")

    previous = (
        df.groupby("project_id")[column]
        .shift(4)
    )

    df[f"{column}_change_4w"] = (
        df[column] - previous
    )


# ============================================================
# MORE MEANINGFUL NAMED FEATURES
# ============================================================

print("\nCreating derived trend features...")


# ------------------------------------------------------------
# COMPLETION CHANGE
# ------------------------------------------------------------

df["completion_change_1w"] = (
    df["completion_percentage_change_1w"]
)

df["completion_change_4w"] = (
    df["completion_percentage_change_4w"]
)


# ------------------------------------------------------------
# TASK GROWTH
# ------------------------------------------------------------

df["tasks_change_1w"] = (
    df["total_tasks_change_1w"]
)

df["tasks_change_4w"] = (
    df["total_tasks_change_4w"]
)


# ------------------------------------------------------------
# PENDING TASK TREND
# ------------------------------------------------------------

df["pending_change_1w"] = (
    df["pending_tasks_change_1w"]
)

df["pending_change_4w"] = (
    df["pending_tasks_change_4w"]
)


# ------------------------------------------------------------
# WORKFLOW ACTIVITY TRENDS
# ------------------------------------------------------------

df["transition_change_1w"] = (
    df["transition_count_change_1w"]
)

df["transition_change_4w"] = (
    df["transition_count_change_4w"]
)

df["reassignment_change_1w"] = (
    df["reassignment_count_change_1w"]
)

df["reassignment_change_4w"] = (
    df["reassignment_count_change_4w"]
)

df["reopen_change_1w"] = (
    df["reopen_count_change_1w"]
)

df["reopen_change_4w"] = (
    df["reopen_count_change_4w"]
)


# ============================================================
# NEW TASKS IN LAST 4 WEEKS
# ============================================================

df["new_tasks_4w"] = (
    df["total_tasks_change_4w"]
)


# ============================================================
# COMPLETION RATE OVER LAST 4 WEEKS
# ============================================================

df["completion_rate_4w"] = (
    df["completion_percentage_change_4w"]
)


# ============================================================
# TASK GROWTH RATE
# ============================================================

tasks_4w_ago = (
    df.groupby("project_id")["total_tasks"]
    .shift(4)
)

df["task_growth_rate_4w"] = np.where(
    tasks_4w_ago > 0,
    (
        (df["total_tasks"] - tasks_4w_ago)
        / tasks_4w_ago
    ),
    np.nan
)


# ============================================================
# WORKFLOW INTENSITY
# ============================================================

# How much workflow activity occurred during the last week
# relative to the current number of tasks.

df["transitions_per_task_1w"] = np.where(
    df["total_tasks"] > 0,
    df["transition_change_1w"] /
    df["total_tasks"],
    0
)


df["reassignments_per_task_1w"] = np.where(
    df["total_tasks"] > 0,
    df["reassignment_change_1w"] /
    df["total_tasks"],
    0
)


df["reopens_per_task_1w"] = np.where(
    df["total_tasks"] > 0,
    df["reopen_change_1w"] /
    df["total_tasks"],
    0
)


# ============================================================
# BACKLOG PRESSURE
# ============================================================

df["pending_ratio"] = np.where(
    df["total_tasks"] > 0,
    df["pending_tasks"] /
    df["total_tasks"],
    0
)


pending_4w_ago = (
    df.groupby("project_id")["pending_tasks"]
    .shift(4)
)

df["pending_growth_4w"] = np.where(
    pending_4w_ago > 0,
    (
        (df["pending_tasks"] - pending_4w_ago)
        / pending_4w_ago
    ),
    np.nan
)


# ============================================================
# REBUILD 4-CLASS TARGET
# ============================================================

print("\nRebuilding 4-class dynamic risk labels...")


q25 = df[
    "future_delayed_rate"
].quantile(0.25)

q50 = df[
    "future_delayed_rate"
].quantile(0.50)

q75 = df[
    "future_delayed_rate"
].quantile(0.75)


print("\nRisk thresholds:")

print(
    f"Low / Medium      : {q25}"
)

print(
    f"Medium / High     : {q50}"
)

print(
    f"High / Critical   : {q75}"
)


def risk_label(value):

    if pd.isna(value):
        return np.nan

    if value <= q25:
        return "Low"

    elif value <= q50:
        return "Medium"

    elif value <= q75:
        return "High"

    else:
        return "Critical"


df["dynamic_risk_level"] = (
    df["future_delayed_rate"]
    .apply(risk_label)
)


# ============================================================
# REMOVE EARLY SNAPSHOTS
# ============================================================

# The first few snapshots of a project don't have enough
# history to calculate 4-week trends.
#
# We keep only snapshots where a 4-week historical state exists.

print("\nChecking temporal history...")

df["weeks_of_history"] = (
    df.groupby("project_id")
    .cumcount()
)


before = len(df)

df = df[
    df["weeks_of_history"] >= 4
].copy()

df.drop(
    columns=["weeks_of_history"],
    inplace=True
)

print(
    "Removed early snapshots:",
    before - len(df)
)

print(
    "Remaining snapshots:",
    len(df)
)


# ============================================================
# CLEAN INFINITE VALUES
# ============================================================

df = df.replace(
    [np.inf, -np.inf],
    np.nan
)


# ============================================================
# FILL TREND VALUES
# ============================================================

# Missing values can occur when an earlier snapshot has
# unavailable information. CatBoost can handle numerical
# missing values, so we intentionally retain NaN rather
# than replacing them with arbitrary values.

# ============================================================
# FINAL SORT
# ============================================================

df = df.sort_values(
    ["project_id", "snapshot_date"]
).reset_index(drop=True)


# ============================================================
# RISK DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("FINAL V2 DATASET")
print("=" * 70)

print(
    "Projects :",
    df["project_id"].nunique()
)

print(
    "Snapshots:",
    len(df)
)

print(
    "Columns  :",
    len(df.columns)
)


print("\nDynamic risk distribution:")

print(
    df["dynamic_risk_level"]
    .value_counts()
)


print("\nDynamic risk percentages:")

print(
    df["dynamic_risk_level"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)


# ============================================================
# SHOW NEW FEATURES
# ============================================================

NEW_FEATURES = [
    "completion_change_1w",
    "completion_change_4w",
    "tasks_change_1w",
    "tasks_change_4w",
    "pending_change_1w",
    "pending_change_4w",
    "transition_change_1w",
    "transition_change_4w",
    "reassignment_change_1w",
    "reassignment_change_4w",
    "reopen_change_1w",
    "reopen_change_4w",
    "new_tasks_4w",
    "completion_rate_4w",
    "task_growth_rate_4w",
    "transitions_per_task_1w",
    "reassignments_per_task_1w",
    "reopens_per_task_1w",
    "pending_ratio",
    "pending_growth_4w"
]


print("\nNew temporal features:")

for feature in NEW_FEATURES:

    print(
        " ✓",
        feature
    )


# ============================================================
# SAVE
# ============================================================

print("\nSaving V2 dataset...")

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC DATASET V2 CREATED")
print("=" * 70)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nFinal shape:")
print(df.shape)

print("\nReady for Dynamic CatBoost V2 training.")