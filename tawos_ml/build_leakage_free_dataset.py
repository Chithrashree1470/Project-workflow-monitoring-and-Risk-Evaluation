import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

ISSUES_FILE = DATA_DIR / "tawos_30projects_issues.csv"
CHANGELOG_FILE = DATA_DIR / "tawos_30projects_changelog.csv"

OUTPUT_FILE = DATA_DIR / "tawos_phase1_history_30dataset.csv"

MAX_SNAPSHOTS_PER_ISSUE = 5


# ============================================================
# TARGET BOUNDARIES
# ============================================================

LOW_MAX = 7
MEDIUM_MAX = 30
HIGH_MAX = 90


# ============================================================
# HELPERS
# ============================================================

def clean_string(value):

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.lower() in [
        "",
        "null",
        "none",
        "nan"
    ]:
        return ""

    return value


def clean_number(value):

    if pd.isna(value):
        return np.nan

    value = str(value).strip()

    if value.lower() in [
        "",
        "null",
        "none",
        "nan"
    ]:
        return np.nan

    try:
        return float(value)

    except:
        return np.nan


def get_change_value(row):

    string_value = clean_string(
        row.get("From_String")
    )

    if string_value:
        return string_value

    return clean_string(
        row.get("From_Value")
    )


def classify_duration(days):

    if days <= LOW_MAX:
        return "Low"

    elif days <= MEDIUM_MAX:
        return "Medium"

    elif days <= HIGH_MAX:
        return "High"

    return "Critical"


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("BUILDING LEAKAGE-FREE TAWOS HISTORICAL DATASET")
print("=" * 70)

print("\nLoading issues...")

issues = pd.read_csv(
    ISSUES_FILE,
    low_memory=False
)

print("Issues:", len(issues))


print("\nLoading change history...")

changes = pd.read_csv(
    CHANGELOG_FILE,
    low_memory=False
)

print("Change records:", len(changes))


# ============================================================
# DATE CONVERSION
# ============================================================

issues["Creation_Date"] = pd.to_datetime(
    issues["Creation_Date"],
    errors="coerce"
)

issues["Resolution_Date"] = pd.to_datetime(
    issues["Resolution_Date"],
    errors="coerce"
)

changes["Creation_Date"] = pd.to_datetime(
    changes["Creation_Date"],
    errors="coerce"
)


# ============================================================
# ID CLEANING
# ============================================================

issues["ID"] = pd.to_numeric(
    issues["ID"],
    errors="coerce"
)

changes["Issue_ID"] = pd.to_numeric(
    changes["Issue_ID"],
    errors="coerce"
)

issues = issues.dropna(
    subset=[
        "ID",
        "Creation_Date"
    ]
).copy()

changes = changes.dropna(
    subset=[
        "Issue_ID",
        "Creation_Date"
    ]
).copy()

issues["ID"] = issues["ID"].astype(int)
changes["Issue_ID"] = changes["Issue_ID"].astype(int)


# ============================================================
# ONLY RESOLVED ISSUES
# ============================================================

issues = issues[
    issues["Resolution_Date"].notna()
].copy()

print(
    "\nResolved issues:",
    len(issues)
)

print(
    "Projects:",
    issues["Project_ID"].nunique()
)


# ============================================================
# NORMALIZE CHANGE FIELDS
# ============================================================

changes["field_normalized"] = (
    changes["Field"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)


# ============================================================
# RELEVANT HISTORICAL FIELDS
# ============================================================

RELEVANT_FIELDS = {
    "status",
    "priority",
    "assignee",
    "sprint",
    "story points",
    "timespent",
    "timeestimate",
    "timeoriginalestimate",
    "issuetype",
    "type"
}

changes = changes[
    changes["field_normalized"].isin(
        RELEVANT_FIELDS
    )
].copy()


# ============================================================
# ISSUE LOOKUP
# ============================================================

issue_lookup = (
    issues
    .set_index("ID")
    .to_dict("index")
)

valid_issue_ids = set(
    issues["ID"]
)

changes = changes[
    changes["Issue_ID"].isin(
        valid_issue_ids
    )
].copy()


# ============================================================
# IMPORTANT FIX #1
#
# REMOVE CHANGE EVENTS THAT OCCURRED BEFORE ISSUE CREATION.
#
# Such events cannot legitimately describe the issue's state.
# ============================================================

changes = changes.merge(
    issues[
        [
            "ID",
            "Creation_Date"
        ]
    ].rename(
        columns={
            "ID": "Issue_ID",
            "Creation_Date": "Issue_Creation_Date"
        }
    ),
    on="Issue_ID",
    how="inner"
)

before_creation = (
    changes["Creation_Date"]
    <
    changes["Issue_Creation_Date"]
).sum()

print(
    "\nChange events before issue creation:",
    before_creation
)

changes = changes[
    changes["Creation_Date"]
    >=
    changes["Issue_Creation_Date"]
].copy()

changes.drop(
    columns=[
        "Issue_Creation_Date"
    ],
    inplace=True
)


# ============================================================
# HISTORY LOOKUP
# ============================================================

history_lookup = {}

for issue_id, group in changes.groupby(
    "Issue_ID",
    sort=False
):

    issue = issue_lookup.get(
        issue_id
    )

    if issue is None:
        continue

    creation_date = issue[
        "Creation_Date"
    ]

    resolution_date = issue[
        "Resolution_Date"
    ]

    group = group[
        (group["Creation_Date"] >= creation_date)
        &
        (group["Creation_Date"] < resolution_date)
    ].copy()

    group = group.sort_values(
        [
            "Creation_Date",
            "ID"
        ]
    )

    if len(group) > 0:

        history_lookup[
            issue_id
        ] = group


print(
    "Relevant history records:",
    len(changes)
)


print("\nRelevant fields:")

print(
    changes["field_normalized"]
    .value_counts()
)


# ============================================================
# CREATE SNAPSHOTS
# ============================================================

print("\nCreating historical snapshots...")

snapshots = []

processed = 0
issues_with_snapshots = 0


for issue_id, issue in issue_lookup.items():

    history = history_lookup.get(
        issue_id
    )

    if history is None:
        continue

    creation_date = pd.Timestamp(
        issue["Creation_Date"]
    )

    resolution_date = pd.Timestamp(
        issue["Resolution_Date"]
    )

    if resolution_date <= creation_date:
        continue


    # ========================================================
    # IMPORTANT FIX #2
    #
    # TARGET IS CALCULATED ONCE PER ISSUE.
    #
    # Therefore every snapshot of this issue receives exactly
    # the same target.
    # ========================================================

    actual_duration_days = (
        resolution_date - creation_date
    ).total_seconds() / 86400

    task_risk_level = classify_duration(
        actual_duration_days
    )


    # ========================================================
    # START FROM FINAL STATE
    # ========================================================

    state = {

        "issue_type":
            clean_string(
                issue.get("Type")
            ),

        "priority":
            clean_string(
                issue.get("Priority")
            ),

        "status":
            clean_string(
                issue.get("Status")
            ),

        "story_points":
            clean_number(
                issue.get("Story_Point")
            ),

        "timespent":
            clean_number(
                issue.get("Timespent")
            ),

        "assignee":
            clean_string(
                issue.get("Assignee_ID")
            ),

        "sprint":
            clean_string(
                issue.get("Sprint_ID")
            )
    }


    # ========================================================
    # REVERSE CHANGE COUNTERS
    # ========================================================

    change_counts = {

        "status": 0,
        "priority": 0,
        "assignee": 0,
        "story points": 0,
        "timespent": 0,
        "sprint": 0
    }

    for field in change_counts:

        change_counts[field] = int(
            (
                history["field_normalized"]
                == field
            ).sum()
        )


    # ========================================================
    # RECONSTRUCT HISTORY BACKWARDS
    # ========================================================

    issue_snapshots = []

    reverse_history = list(
        history.iloc[::-1].itertuples(
            index=False
        )
    )


    for row in reverse_history:

        change_date = row.Creation_Date
        field = row.field_normalized

        if pd.isna(change_date):
            continue

        # Safety check
        if change_date < creation_date:
            continue

        if change_date >= resolution_date:
            continue


        row_dict = row._asdict()

        # ====================================================
        # RESTORE STATE BEFORE THIS CHANGE
        # ====================================================

        if field == "status":

            state["status"] = get_change_value(
                row_dict
            )

        elif field == "priority":

            state["priority"] = get_change_value(
                row_dict
            )

        elif field == "assignee":

            state["assignee"] = get_change_value(
                row_dict
            )

        elif field == "sprint":

            state["sprint"] = get_change_value(
                row_dict
            )

        elif field == "story points":

            state["story_points"] = clean_number(
                get_change_value(
                    row_dict
                )
            )

        elif field == "timespent":

            state["timespent"] = clean_number(
                get_change_value(
                    row_dict
                )
            )

        elif field in [
            "issuetype",
            "type"
        ]:

            state["issue_type"] = get_change_value(
                row_dict
            )


        # ====================================================
        # DECREMENT HISTORICAL COUNTERS
        # ====================================================

        if field in change_counts:

            change_counts[field] = max(
                0,
                change_counts[field] - 1
            )


        # ====================================================
        # TASK AGE
        # ====================================================

        task_age_days = (
            change_date - creation_date
        ).total_seconds() / 86400


        # HARD SAFETY CHECK
        if task_age_days < 0:
            continue


        # ====================================================
        # RECENT CHANGE ACTIVITY
        # ====================================================

        recent_start = (
            change_date
            -
            pd.Timedelta(days=7)
        )

        changes_last_7_days = len(
            history[
                (history["Creation_Date"] >= recent_start)
                &
                (history["Creation_Date"] < change_date)
            ]
        )


        # ====================================================
        # SNAPSHOT
        # ====================================================

        snapshot = {

            "project_id":
                issue.get("Project_ID"),

            "issue_id":
                issue_id,

            "issue_key":
                issue.get("Issue_Key"),

            "snapshot_date":
                change_date,

            "issue_type":
                state["issue_type"]
                or "Unknown",

            "priority":
                state["priority"]
                or "Unknown",

            "status":
                state["status"]
                or "Unknown",

            "story_points":
                (
                    state["story_points"]
                    if pd.notna(
                        state["story_points"]
                    )
                    else 0
                ),

            "story_points_missing":
                int(
                    pd.isna(
                        state["story_points"]
                    )
                    or
                    state["story_points"] == 0
                ),

            "timespent":
                (
                    state["timespent"]
                    if pd.notna(
                        state["timespent"]
                    )
                    else 0
                ),

            "assignee":
                state["assignee"]
                or "Unknown",

            "sprint":
                state["sprint"]
                or "Unknown",

            "task_age_days":
                task_age_days,

            "status_change_count":
                change_counts["status"],

            "priority_change_count":
                change_counts["priority"],

            "assignee_change_count":
                change_counts["assignee"],

            "story_point_change_count":
                change_counts["story points"],

            "estimate_change_count":
                (
                    (
                        history["field_normalized"]
                        == "timeoriginalestimate"
                    )
                    &
                    (
                        history["Creation_Date"]
                        < change_date
                    )
                ).sum(),

            "changes_last_7_days":
                changes_last_7_days,

            # TARGET CONSTRUCTION ONLY
            "actual_duration_days":
                actual_duration_days,

            "task_risk_level":
                task_risk_level
        }

        issue_snapshots.append(
            snapshot
        )


    # ========================================================
    # SELECT MAX 5 SNAPSHOTS
    # ========================================================

    if issue_snapshots:

        issue_snapshots = sorted(
            issue_snapshots,
            key=lambda x:
                x["snapshot_date"]
        )

        if len(issue_snapshots) > MAX_SNAPSHOTS_PER_ISSUE:

            indexes = np.linspace(
                0,
                len(issue_snapshots) - 1,
                MAX_SNAPSHOTS_PER_ISSUE
            ).astype(int)

            issue_snapshots = [
                issue_snapshots[i]
                for i in indexes
            ]

        snapshots.extend(
            issue_snapshots
        )

        issues_with_snapshots += 1


    processed += 1

    if processed % 1000 == 0:

        print(
            f"Processed issues: "
            f"{processed:,}"
        )


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(
    snapshots
)


if df.empty:

    raise RuntimeError(
        "No snapshots were created."
    )


# ============================================================
# REMOVE DUPLICATES
# ============================================================

df = df.drop_duplicates(
    subset=[
        "issue_id",
        "snapshot_date"
    ]
)


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "issue_id",
        "snapshot_date"
    ]
)


# ============================================================
# SNAPSHOT NUMBER
# ============================================================

df["snapshot_number"] = (
    df.groupby("issue_id")
    .cumcount()
    + 1
)


# ============================================================
# FINAL SAFETY CHECK
# ============================================================

negative_age_count = (
    df["task_age_days"] < 0
).sum()

if negative_age_count > 0:

    raise RuntimeError(
        f"Found {negative_age_count} "
        "snapshots with negative task age."
    )


target_consistency = (
    df.groupby("issue_id")["task_risk_level"]
    .nunique()
)

inconsistent_targets = (
    target_consistency > 1
).sum()

if inconsistent_targets > 0:

    raise RuntimeError(
        f"Found {inconsistent_targets} "
        "issues with multiple target labels."
    )


# ============================================================
# FINAL COLUMNS
# ============================================================

FINAL_COLUMNS = [

    "project_id",
    "issue_id",
    "issue_key",

    "snapshot_date",
    "snapshot_number",

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

    "changes_last_7_days",

    "actual_duration_days",
    "task_risk_level"
]

df = df[
    FINAL_COLUMNS
]


# ============================================================
# REPORT
# ============================================================

print("\n" + "=" * 70)
print("SNAPSHOT CREATION COMPLETE")
print("=" * 70)

print(
    "Issues processed      :",
    processed
)

print(
    "Issues with snapshots :",
    issues_with_snapshots
)

print(
    "Snapshots created     :",
    len(df)
)


print("\n" + "=" * 70)
print("FINAL DATASET")
print("=" * 70)

print(
    "Projects :",
    df["project_id"].nunique()
)

print(
    "Issues   :",
    df["issue_id"].nunique()
)

print(
    "Snapshots:",
    len(df)
)

print(
    "Columns  :",
    len(df.columns)
)


print("\nRisk distribution:")

print(
    df["task_risk_level"]
    .value_counts()
)


print("\nRisk percentages:")

print(
    (
        df["task_risk_level"]
        .value_counts(normalize=True)
        * 100
    ).round(2)
)


print("\nUnknown values:")

for col in [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]:

    unknown = (
        df[col] == "Unknown"
    ).sum()

    percentage = (
        unknown / len(df) * 100
    )

    print(
        f"{col:15s}: "
        f"{unknown:,} "
        f"({percentage:.2f}%)"
    )


print("\nTask age:")

print(
    df["task_age_days"].describe()
)


print("\nTarget consistency:")

print(
    "Issues with multiple targets:",
    inconsistent_targets
)


print("\nSnapshots per issue:")

print(
    df.groupby("issue_id")
    .size()
    .describe()
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n" + "=" * 70)
print("DATASET SAVED")
print("=" * 70)

print(OUTPUT_FILE)

print("=" * 70)