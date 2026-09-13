import pandas as pd
import numpy as np

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

PHASE1_PATH = (
    DATA_DIR /
    "tawos_phase1_history_dataset.csv"
)

CHANGELOG_PATH = (
    DATA_DIR /
    "tawos_10projects_changelog.csv"
)

OUTPUT_PATH = (
    DATA_DIR /
    "tawos_phase2_history_dataset.csv"
)


# ============================================================
# CONFIG
# ============================================================

RECENT_DAYS = 7


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("TAWOS PHASE 2 - HISTORICAL FEATURE ENGINEERING")
print("=" * 70)

print("\nLoading Phase 1 dataset...")

snapshots = pd.read_csv(
    PHASE1_PATH,
    low_memory=False
)

print(
    "Snapshots:",
    len(snapshots)
)

print(
    "Issues:",
    snapshots["issue_id"].nunique()
)

print(
    "Projects:",
    snapshots["project_id"].nunique()
)


print("\nLoading change history...")

changes = pd.read_csv(
    CHANGELOG_PATH,
    low_memory=False
)

print(
    "Change records:",
    len(changes)
)

print(
    "Issues with history:",
    changes["Issue_ID"].nunique()
)


# ============================================================
# DATE CONVERSION
# ============================================================

snapshots["snapshot_date"] = pd.to_datetime(
    snapshots["snapshot_date"],
    errors="coerce"
)

changes["Creation_Date"] = pd.to_datetime(
    changes["Creation_Date"],
    errors="coerce"
)


# ============================================================
# NORMALIZE CHANGELOG FIELDS
# ============================================================

def normalize_field(value):

    if pd.isna(value):
        return ""

    value = str(value).strip().lower()

    if value == "issuetype":
        return "issuetype"

    if value == "story points":
        return "story points"

    if value == "timeestimate":
        return "timeestimate"

    if value == "timeoriginalestimate":
        return "timeoriginalestimate"

    return value


changes["field_normalized"] = (
    changes["Field"]
    .apply(normalize_field)
)


# ============================================================
# KEEP RELEVANT EVENTS
# ============================================================

RELEVANT_FIELDS = {
    "status",
    "assignee",
    "priority",
    "sprint",
    "timespent",
    "story points",
    "issuetype",
    "timeestimate",
    "timeoriginalestimate"
}

changes = changes[
    changes["field_normalized"].isin(
        RELEVANT_FIELDS
    )
].copy()


print("\nRelevant change records:")

print(
    len(changes)
)

print("\nRelevant fields:")

print(
    changes[
        "field_normalized"
    ]
    .value_counts()
)


# ============================================================
# SORT
# ============================================================

changes = changes.sort_values(
    [
        "Issue_ID",
        "Creation_Date",
        "ID"
    ]
)


snapshots = snapshots.sort_values(
    [
        "issue_id",
        "snapshot_date"
    ]
)


# ============================================================
# FEATURE FUNCTION
# ============================================================

def build_history_features(
    issue_snapshots,
    issue_changes
):

    result = []

    issue_changes = (
        issue_changes
        .sort_values(
            ["Creation_Date", "ID"]
        )
    )

    # --------------------------------------------------------
    # Process every snapshot for this issue
    # --------------------------------------------------------

    for _, snapshot in issue_snapshots.iterrows():

        snapshot_date = (
            snapshot["snapshot_date"]
        )

        # ----------------------------------------------------
        # ONLY EVENTS AVAILABLE AT SNAPSHOT TIME
        # ----------------------------------------------------

        historical = issue_changes[
            issue_changes[
                "Creation_Date"
            ] <= snapshot_date
        ]

        # ----------------------------------------------------
        # Base values
        # ----------------------------------------------------

        features = {
            "issue_id":
                snapshot["issue_id"],

            "snapshot_date":
                snapshot_date
        }

        # ----------------------------------------------------
        # Total historical changes
        # ----------------------------------------------------

        features[
            "total_change_count"
        ] = len(historical)

        # ----------------------------------------------------
        # Distinct values
        # ----------------------------------------------------

        for field, output_name in [

            (
                "assignee",
                "distinct_assignee_count"
            ),

            (
                "status",
                "distinct_status_count"
            ),

            (
                "priority",
                "distinct_priority_count"
            ),

            (
                "sprint",
                "distinct_sprint_count"
            )
        ]:

            field_changes = historical[
                historical[
                    "field_normalized"
                ] == field
            ]

            values = pd.concat(
                [
                    field_changes[
                        "From_String"
                    ],
                    field_changes[
                        "To_String"
                    ]
                ]
            )

            values = (
                values
                .dropna()
                .astype(str)
                .str.strip()
            )

            values = values[
                values != ""
            ]

            features[
                output_name
            ] = values.nunique()

        # ----------------------------------------------------
        # Transition counts
        # ----------------------------------------------------

        status_events = historical[
            historical[
                "field_normalized"
            ] == "status"
        ]

        features[
            "status_transition_count"
        ] = len(status_events)

        assignee_events = historical[
            historical[
                "field_normalized"
            ] == "assignee"
        ]

        features[
            "reassignment_count"
        ] = len(assignee_events)

        # ----------------------------------------------------
        # Recent events
        # ----------------------------------------------------

        recent_start = (
            snapshot_date
            -
            pd.Timedelta(
                days=RECENT_DAYS
            )
        )

        recent = historical[
            historical[
                "Creation_Date"
            ] >= recent_start
        ]

        features[
            "recent_total_changes_7d"
        ] = len(recent)

        for field, output_name in [

            (
                "status",
                "recent_status_changes_7d"
            ),

            (
                "assignee",
                "recent_assignee_changes_7d"
            ),

            (
                "priority",
                "recent_priority_changes_7d"
            ),

            (
                "sprint",
                "recent_sprint_changes_7d"
            ),

            (
                "timespent",
                "recent_timespent_changes_7d"
            )
        ]:

            features[
                output_name
            ] = (
                recent[
                    "field_normalized"
                ]
                .eq(field)
                .sum()
            )

        # ----------------------------------------------------
        # Days since last change by field
        # ----------------------------------------------------

        for field, output_name in [

            (
                "status",
                "days_since_last_status_change"
            ),

            (
                "assignee",
                "days_since_last_assignee_change"
            ),

            (
                "priority",
                "days_since_last_priority_change"
            ),

            (
                "sprint",
                "days_since_last_sprint_change"
            )
        ]:

            field_history = historical[
                historical[
                    "field_normalized"
                ] == field
            ]

            if len(field_history) > 0:

                last_event = (
                    field_history[
                        "Creation_Date"
                    ].max()
                )

                features[
                    output_name
                ] = max(
                    0,
                    (
                        snapshot_date
                        -
                        last_event
                    ).total_seconds()
                    / 86400
                )

            else:

                features[
                    output_name
                ] = (
                    snapshot[
                        "task_age_days"
                    ]
                )

        result.append(features)

    return pd.DataFrame(result)


# ============================================================
# BUILD FEATURES
# ============================================================

print("\n" + "=" * 70)
print("BUILDING HISTORICAL FEATURES")
print("=" * 70)

all_features = []

change_groups = {
    issue_id: group
    for issue_id, group
    in changes.groupby("Issue_ID")
}

processed = 0

for issue_id, issue_snapshots in (
    snapshots.groupby("issue_id")
):

    issue_changes = (
        change_groups
        .get(
            issue_id,
            pd.DataFrame(
                columns=changes.columns
            )
        )
    )

    features = build_history_features(
        issue_snapshots,
        issue_changes
    )

    all_features.append(
        features
    )

    processed += 1

    if processed % 1000 == 0:

        print(
            f"Processed issues: "
            f"{processed:,}"
        )


history_features = pd.concat(
    all_features,
    ignore_index=True
)


# ============================================================
# MERGE
# ============================================================

print("\nMerging historical features...")

phase2 = snapshots.merge(
    history_features,
    on=[
        "issue_id",
        "snapshot_date"
    ],
    how="left"
)


# ============================================================
# REMOVE DUPLICATE COLUMNS IF ANY
# ============================================================

phase2 = phase2.loc[
    :,
    ~phase2.columns.duplicated()
]


# ============================================================
# SORT
# ============================================================

phase2 = phase2.sort_values(
    [
        "project_id",
        "issue_id",
        "snapshot_date"
    ]
).reset_index(
    drop=True
)


# ============================================================
# CHECK
# ============================================================

NEW_FEATURES = [

    "total_change_count",
    "distinct_assignee_count",
    "distinct_status_count",
    "distinct_priority_count",
    "distinct_sprint_count",

    "status_transition_count",
    "reassignment_count",

    "recent_total_changes_7d",
    "recent_status_changes_7d",
    "recent_assignee_changes_7d",
    "recent_priority_changes_7d",
    "recent_sprint_changes_7d",
    "recent_timespent_changes_7d",

    
    "days_since_last_status_change",
    "days_since_last_assignee_change",
    "days_since_last_priority_change",
    "days_since_last_sprint_change"
]


print("\n" + "=" * 70)
print("PHASE 2 DATASET")
print("=" * 70)

print(
    "Rows     :",
    len(phase2)
)

print(
    "Projects :",
    phase2["project_id"].nunique()
)

print(
    "Issues   :",
    phase2["issue_id"].nunique()
)

print(
    "Columns  :",
    len(phase2.columns)
)


print("\nNew historical features:")

for feature in NEW_FEATURES:

    if feature in phase2.columns:

        print(
            f" ✓ {feature}"
        )


# ============================================================
# NULL CHECK
# ============================================================

print("\nNew feature null counts:")

for feature in NEW_FEATURES:

    if feature in phase2.columns:

        nulls = (
            phase2[feature]
            .isna()
            .sum()
        )

        print(
            f"{feature:40s}: "
            f"{nulls:,}"
        )


# ============================================================
# BASIC STATISTICS
# ============================================================

print("\nHistorical feature statistics:")

print(
    phase2[
        NEW_FEATURES
    ]
    .describe()
    .round(3)
    .to_string()
)


# ============================================================
# TARGET
# ============================================================

print("\nTarget distribution:")

print(
    phase2[
        "task_risk_level"
    ].value_counts()
)


# ============================================================
# SAVE
# ============================================================

phase2.to_csv(
    OUTPUT_PATH,
    index=False
)


print("\n" + "=" * 70)
print("PHASE 2 DATASET SAVED")
print("=" * 70)

print(
    OUTPUT_PATH
)

print("=" * 70)