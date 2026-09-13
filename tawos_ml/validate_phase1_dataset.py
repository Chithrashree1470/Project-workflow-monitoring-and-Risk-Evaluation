import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATASET = DATA_DIR / "tawos_phase1_history_dataset.csv"


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 DATASET VALIDATION")
print("=" * 70)

df = pd.read_csv(
    DATASET,
    low_memory=False
)

print("\nRows    :", len(df))
print("Columns :", len(df))

print("\nColumns:")
for col in df.columns:
    print(" ✓", col)


# ============================================================
# 1. BASIC DATASET CHECK
# ============================================================

print("\n" + "=" * 70)
print("1. BASIC DATASET CHECK")
print("=" * 70)

print("Projects :", df["project_id"].nunique())
print("Issues   :", df["issue_id"].nunique())
print("Snapshots:", len(df))

print("\nSnapshots per issue:")

snapshots_per_issue = (
    df.groupby("issue_id")
    .size()
)

print(
    snapshots_per_issue.describe()
)


# ============================================================
# 2. DUPLICATE CHECK
# ============================================================

print("\n" + "=" * 70)
print("2. DUPLICATE CHECK")
print("=" * 70)

duplicate_rows = df.duplicated().sum()

duplicate_snapshots = df.duplicated(
    subset=[
        "issue_id",
        "snapshot_date"
    ]
).sum()

print(
    "Duplicate complete rows       :",
    duplicate_rows
)

print(
    "Duplicate issue/snapshot rows:",
    duplicate_snapshots
)


# ============================================================
# 3. DATE VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("3. SNAPSHOT DATE VALIDATION")
print("=" * 70)

df["snapshot_date"] = pd.to_datetime(
    df["snapshot_date"],
    errors="coerce"
)

invalid_snapshot_dates = (
    df["snapshot_date"].isna().sum()
)

print(
    "Invalid snapshot dates:",
    invalid_snapshot_dates
)

# Snapshot order
out_of_order = 0

for issue_id, group in df.groupby("issue_id"):

    dates = group["snapshot_date"]

    if not dates.is_monotonic_increasing:
        out_of_order += 1

print(
    "Issues with snapshots out of order:",
    out_of_order
)


# ============================================================
# 4. SNAPSHOT NUMBER VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("4. SNAPSHOT NUMBER VALIDATION")
print("=" * 70)

bad_snapshot_numbers = 0

for issue_id, group in df.groupby("issue_id"):

    numbers = (
        group["snapshot_number"]
        .sort_values()
        .tolist()
    )

    expected = list(
        range(1, len(numbers) + 1)
    )

    if numbers != expected:
        bad_snapshot_numbers += 1

print(
    "Issues with invalid snapshot numbering:",
    bad_snapshot_numbers
)


# ============================================================
# 5. TARGET CHECK
# ============================================================

print("\n" + "=" * 70)
print("5. TARGET VALIDATION")
print("=" * 70)

valid_targets = {
    "Low",
    "Medium",
    "High",
    "Critical"
}

actual_targets = set(
    df["task_risk_level"]
    .dropna()
    .unique()
)

print(
    "Target classes:",
    sorted(actual_targets)
)

unexpected_targets = (
    actual_targets - valid_targets
)

print(
    "Unexpected target values:",
    unexpected_targets
)

print("\nTarget distribution:")

target_counts = (
    df["task_risk_level"]
    .value_counts()
)

print(target_counts)

print("\nTarget percentages:")

print(
    (
        target_counts /
        len(df) *
        100
    ).round(2)
)


# ============================================================
# 6. TARGET CONSISTENCY PER ISSUE
#
# Every snapshot of an issue currently receives the same
# eventual outcome.
# This is expected for our current target construction.
# ============================================================

print("\n" + "=" * 70)
print("6. TARGET CONSISTENCY PER ISSUE")
print("=" * 70)

target_counts_per_issue = (
    df.groupby("issue_id")["task_risk_level"]
    .nunique()
)

inconsistent_target_issues = (
    target_counts_per_issue > 1
).sum()

print(
    "Issues with multiple target labels:",
    inconsistent_target_issues
)

if inconsistent_target_issues == 0:
    print(
        "✓ Every snapshot of an issue has the same target."
    )
else:
    print(
        "WARNING: Some issues have multiple target labels."
    )


# ============================================================
# 7. ACTUAL DURATION CHECK
# ============================================================

print("\n" + "=" * 70)
print("7. ACTUAL DURATION CHECK")
print("=" * 70)

duration = pd.to_numeric(
    df["actual_duration_days"],
    errors="coerce"
)

print(
    duration.describe()
)

negative_duration = (
    duration < 0
).sum()

zero_duration = (
    duration == 0
).sum()

print(
    "\nNegative durations:",
    negative_duration
)

print(
    "Zero durations    :",
    zero_duration
)


# ============================================================
# 8. LEAKAGE CHECK
# ============================================================

print("\n" + "=" * 70)
print("8. LEAKAGE CHECK")
print("=" * 70)

# These columns should NEVER be model features.

FORBIDDEN_FEATURES = [
    "actual_duration_days",
    "task_risk_level",
    "issue_id",
    "issue_key",
    "project_id",
    "snapshot_date",
    "snapshot_number"
]

print(
    "Columns that must NOT be supplied to the model:"
)

for col in FORBIDDEN_FEATURES:
    if col in df.columns:
        print(" !", col)


# Check suspicious direct outcome information.

print("\nPotentially dangerous columns:")

dangerous_patterns = [
    "resolution",
    "delay",
    "actual_duration",
    "overrun"
]

for col in df.columns:

    lower = col.lower()

    if any(
        pattern in lower
        for pattern in dangerous_patterns
    ):

        print(
            " !",
            col
        )


# ============================================================
# 9. MISSING VALUE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("9. MISSING VALUE ANALYSIS")
print("=" * 70)

missing = (
    df.isna()
    .sum()
    .sort_values(
        ascending=False
    )
)

missing_pct = (
    missing / len(df) * 100
).round(2)

missing_table = pd.DataFrame({
    "missing": missing,
    "percentage": missing_pct
})

print(
    missing_table
)


# ============================================================
# 10. CATEGORICAL DISTRIBUTIONS
# ============================================================

print("\n" + "=" * 70)
print("10. CATEGORICAL FEATURE DISTRIBUTIONS")
print("=" * 70)

categorical = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

for col in categorical:

    if col not in df.columns:
        continue

    print(
        f"\n--- {col} ---"
    )

    print(
        df[col]
        .value_counts()
        .head(15)
    )


# ============================================================
# 11. NUMERIC FEATURE CHECK
# ============================================================

print("\n" + "=" * 70)
print("11. NUMERIC FEATURE CHECK")
print("=" * 70)

numeric = [
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

for col in numeric:

    if col not in df.columns:
        continue

    values = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    print(
        f"\n{col}"
    )

    print(
        "  min    :",
        values.min()
    )

    print(
        "  median :",
        values.median()
    )

    print(
        "  max    :",
        values.max()
    )

    print(
        "  missing:",
        values.isna().sum()
    )


# ============================================================
# 12. CRITICAL LEAKAGE TEST
#
# For every feature that represents a historical state,
# inspect whether it changes across snapshots.
# ============================================================

print("\n" + "=" * 70)
print("12. HISTORICAL FEATURE VARIATION")
print("=" * 70)

historical_features = [
    "status",
    "priority",
    "story_points",
    "timespent",
    "assignee",
    "sprint",
    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days"
]

for col in historical_features:

    if col not in df.columns:
        continue

    unique_per_issue = (
        df.groupby("issue_id")[col]
        .nunique()
    )

    changed = (
        unique_per_issue > 1
    ).sum()

    print(
        f"{col:35s}: "
        f"{changed:,} issues changed"
    )


# ============================================================
# 13. TARGET VS SNAPSHOT NUMBER
#
# If every snapshot number has almost exactly the same target
# distribution, that's normal.
# But if snapshot number almost perfectly predicts the target,
# we need to investigate.
# ============================================================

print("\n" + "=" * 70)
print("13. TARGET DISTRIBUTION BY SNAPSHOT")
print("=" * 70)

snapshot_target = pd.crosstab(
    df["snapshot_number"],
    df["task_risk_level"],
    normalize="index"
) * 100

print(
    snapshot_target.round(2)
)


# ============================================================
# FINAL VERDICT
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)

problems = []

if duplicate_snapshots > 0:
    problems.append(
        f"{duplicate_snapshots} duplicate snapshots"
    )

if invalid_snapshot_dates > 0:
    problems.append(
        f"{invalid_snapshot_dates} invalid snapshot dates"
    )

if out_of_order > 0:
    problems.append(
        f"{out_of_order} issues with unordered snapshots"
    )

if bad_snapshot_numbers > 0:
    problems.append(
        f"{bad_snapshot_numbers} issues with bad snapshot numbering"
    )

if unexpected_targets:
    problems.append(
        f"Unexpected targets: {unexpected_targets}"
    )

if negative_duration > 0:
    problems.append(
        f"{negative_duration} negative durations"
    )


if problems:

    print("\nWARNING: Problems found:")

    for problem in problems:
        print(" !", problem)

else:

    print(
        "\n✓ No basic structural problems detected."
    )

print("\n" + "=" * 70)
print("IMPORTANT")
print("=" * 70)

print(
    """
The dataset can now be structurally validated,
but a clean structural result does NOT prove that
the target is useful or that the dataset is
completely free from predictive leakage.

The next analysis should specifically test:

1. Whether historical features contain future information.
2. Whether target is strongly correlated with issue age.
3. Whether project-level splitting is appropriate.
4. Whether the model can predict risk before the outcome.
"""
)

print("=" * 70)