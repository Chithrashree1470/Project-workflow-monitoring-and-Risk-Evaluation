import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TAWOS_PATH = BASE_DIR / "tawos_issue_ml.csv"

OUTPUT_PATH = (
    BASE_DIR / "tawos_phase1_training_dataset.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("BUILDING TAWOS PHASE 1 - LEAKAGE-FREE DATASET")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading TAWOS...")

EXPECTED_COLUMNS = [
    "ID",
    "Issue_Key",
    "Type",
    "Priority",
    "Status",
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date",
    "Last_Updated",
    "Story_Point",
    "Timespent",
    "Assignee_ID",
    "Project_ID",
    "Sprint_ID"
]

df = pd.read_csv(
    TAWOS_PATH,
    usecols=EXPECTED_COLUMNS,
    engine="python",
    on_bad_lines="skip"
)

print("Rows    :", len(df))
print("Columns :", len(df.columns))

print("\nDetected columns:")
print(df.columns.tolist())


# ============================================================
# DATE CONVERSION
# ============================================================

print("\nConverting dates...")

for column in [
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date"
]:

    df[column] = pd.to_datetime(
        df[column],
        errors="coerce",
        utc=True
    )


# ============================================================
# BASIC CLEANING
# ============================================================

df = df.dropna(
    subset=[
        "ID",
        "Project_ID",
        "Creation_Date",
        "Resolution_Date"
    ]
).copy()


df = df.drop_duplicates(
    subset=["ID"]
).copy()


print("\nTasks after basic cleaning:", len(df))
print("Projects:", df["Project_ID"].nunique())


# ============================================================
# NUMERIC CONVERSION
# ============================================================

df["Story_Point"] = pd.to_numeric(
    df["Story_Point"],
    errors="coerce"
)

df["Timespent"] = pd.to_numeric(
    df["Timespent"],
    errors="coerce"
)


# ============================================================
# ACTUAL DELAY
# ============================================================
#
# This is ONLY used to create the target.
#
# It will NEVER be used as a model feature.
# ============================================================

df["delay_days"] = (
    (
        df["Resolution_Date"]
        -
        df["Estimation_Date"]
    )
    .dt.total_seconds()
    / 86400
)


# Remove tasks where delay cannot be calculated.

df = df[
    df["delay_days"].notna()
].copy()


# Negative delay means the task finished before its
# estimation date.
#
# For the target, that is simply treated as zero delay.

df["delay_days"] = (
    df["delay_days"]
    .clip(lower=0)
)


print(
    "\nTasks with valid delay:",
    len(df)
)


# ============================================================
# TARGET BOUNDARIES
# ============================================================

q25 = df["delay_days"].quantile(0.25)
q50 = df["delay_days"].quantile(0.50)
q75 = df["delay_days"].quantile(0.75)


print("\nTarget boundaries:")

print(
    f"Low      : <= {q25:.2f} days"
)

print(
    f"Medium   : {q25:.2f} - {q50:.2f} days"
)

print(
    f"High     : {q50:.2f} - {q75:.2f} days"
)

print(
    f"Critical : > {q75:.2f} days"
)


def make_risk_label(delay):

    if delay <= q25:
        return "Low"

    elif delay <= q50:
        return "Medium"

    elif delay <= q75:
        return "High"

    else:
        return "Critical"


df["task_risk_level"] = (
    df["delay_days"]
    .apply(make_risk_label)
)


# ============================================================
# CREATION-TIME FEATURES
# ============================================================

print(
    "\nCreating leakage-free creation-time features..."
)


# ------------------------------------------------------------
# Estimated duration
# ------------------------------------------------------------
#
# Some TAWOS estimation dates occur before creation dates.
#
# Therefore we DO NOT delete those tasks.
#
# Invalid estimates become NaN.
# ------------------------------------------------------------

df["estimated_duration_days"] = (
    (
        df["Estimation_Date"]
        -
        df["Creation_Date"]
    )
    .dt.total_seconds()
    / 86400
)


df.loc[
    df["estimated_duration_days"] <= 0,
    "estimated_duration_days"
] = np.nan


# ------------------------------------------------------------
# Assignee
# ------------------------------------------------------------

df["has_assignee"] = (
    df["Assignee_ID"]
    .notna()
    .astype(int)
)


# ------------------------------------------------------------
# Sprint
# ------------------------------------------------------------

df["has_sprint"] = (
    df["Sprint_ID"]
    .notna()
    .astype(int)
)


# ------------------------------------------------------------
# Story points
# ------------------------------------------------------------

df["Story_Point"] = (
    df["Story_Point"]
    .fillna(0)
)


# ============================================================
# MODEL FEATURES
# ============================================================

PHASE1_FEATURES = [

    "Type",

    "Priority",

    "Story_Point",

    "estimated_duration_days",

    "has_assignee",

    "has_sprint"

]


# ============================================================
# FINAL DATASET
# ============================================================

OUTPUT_COLUMNS = [

    "ID",

    "Issue_Key",

    "Project_ID",

    "Creation_Date",

    "Estimation_Date",

    *PHASE1_FEATURES,

    # Target information
    "delay_days",

    "task_risk_level"

]


phase1 = df[
    OUTPUT_COLUMNS
].copy()


# ============================================================
# FINAL CLEANING
# ============================================================

phase1 = phase1.replace(
    [np.inf, -np.inf],
    np.nan
)


phase1 = phase1.dropna(
    subset=[
        "Project_ID",
        "task_risk_level"
    ]
).copy()


# Missing estimation duration is allowed.
#
# Fill it with the median of valid estimation durations.

median_estimation = (
    phase1["estimated_duration_days"]
    .median()
)


phase1["estimated_duration_days"] = (
    phase1["estimated_duration_days"]
    .fillna(median_estimation)
)


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1 TARGET DISTRIBUTION")
print("=" * 70)


print(
    phase1["task_risk_level"]
    .value_counts()
)


print("\nRisk percentages:")


print(
    phase1["task_risk_level"]
    .value_counts(
        normalize=True
    )
    .mul(100)
    .round(2)
)


# ============================================================
# DELAY STATISTICS
# ============================================================

print("\nDelay statistics:")


print(
    phase1
    .groupby(
        "task_risk_level"
    )["delay_days"]
    .agg([
        "count",
        "mean",
        "median",
        "min",
        "max"
    ])
)


# ============================================================
# PROJECT STATISTICS
# ============================================================

print("\nProject statistics:")


print(
    "Projects:",
    phase1["Project_ID"].nunique()
)


print(
    "Tasks   :",
    len(phase1)
)


# ============================================================
# FEATURES
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1 MODEL FEATURES")
print("=" * 70)


print(
    "Feature count:",
    len(PHASE1_FEATURES)
)


for feature in PHASE1_FEATURES:

    print(
        " ✓",
        feature
    )


# ============================================================
# SAVE
# ============================================================

phase1.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("TAWOS PHASE 1 DATASET CREATED")
print("=" * 70)


print(
    "\nProjects :",
    phase1["Project_ID"].nunique()
)


print(
    "Tasks    :",
    len(phase1)
)


print(
    "Columns  :",
    len(phase1.columns)
)


print(
    "Features :",
    len(PHASE1_FEATURES)
)


print("\nOutput:")
print(OUTPUT_PATH)


print("\n" + "=" * 70)
print("READY FOR PHASE 1 TAWOS TRAINING")
print("=" * 70)