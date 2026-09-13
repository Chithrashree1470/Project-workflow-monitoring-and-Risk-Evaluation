import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "itemlet_relevant.csv"
OUTPUT_FILE = BASE_DIR / "dynamic_training_dataset.csv"

SNAPSHOT_DAYS = 7
FUTURE_WINDOW_DAYS = 30

# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("BUILDING OPTIMIZED DYNAMIC SNAPSHOT DATASET")
print("=" * 70)

print("\nLoading Itemlet...")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print("Rows loaded:", len(df))


# ============================================================
# DATE CONVERSION
# ============================================================

print("\nConverting dates...")

for col in [
    "created",
    "updated",
    "resolutiondate"
]:
    df[col] = pd.to_datetime(
        df[col],
        errors="coerce",
        utc=True
    )


# ============================================================
# NUMERIC CONVERSION
# ============================================================

numeric_cols = [
    "story_points",
    "Transition Count",
    "Reassignment Count",
    "Reopen Count",
    "Updated By Count",
    "Assignee Count"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)


# ============================================================
# BASIC CLEANING
# ============================================================

df = df[
    df["project_id"].notna() &
    df["issue_key"].notna()
].copy()

df = df.drop_duplicates()

print("Usable rows:", len(df))


# ============================================================
# TASK ID
# ============================================================
#
# IMPORTANT:
# issue_id is NOT globally unique in this dataset.
#
# Therefore task identity = project_id + issue_key
# ============================================================

df["task_id"] = (
    df["project_id"].astype(str)
    + "_"
    + df["issue_key"].astype(str)
)

print(
    "Unique task IDs:",
    df["task_id"].nunique()
)


# ============================================================
# CHECK REPEATED TASKS
# ============================================================

task_counts = df["task_id"].value_counts()

print("\nTask record distribution:")
print(task_counts.describe())

repeated_tasks = (
    task_counts > 1
).sum()

print(
    "Tasks with multiple records:",
    repeated_tasks
)


# ============================================================
# CONSOLIDATE TASK RECORDS
# ============================================================
#
# For the current MVP we need one final task record.
#
# If multiple records exist for the same project + issue_key,
# retain the most recently updated record.
#
# Historical task events are already represented through
# Itemlet's transition/reassignment/reopen counters.
# ============================================================

df = df.sort_values(
    ["task_id", "updated"],
    na_position="first"
)

df = (
    df.groupby(
        "task_id",
        as_index=False,
        sort=False
    )
    .tail(1)
    .copy()
)

print(
    "Task records after consolidation:",
    len(df)
)


# ============================================================
# TASK EXECUTION METRICS
# ============================================================

print("\nCalculating task execution metrics...")

df["is_completed"] = (
    df["resolutiondate"].notna()
)

df["cycle_time_hours"] = (
    df["resolutiondate"] -
    df["created"]
).dt.total_seconds() / 3600

df.loc[
    df["cycle_time_hours"] < 0,
    "cycle_time_hours"
] = np.nan


# ============================================================
# PROJECT DELAY THRESHOLD
# ============================================================
#
# A task is considered unusually slow when its cycle time
# exceeds the 75th percentile of completed tasks in its
# project.
# ============================================================

print("Calculating project delay thresholds...")

completed = df[
    df["is_completed"] &
    df["cycle_time_hours"].notna()
].copy()

project_thresholds = (
    completed
    .groupby("project_id")["cycle_time_hours"]
    .quantile(0.75)
    .rename("delay_threshold_hours")
)

df = df.join(
    project_thresholds,
    on="project_id"
)

df["is_delayed"] = (
    df["is_completed"] &
    df["delay_threshold_hours"].notna() &
    (
        df["cycle_time_hours"]
        >
        df["delay_threshold_hours"]
    )
)


# ============================================================
# TASK FEATURE FLAGS
# ============================================================

priority = (
    df["priority_name"]
    .fillna("Unknown")
    .astype(str)
    .str.lower()
)

df["critical_task"] = (
    priority.isin(
        ["critical", "highest"]
    )
).astype(int)

df["high_priority_task"] = (
    priority.isin(
        ["major", "high"]
    )
).astype(int)


issue_type = (
    df["issuetype_name"]
    .fillna("Unknown")
    .astype(str)
    .str.lower()
)

df["bug_task"] = (
    issue_type == "bug"
).astype(int)

df["story_task"] = (
    issue_type == "story"
).astype(int)


# ============================================================
# CREATE WEEKLY SNAPSHOTS
# ============================================================

print("\nCreating weekly snapshots...")

# Use created and updated to establish project activity period.
project_start = (
    df.groupby("project_id")["created"]
    .min()
)

project_end = (
    df.groupby("project_id")[
        ["created", "updated"]
    ]
    .max()
    .max(axis=1)
)

project_dates = pd.DataFrame({
    "project_start": project_start,
    "project_end": project_end
})

project_dates = project_dates.dropna()


snapshot_parts = []

for project_id, row in project_dates.iterrows():

    if row["project_end"] < row["project_start"]:
        continue

    dates = pd.date_range(
        start=row["project_start"],
        end=row["project_end"],
        freq=f"{SNAPSHOT_DAYS}D"
    )

    if len(dates) == 0:
        continue

    snapshot_parts.append(
        pd.DataFrame({
            "project_id": project_id,
            "snapshot_date": dates
        })
    )

snapshots = pd.concat(
    snapshot_parts,
    ignore_index=True
)

print(
    "Snapshots created:",
    len(snapshots)
)


# ============================================================
# CURRENT PROJECT STATE
# ============================================================
#
# Instead of calculating every project/snapshot separately,
# construct task intervals and use cumulative event counts.
# ============================================================

print("\nCalculating current project state...")


# ------------------------------------------------------------
# CREATED TASK EVENTS
# ------------------------------------------------------------

created_events = (
    df.groupby(
        ["project_id", "created"]
    )
    .size()
    .rename("created_count")
    .reset_index()
)

created_events["cumulative_tasks"] = (
    created_events
    .groupby("project_id")["created_count"]
    .cumsum()
)


# ------------------------------------------------------------
# COMPLETED TASK EVENTS
# ------------------------------------------------------------

completed_events = (
    df[
        df["resolutiondate"].notna()
    ]
    .groupby(
        ["project_id", "resolutiondate"]
    )
    .size()
    .rename("completed_count")
    .reset_index()
)

completed_events["cumulative_completed"] = (
    completed_events
    .groupby("project_id")["completed_count"]
    .cumsum()
)


# ------------------------------------------------------------
# DELAYED TASK EVENTS
# ------------------------------------------------------------

delayed_events = (
    df[
        df["is_delayed"]
    ]
    .groupby(
        ["project_id", "resolutiondate"]
    )
    .size()
    .rename("delayed_count")
    .reset_index()
)

delayed_events["cumulative_delayed"] = (
    delayed_events
    .groupby("project_id")["delayed_count"]
    .cumsum()
)


# ============================================================
# HELPER FUNCTION
# ============================================================

def cumulative_at_dates(
    snapshots,
    events,
    date_column,
    value_column,
    output_name
):
    """
    Calculate cumulative event count at each snapshot.

    Uses pandas merge_asof separately for each project
    through groupby processing to avoid global sorting issues.
    """

    result_parts = []

    event_projects = set(
        events["project_id"].unique()
    )

    for project_id, snap_group in snapshots.groupby(
        "project_id",
        sort=False
    ):

        snap_group = snap_group.sort_values(
            "snapshot_date"
        )

        if project_id not in event_projects:

            result = snap_group[
                ["project_id", "snapshot_date"]
            ].copy()

            result[output_name] = 0

            result_parts.append(result)

            continue

        event_group = events[
            events["project_id"] == project_id
        ].copy()

        event_group = event_group.sort_values(
            date_column
        )

        result = pd.merge_asof(
            snap_group,
            event_group[
                [
                    date_column,
                    value_column
                ]
            ],
            left_on="snapshot_date",
            right_on=date_column,
            direction="backward"
        )

        result[output_name] = (
            result[value_column]
            .fillna(0)
        )

        result_parts.append(
            result[
                [
                    "project_id",
                    "snapshot_date",
                    output_name
                ]
            ]
        )

    return pd.concat(
        result_parts,
        ignore_index=True
    )


# ============================================================
# CURRENT COUNTS
# ============================================================

current_tasks = cumulative_at_dates(
    snapshots,
    created_events,
    "created",
    "cumulative_tasks",
    "total_tasks"
)

current_completed = cumulative_at_dates(
    snapshots,
    completed_events,
    "resolutiondate",
    "cumulative_completed",
    "completed_tasks"
)

current_delayed = cumulative_at_dates(
    snapshots,
    delayed_events,
    "resolutiondate",
    "cumulative_delayed",
    "delayed_tasks"
)


# ============================================================
# COMBINE CURRENT STATE
# ============================================================

dynamic = current_tasks.merge(
    current_completed,
    on=["project_id", "snapshot_date"],
    how="left"
)

dynamic = dynamic.merge(
    current_delayed,
    on=["project_id", "snapshot_date"],
    how="left"
)

dynamic["completed_tasks"] = (
    dynamic["completed_tasks"]
    .fillna(0)
)

dynamic["delayed_tasks"] = (
    dynamic["delayed_tasks"]
    .fillna(0)
)

dynamic["pending_tasks"] = (
    dynamic["total_tasks"]
    -
    dynamic["completed_tasks"]
)

dynamic["completion_percentage"] = np.where(
    dynamic["total_tasks"] > 0,
    (
        dynamic["completed_tasks"] /
        dynamic["total_tasks"]
    ) * 100,
    0
)


# ============================================================
# FUTURE OUTCOME
# ============================================================
#
# For each snapshot T:
#
# Future window = T -> T + 30 days
#
# We count:
#
#   tasks resolved in that window
#   tasks delayed in that window
#
# Then:
#
# future_delayed_rate =
# delayed future tasks /
# all future resolved tasks
# ============================================================

print("\nCalculating future execution outcomes...")


# ------------------------------------------------------------
# Create future date
# ------------------------------------------------------------

dynamic["future_date"] = (
    dynamic["snapshot_date"]
    +
    pd.Timedelta(
        days=FUTURE_WINDOW_DAYS
    )
)


# ------------------------------------------------------------
# Future completed events
# ------------------------------------------------------------

future_completed = cumulative_at_dates(
    dynamic[
        [
            "project_id",
            "future_date"
        ]
    ].rename(
        columns={
            "future_date":
            "snapshot_date"
        }
    ),
    completed_events,
    "resolutiondate",
    "cumulative_completed",
    "future_cumulative_completed"
)

current_completed_2 = cumulative_at_dates(
    dynamic[
        [
            "project_id",
            "snapshot_date"
        ]
    ],
    completed_events,
    "resolutiondate",
    "cumulative_completed",
    "current_cumulative_completed"
)


future_delayed = cumulative_at_dates(
    dynamic[
        [
            "project_id",
            "future_date"
        ]
    ].rename(
        columns={
            "future_date":
            "snapshot_date"
        }
    ),
    delayed_events,
    "resolutiondate",
    "cumulative_delayed",
    "future_cumulative_delayed"
)

current_delayed_2 = cumulative_at_dates(
    dynamic[
        [
            "project_id",
            "snapshot_date"
        ]
    ],
    delayed_events,
    "resolutiondate",
    "cumulative_delayed",
    "current_cumulative_delayed"
)


# ============================================================
# ALIGN RESULTS
# ============================================================

dynamic = dynamic.reset_index(drop=True)

future_completed = (
    future_completed
    .reset_index(drop=True)
)

current_completed_2 = (
    current_completed_2
    .reset_index(drop=True)
)

future_delayed = (
    future_delayed
    .reset_index(drop=True)
)

current_delayed_2 = (
    current_delayed_2
    .reset_index(drop=True)
)


# Safety check
if not (
    len(dynamic)
    ==
    len(future_completed)
    ==
    len(current_completed_2)
    ==
    len(future_delayed)
    ==
    len(current_delayed_2)
):
    raise RuntimeError(
        "Snapshot alignment failed."
    )


dynamic[
    "future_completed_30d"
] = (
    future_completed[
        "future_cumulative_completed"
    ]
    -
    current_completed_2[
        "current_cumulative_completed"
    ]
)

dynamic[
    "future_delayed_30d"
] = (
    future_delayed[
        "future_cumulative_delayed"
    ]
    -
    current_delayed_2[
        "current_cumulative_delayed"
    ]
)


# ============================================================
# CLEAN FUTURE COUNTS
# ============================================================

dynamic[
    "future_completed_30d"
] = (
    dynamic[
        "future_completed_30d"
    ]
    .clip(lower=0)
)

dynamic[
    "future_delayed_30d"
] = (
    dynamic[
        "future_delayed_30d"
    ]
    .clip(lower=0)
)


# ============================================================
# FUTURE DELAY RATE
# ============================================================

dynamic[
    "future_delayed_rate"
] = np.where(

    dynamic[
        "future_completed_30d"
    ] > 0,

    dynamic[
        "future_delayed_30d"
    ]
    /
    dynamic[
        "future_completed_30d"
    ],

    np.nan
)


# ============================================================
# REMOVE SNAPSHOTS WITHOUT FUTURE OUTCOME
# ============================================================

dynamic = dynamic[
    dynamic[
        "future_completed_30d"
    ] > 0
].copy()


# ============================================================
# PROJECT AGE
# ============================================================

dynamic["project_start"] = (
    dynamic["project_id"]
    .map(project_start)
)

dynamic["project_age_days"] = (
    dynamic["snapshot_date"]
    -
    dynamic["project_start"]
).dt.total_seconds() / 86400


# ============================================================
# ADD CURRENT ACTIVITY FEATURES
# ============================================================
#
# These are calculated from all task records that existed
# by each snapshot.
#
# To keep this version fast, we calculate project-level
# historical totals using task creation dates.
# ============================================================

# ============================================================
# WORKFLOW FEATURES
# ============================================================

print("\nAdding workflow features...")


# We calculate these using the task records that existed
# before each snapshot.
#
# To avoid expensive merge_asof operations, we use the
# cumulative project-level values already available in the
# task data and map them through snapshot dates.


workflow_features = [
    "Transition Count",
    "Reassignment Count",
    "Reopen Count",
    "Updated By Count",
    "Assignee Count",
    "critical_task",
    "high_priority_task",
    "bug_task",
    "story_task"
]


# Remove rows without creation dates before building
# event tables.
workflow_df = df[
    df["created"].notna()
].copy()


for feature in workflow_features:

    print("Processing:", feature)

    # Aggregate feature values by project + creation date
    events = (
        workflow_df
        .groupby(
            [
                "project_id",
                "created"
            ],
            as_index=False
        )[feature]
        .sum()
    )

    # Sort explicitly
    events = events.sort_values(
        [
            "project_id",
            "created"
        ]
    )

    # Cumulative value inside each project
    events["cumulative_value"] = (
        events
        .groupby("project_id")[feature]
        .cumsum()
    )

    # Use the same helper, but now there are guaranteed
    # to be no null dates.
    feature_result = cumulative_at_dates(
        snapshots,
        events,
        "created",
        "cumulative_value",
        feature
    )

    dynamic = dynamic.merge(
        feature_result,
        on=[
            "project_id",
            "snapshot_date"
        ],
        how="left"
    )


# ============================================================
# RENAME WORKFLOW FEATURES
# ============================================================

dynamic = dynamic.rename(
    columns={
        "Transition Count":
            "transition_count",

        "Reassignment Count":
            "reassignment_count",

        "Reopen Count":
            "reopen_count",

        "Updated By Count":
            "updated_by_count",

        "Assignee Count":
            "assignee_count",

        "critical_task":
            "critical_task_count",

        "high_priority_task":
            "high_priority_task_count",

        "bug_task":
            "bug_count",

        "story_task":
            "story_count"
    }
)

# ============================================================
# RENAME FEATURES
# ============================================================

dynamic = dynamic.rename(
    columns={
        "Transition Count":
            "transition_count",

        "Reassignment Count":
            "reassignment_count",

        "Reopen Count":
            "reopen_count",

        "Updated By Count":
            "updated_by_count",

        "Assignee Count":
            "assignee_count",

        "critical_task":
            "critical_task_count",

        "high_priority_task":
            "high_priority_task_count",

        "bug_task":
            "bug_count",

        "story_task":
            "story_count"
    }
)


# ============================================================
# FINAL FEATURES
# ============================================================

final_columns = [

    "project_id",
    "snapshot_date",
    "project_age_days",

    "total_tasks",
    "completed_tasks",
    "pending_tasks",
    "completion_percentage",

    "transition_count",
    "reassignment_count",
    "reopen_count",
    "updated_by_count",
    "assignee_count",

    "critical_task_count",
    "high_priority_task_count",
    "bug_count",
    "story_count",

    "future_completed_30d",
    "future_delayed_30d",
    "future_delayed_rate"
]

# Keep only columns that actually exist
final_columns = [
    c for c in final_columns
    if c in dynamic.columns
]

dynamic = dynamic[
    final_columns
].copy()

# ============================================================
# CREATE 4-CLASS DYNAMIC RISK LABEL
# ============================================================

print("\nCreating 4-class dynamic risk labels...")

# Use future_delayed_rate as the underlying outcome measure.
#
# We use quartiles so that the four classes are determined
# from the actual distribution of project snapshots rather
# than arbitrary manually selected thresholds.

q25 = dynamic["future_delayed_rate"].quantile(0.25)
q50 = dynamic["future_delayed_rate"].quantile(0.50)
q75 = dynamic["future_delayed_rate"].quantile(0.75)

print("\nDynamic risk thresholds:")
print(f"Low / Medium      : {q25}")
print(f"Medium / High     : {q50}")
print(f"High / Critical   : {q75}")


def assign_dynamic_risk(rate):

    if rate <= q25:
        return "Low"

    elif rate <= q50:
        return "Medium"

    elif rate <= q75:
        return "High"

    else:
        return "Critical"


dynamic["dynamic_risk_level"] = (
    dynamic["future_delayed_rate"]
    .apply(assign_dynamic_risk)
)


# ============================================================
# DISPLAY DISTRIBUTION
# ============================================================

print("\nDynamic risk distribution:")

print(
    dynamic["dynamic_risk_level"]
    .value_counts()
    .sort_index()
)

# ============================================================
# CLEAN
# ============================================================

dynamic.replace(
    [np.inf, -np.inf],
    np.nan,
    inplace=True
)

dynamic = dynamic.dropna(
    subset=[
        "future_delayed_rate",
        "dynamic_risk_level"
    ]
)

dynamic = dynamic.sort_values(
    [
        "project_id",
        "snapshot_date"
    ]
).reset_index(drop=True)


# ============================================================
# SAVE
# ============================================================

dynamic.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC DATASET CREATED")
print("=" * 70)

print(
    "Projects :",
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

print("\nFuture delayed rate:")
print(
    dynamic[
        "future_delayed_rate"
    ].describe()
)

print("\nDynamic risk distribution:")
print(
    dynamic[
        "dynamic_risk_level"
    ].value_counts()
)

print("\nRisk boundaries:")
print("Low / Medium      :", q25)
print("Medium / High     :", q50)
print("High / Critical   :", q75)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nFirst 10 rows:")
print(
    dynamic.head(10).to_string(
        index=False
    )
)

print("\n" + "=" * 70)
print("READY FOR DYNAMIC MODEL TRAINING")
print("=" * 70)