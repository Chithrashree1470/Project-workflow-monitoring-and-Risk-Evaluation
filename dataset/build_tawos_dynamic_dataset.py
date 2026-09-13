import pandas as pd
import numpy as np

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TAWOS_PATH = BASE_DIR / "tawos_issue_ml.csv"

OUTPUT_PATH = (
    BASE_DIR
    / "dynamic_tawos_training_dataset.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_SNAPSHOTS_PER_TASK = 5


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("BUILDING REDESIGNED DYNAMIC TAWOS DATASET")
print("=" * 70)


# ============================================================
# LOAD DATASET
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
    sep=",",
    usecols=EXPECTED_COLUMNS,
    engine="python",
    on_bad_lines="skip"
)

print("Rows    :", len(df))
print("Columns :", len(df.columns))

print("\nDetected columns:")
print(df.columns.tolist())

if len(df.columns) != 14:
    raise ValueError(
        f"TAWOS CSV parsing failed. "
        f"Expected 14 columns, got {len(df.columns)}."
    )
# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED = [
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


missing = [
    c for c in REQUIRED
    if c not in df.columns
]


if missing:

    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# DATE CONVERSION
# ============================================================

print("\nConverting dates...")

DATE_COLUMNS = [
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date",
    "Last_Updated"
]


for column in DATE_COLUMNS:

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
        "Estimation_Date",
        "Resolution_Date"
    ]
).copy()


df = df.drop_duplicates(
    subset=["ID"]
).copy()


print(
    "\nTasks with valid dates:",
    len(df)
)

print(
    "Projects:",
    df["Project_ID"].nunique()
)


# ============================================================
# NUMERIC COLUMNS
# ============================================================

df["Story_Point"] = pd.to_numeric(
    df["Story_Point"],
    errors="coerce"
).fillna(0)


df["Timespent"] = pd.to_numeric(
    df["Timespent"],
    errors="coerce"
).fillna(0)


# ============================================================
# ACTUAL FINAL DELAY
# ============================================================
#
# This is the FUTURE OUTCOME.
#
# It is used ONLY to create the target.
# It is never used as a model feature.
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


df = df[
    df["delay_days"].notna()
].copy()


df = df[
    df["delay_days"] >= 0
].copy()


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

    return "Critical"


df["task_risk_level"] = (
    df["delay_days"]
    .apply(make_risk_label)
)


# ============================================================
# PROJECT CONTEXT
# ============================================================

print("\nCalculating project context...")


project_task_count = (
    df.groupby("Project_ID")
    .size()
    .rename("project_task_count")
)


df = df.merge(
    project_task_count,
    on="Project_ID",
    how="left"
)


# ============================================================
# CREATE SNAPSHOTS
# ============================================================
#
# IMPORTANT:
#
# We create at most 5 snapshots per task.
#
# Instead of taking the first 5 weeks, snapshots are distributed
# across the task's lifetime.
#
# Example:
#
# 100-day task
#
# Day 1
# Day 25
# Day 50
# Day 75
# Day 99
#
# This prevents long-running tasks from dominating the dataset.
# ============================================================

print("\nCreating prediction snapshots...")


snapshot_rows = []

total_tasks = len(df)


for counter, (_, task) in enumerate(
    df.iterrows(),
    start=1
):

    creation = task["Creation_Date"]

    resolution = task["Resolution_Date"]

    estimation = task["Estimation_Date"]


    # --------------------------------------------------------
    # Task lifetime
    # --------------------------------------------------------

    lifetime_days = (
        resolution - creation
    ).total_seconds() / 86400


    # Need a positive lifetime.
    if lifetime_days <= 0:

        continue


    # --------------------------------------------------------
    # Generate snapshot positions
    # --------------------------------------------------------
    #
    # Leave the final day out because that is too close to the
    # resolution event.
    #
    # For short tasks, this naturally produces fewer snapshots.
    # --------------------------------------------------------

    if lifetime_days <= 1:

        snapshot_offsets = [
            lifetime_days * 0.5
        ]

    else:

        snapshot_count = min(
            MAX_SNAPSHOTS_PER_TASK,
            max(
                1,
                int(np.ceil(lifetime_days / 7))
            )
        )

        snapshot_count = min(
            snapshot_count,
            MAX_SNAPSHOTS_PER_TASK
        )


        # Spread snapshots across 10% -> 90% of lifetime.
        snapshot_offsets = np.linspace(
            lifetime_days * 0.10,
            lifetime_days * 0.90,
            snapshot_count
        )


    # --------------------------------------------------------
    # Create snapshots
    # --------------------------------------------------------

    for snapshot_number, offset in enumerate(
        snapshot_offsets,
        start=1
    ):

        snapshot_date = (
            creation
            +
            pd.Timedelta(
                days=float(offset)
            )
        )


        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if snapshot_date >= resolution:

            continue


        # ----------------------------------------------------
        # Task age
        # ----------------------------------------------------

        task_age_days = (
            snapshot_date - creation
        ).total_seconds() / 86400


        # ----------------------------------------------------
        # Estimated duration
        # ----------------------------------------------------

        estimated_duration_days = (
            estimation - creation
        ).total_seconds() / 86400


        # ----------------------------------------------------
        # Days until estimate
        # ----------------------------------------------------

        days_until_estimation = (
            estimation - snapshot_date
        ).total_seconds() / 86400


        # ----------------------------------------------------
        # Age relative to estimate
        # ----------------------------------------------------

        if estimated_duration_days > 0:

            age_to_estimation_ratio = (
                task_age_days
                /
                estimated_duration_days
            )

        else:

            age_to_estimation_ratio = 0


        # ----------------------------------------------------
        # Timespent relative to estimate
        # ----------------------------------------------------

        if estimated_duration_days > 0:

            timespent_to_estimation_ratio = (
                task["Timespent"]
                /
                estimated_duration_days
            )

        else:

            timespent_to_estimation_ratio = 0


        # ----------------------------------------------------
        # Availability flags
        # ----------------------------------------------------

        has_assignee = int(
            pd.notna(task["Assignee_ID"])
        )


        has_sprint = int(
            pd.notna(task["Sprint_ID"])
        )


        # ----------------------------------------------------
        # Snapshot row
        # ----------------------------------------------------

        snapshot_rows.append({

            # Identifiers
            "project_id": task["Project_ID"],
            "issue_id": task["ID"],
            "issue_key": task["Issue_Key"],

            # Snapshot information
            "snapshot_date": snapshot_date,
            "snapshot_number": snapshot_number,

            # Current task state
            "issue_type": task["Type"],
            "priority": task["Priority"],
            "status": task["Status"],

            "story_points": task["Story_Point"],
            "timespent": task["Timespent"],

            "assignee_id": task["Assignee_ID"],
            "sprint_id": task["Sprint_ID"],

            # Temporal features
            "task_age_days": task_age_days,

            "days_until_estimation": (
                days_until_estimation
            ),

            "estimated_duration_days": (
                estimated_duration_days
            ),

            "age_to_estimation_ratio": (
                age_to_estimation_ratio
            ),

            "timespent_to_estimation_ratio": (
                timespent_to_estimation_ratio
            ),

            # Availability
            "has_assignee": has_assignee,
            "has_sprint": has_sprint,

            # Project context
            "project_task_count": (
                task["project_task_count"]
            ),

            # Future outcome / target
            "delay_days": task["delay_days"],

            "task_risk_level": (
                task["task_risk_level"]
            )
        })


    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    if counter % 10000 == 0:

        print(
            f"Processed tasks: "
            f"{counter}/{total_tasks}"
        )


# ============================================================
# CREATE SNAPSHOT DATAFRAME
# ============================================================

snapshots = pd.DataFrame(
    snapshot_rows
)


print(
    "\nSnapshots created:",
    len(snapshots)
)


# ============================================================
# CLEANING
# ============================================================

if snapshots.empty:

    raise ValueError(
        "No snapshots were created. "
        "Check Creation_Date and Resolution_Date."
    )


snapshots = snapshots.replace(
    [np.inf, -np.inf],
    np.nan
)


snapshots = snapshots.dropna(
    subset=[
        "snapshot_date",
        "task_risk_level"
    ]
).copy()


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("TASK RISK DISTRIBUTION")
print("=" * 70)


risk_counts = (
    snapshots["task_risk_level"]
    .value_counts()
)


print(
    risk_counts
)


print("\nRisk percentages:")


print(
    snapshots["task_risk_level"]
    .value_counts(
        normalize=True
    )
    .mul(100)
    .round(2)
)


# ============================================================
# DELAY STATISTICS
# ============================================================

print("\nDelay statistics by class:")


print(
    snapshots
    .groupby("task_risk_level")["delay_days"]
    .agg(
        [
            "count",
            "mean",
            "median",
            "min",
            "max"
        ]
    )
)


# ============================================================
# SNAPSHOT COUNTS PER TASK
# ============================================================

snapshot_counts = (
    snapshots
    .groupby("issue_id")
    .size()
)


print("\nSnapshots per task:")

print(
    snapshot_counts.describe()
)


print(
    "\nMaximum snapshots for one task:",
    snapshot_counts.max()
)


# ============================================================
# DATASET STATISTICS
# ============================================================

print("\n" + "=" * 70)
print("SNAPSHOT STATISTICS")
print("=" * 70)


print(
    "Projects :",
    snapshots["project_id"].nunique()
)


print(
    "Tasks    :",
    snapshots["issue_id"].nunique()
)


print(
    "Snapshots:",
    len(snapshots)
)


# ============================================================
# MODEL FEATURES
# ============================================================
#
# Only information available at prediction time.
# ============================================================

EXCLUDED_COLUMNS = [

    # Identifiers
    "project_id",
    "issue_id",
    "issue_key",

    # Snapshot reference
    "snapshot_date",

    # Future outcome
    "delay_days",

    # Target
    "task_risk_level"
]


FEATURES = [
    column
    for column in snapshots.columns
    if column not in EXCLUDED_COLUMNS
]


print("\n" + "=" * 70)
print("MODEL FEATURES")
print("=" * 70)


print(
    "Feature count:",
    len(FEATURES)
)


for feature in FEATURES:

    print(
        " ✓",
        feature
    )


# ============================================================
# SAVE
# ============================================================

snapshots.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("TAWOS DYNAMIC DATASET CREATED")
print("=" * 70)


print(
    "\nProjects :",
    snapshots["project_id"].nunique()
)


print(
    "Tasks    :",
    snapshots["issue_id"].nunique()
)


print(
    "Snapshots:",
    len(snapshots)
)


print(
    "Columns  :",
    len(snapshots.columns)
)


print(
    "Features :",
    len(FEATURES)
)


print("\nOutput:")
print(OUTPUT_PATH)


print("\n" + "=" * 70)
print("READY FOR TAWOS DYNAMIC MODEL")
print("=" * 70)