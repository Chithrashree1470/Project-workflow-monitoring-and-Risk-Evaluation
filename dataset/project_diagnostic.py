import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "itemlet_relevant.csv"
OUTPUT_FILE = BASE_DIR / "itemlet_project_diagnostic.csv"

# ------------------------------------------------------------
# Load
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Convert dates
for col in ["created", "updated", "resolutiondate"]:
    df[col] = pd.to_datetime(
        df[col],
        errors="coerce",
        utc=True
    )

# ------------------------------------------------------------
# Numeric columns
# ------------------------------------------------------------

numeric_cols = [
    "story_points",
    "worklog_total",
    "Total Time Logged (hours)",
    "workratio",
    "Transition Count",
    "Reassignment Count",
    "Reopen Count",
    "Worklog Count",
    "Updated By Count",
    "Assignee Count",
    "Issue Link Count",
    "Number of Inward Links",
    "Number of Outward Links",
    "Blocking Issues",
    "Blocked By Issues"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ------------------------------------------------------------
# Define completed issues
# ------------------------------------------------------------

completed_statuses = [
    "Done",
    "Closed",
    "Resolved"
]

df["is_completed"] = (
    df["status_name"]
    .astype(str)
    .str.strip()
    .isin(completed_statuses)
)


# ------------------------------------------------------------
# Calculate task duration
# ------------------------------------------------------------

df["task_duration_days"] = (
    df["resolutiondate"] - df["created"]
).dt.total_seconds() / 86400


# ------------------------------------------------------------
# Project aggregation
# ------------------------------------------------------------

project = df.groupby(
    ["project_id", "project_key", "project_name"],
    dropna=False
).agg(

    Total_Issues=("issue_id", "count"),

    Unique_Issues=("issue_id", "nunique"),

    Issues_With_Created=(
        "created",
        lambda x: x.notna().sum()
    ),

    Issues_With_Resolution=(
        "resolutiondate",
        lambda x: x.notna().sum()
    ),

    Completed_Issues=(
        "is_completed",
        "sum"
    ),

    Total_Story_Points=(
        "story_points",
        "sum"
    ),

    Average_Story_Points=(
        "story_points",
        "mean"
    ),

    Total_Worklog_Hours=(
        "Total Time Logged (hours)",
        "sum"
    ),

    Average_Task_Duration_Days=(
        "task_duration_days",
        "mean"
    ),

    Median_Task_Duration_Days=(
        "task_duration_days",
        "median"
    ),

    Average_Transitions=(
        "Transition Count",
        "mean"
    ),

    Average_Reassignments=(
        "Reassignment Count",
        "mean"
    ),

    Average_Reopens=(
        "Reopen Count",
        "mean"
    ),

    Total_Reopens=(
        "Reopen Count",
        "sum"
    ),

    Total_Worklogs=(
        "Worklog Count",
        "sum"
    ),

    Total_Dependencies=(
        "Issue Link Count",
        "sum"
    ),

    Total_Blocking_Issues=(
        "Blocking Issues",
        "sum"
    ),

    Total_Blocked_By=(
        "Blocked By Issues",
        "sum"
    ),

    Earliest_Created=(
        "created",
        "min"
    ),

    Latest_Created=(
        "created",
        "max"
    ),

    Earliest_Resolution=(
        "resolutiondate",
        "min"
    ),

    Latest_Resolution=(
        "resolutiondate",
        "max"
    )
).reset_index()


# ------------------------------------------------------------
# Derived project metrics
# ------------------------------------------------------------

project["Completion_Percentage"] = (
    project["Completed_Issues"] /
    project["Total_Issues"].replace(0, pd.NA)
) * 100


project["Resolution_Coverage_Percentage"] = (
    project["Issues_With_Resolution"] /
    project["Total_Issues"].replace(0, pd.NA)
) * 100


project["Project_Duration_Days"] = (
    project["Latest_Resolution"] -
    project["Earliest_Created"]
).dt.total_seconds() / 86400


# ------------------------------------------------------------
# Data quality flag
# ------------------------------------------------------------

project["Usable_Temporal_Data"] = (
    (project["Issues_With_Created"] >= 10) &
    (project["Issues_With_Resolution"] >= 5) &
    (project["Project_Duration_Days"] > 0)
)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

project.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# Print results
# ------------------------------------------------------------

print("=" * 70)
print("ITEMLET PROJECT DIAGNOSTIC")
print("=" * 70)

print("Projects:", len(project))
print("Total issues:", len(df))

print(
    "\nProjects with usable temporal data:",
    project["Usable_Temporal_Data"].sum()
)

print(
    "Projects without sufficient temporal data:",
    (~project["Usable_Temporal_Data"]).sum()
)

print("\nProject diagnostic saved to:")
print(OUTPUT_FILE)

print("\nProject summary:")
print(
    project[
        [
            "project_id",
            "project_name",
            "Total_Issues",
            "Issues_With_Created",
            "Issues_With_Resolution",
            "Completed_Issues",
            "Completion_Percentage",
            "Average_Task_Duration_Days",
            "Project_Duration_Days",
            "Usable_Temporal_Data"
        ]
    ].to_string(index=False)
)