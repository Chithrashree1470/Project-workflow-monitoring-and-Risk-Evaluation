import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR.parent.parent
    / "dataset"
    / "tawos_phase1_training_dataset.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 DATASET ANALYSIS")
print("=" * 70)


# ============================================================
# LOAD
# ============================================================

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print("Rows    :", len(df))
print("Columns :", len(df))

print("\nColumns:")
for column in df.columns:
    print(" ✓", column)


# ============================================================
# DATE CONVERSION
# ============================================================

for column in [
    "Creation_Date",
    "Estimation_Date"
]:

    if column in df.columns:

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce",
            utc=True
        )


# ============================================================
# 1. ESTIMATION DATE VALIDITY
# ============================================================

print("\n" + "=" * 70)
print("1. ESTIMATION DATE ANALYSIS")
print("=" * 70)


total = len(df)

valid_estimation = df["Estimation_Date"].notna().sum()

print(
    f"\nValid Estimation_Date : "
    f"{valid_estimation} / {total} "
    f"({valid_estimation / total * 100:.2f}%)"
)


# ============================================================
# 2. ESTIMATION AFTER CREATION
# ============================================================

valid_both = df[
    df["Creation_Date"].notna()
    &
    df["Estimation_Date"].notna()
].copy()


valid_both["raw_estimation_duration"] = (
    valid_both["Estimation_Date"]
    -
    valid_both["Creation_Date"]
).dt.total_seconds() / 86400


positive_estimates = (
    valid_both["raw_estimation_duration"] > 0
).sum()


negative_estimates = (
    valid_both["raw_estimation_duration"] <= 0
).sum()


print(
    "\nTasks with both dates:",
    len(valid_both)
)

print(
    f"Estimation AFTER creation : "
    f"{positive_estimates} "
    f"({positive_estimates / max(len(valid_both), 1) * 100:.2f}%)"
)

print(
    f"Estimation BEFORE/same as creation : "
    f"{negative_estimates} "
    f"({negative_estimates / max(len(valid_both), 1) * 100:.2f}%)"
)


# ============================================================
# 3. ESTIMATED DURATION
# ============================================================

print("\n" + "=" * 70)
print("2. ESTIMATED DURATION ANALYSIS")
print("=" * 70)


duration = pd.to_numeric(
    df["estimated_duration_days"],
    errors="coerce"
)


print(
    "\nValid estimated_duration_days:",
    duration.notna().sum()
)

print(
    "Missing:",
    duration.isna().sum()
)


if duration.notna().any():

    print("\nStatistics:")

    print(
        duration.describe()
    )

    print(
        "\nZero/negative:",
        (duration <= 0).sum()
    )

else:

    print(
        "\nWARNING: estimated_duration_days "
        "contains NO valid values."
    )


# ============================================================
# 4. BASIC FEATURE DISTRIBUTIONS
# ============================================================

print("\n" + "=" * 70)
print("3. CREATION-TIME FEATURE ANALYSIS")
print("=" * 70)


for column in [
    "Type",
    "Priority",
    "Story_Point",
    "has_assignee",
    "has_sprint"
]:

    print("\n" + "-" * 60)
    print(column)

    print(
        "Missing:",
        df[column].isna().sum()
    )

    print(
        "Unique:",
        df[column].nunique(dropna=True)
    )

    print("\nDistribution:")

    print(
        df[column]
        .value_counts(dropna=False)
        .head(20)
    )


# ============================================================
# 5. TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("4. TARGET ANALYSIS")
print("=" * 70)


target = "task_risk_level"


print("\nTarget distribution:")

target_counts = (
    df[target]
    .value_counts()
)


print(target_counts)


print("\nTarget percentages:")

print(
    df[target]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)


# ============================================================
# 6. TARGET VS FEATURES
# ============================================================

print("\n" + "=" * 70)
print("5. TARGET VS CREATION-TIME FEATURES")
print("=" * 70)


print("\nRisk by Type:")

print(
    pd.crosstab(
        df["Type"],
        df[target],
        normalize="index"
    )
    .mul(100)
    .round(2)
)


print("\nRisk by Priority:")

print(
    pd.crosstab(
        df["Priority"],
        df[target],
        normalize="index"
    )
    .mul(100)
    .round(2)
)


print("\nRisk by Has Assignee:")

print(
    pd.crosstab(
        df["has_assignee"],
        df[target],
        normalize="index"
    )
    .mul(100)
    .round(2)
)


print("\nRisk by Has Sprint:")

print(
    pd.crosstab(
        df["has_sprint"],
        df[target],
        normalize="index"
    )
    .mul(100)
    .round(2)
)


# ============================================================
# 7. STORY POINTS VS TARGET
# ============================================================

print("\n" + "=" * 70)
print("6. STORY POINT ANALYSIS")
print("=" * 70)


story = pd.to_numeric(
    df["Story_Point"],
    errors="coerce"
)


story_summary = (
    df.assign(
        Story_Point_numeric=story
    )
    .groupby(target)["Story_Point_numeric"]
    .agg([
        "count",
        "mean",
        "median",
        "min",
        "max"
    ])
)


print(story_summary)


# ============================================================
# 8. TARGET VS ESTIMATED DURATION
# ============================================================

print("\n" + "=" * 70)
print("7. ESTIMATION VS TARGET")
print("=" * 70)


estimation_summary = (
    df.assign(
        estimated_duration_numeric=duration
    )
    .groupby(target)["estimated_duration_numeric"]
    .agg([
        "count",
        "mean",
        "median",
        "min",
        "max"
    ])
)


print(estimation_summary)


# ============================================================
# 9. PROJECT DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("8. PROJECT ANALYSIS")
print("=" * 70)


project_counts = (
    df.groupby("Project_ID")
    .size()
    .sort_values(ascending=False)
)


print(
    "\nProjects:",
    df["Project_ID"].nunique()
)


print("\nTasks per project:")

print(
    project_counts.describe()
)


# ============================================================
# 10. TARGET BY PROJECT
# ============================================================

print("\nTarget distribution by project:")

project_target = pd.crosstab(
    df["Project_ID"],
    df[target],
    normalize="index"
).mul(100).round(2)


print(project_target.head(20))


# ============================================================
# 11. LEAKAGE CHECK
# ============================================================

print("\n" + "=" * 70)
print("9. LEAKAGE CHECK")
print("=" * 70)


suspicious_columns = [

    "delay_days",
    "task_risk_level",
    "Resolution_Date",
    "Last_Updated",
    "Timespent",
    "Status",
    "Assignee_ID",
    "Sprint_ID"

]


print(
    "\nColumns that must NOT be Phase 1 prediction features:"
)


for column in suspicious_columns:

    if column in df.columns:

        print(
            " ⚠",
            column
        )


# ============================================================
# 12. TARGET RELATIONSHIP WITH DELAY
# ============================================================

print("\n" + "=" * 70)
print("10. TARGET / DELAY VALIDATION")
print("=" * 70)


if "delay_days" in df.columns:

    delay = pd.to_numeric(
        df["delay_days"],
        errors="coerce"
    )

    delay_summary = (
        df.assign(
            delay_numeric=delay
        )
        .groupby(target)["delay_numeric"]
        .agg([
            "count",
            "mean",
            "median",
            "min",
            "max"
        ])
    )

    print(
        delay_summary
    )


# ============================================================
# 13. FINAL DIAGNOSIS
# ============================================================

print("\n" + "=" * 70)
print("DATASET DIAGNOSIS")
print("=" * 70)


if valid_estimation == 0:

    print(
        "\nWARNING:"
        "\nNo valid estimation dates exist."
        "\nThe estimated-duration feature cannot provide useful signal."
    )

elif positive_estimates == 0:

    print(
        "\nWARNING:"
        "\nNo estimation dates occur after creation."
        "\nEstimated duration is therefore not usable."
    )

else:

    print(
        "\nEstimation dates contain usable information."
    )


print(
    "\nPhase 1 dataset size:",
    len(df)
)

print(
    "Projects:",
    df["Project_ID"].nunique()
)

print(
    "Target classes:",
    df[target].nunique()
)


print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)