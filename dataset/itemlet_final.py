import pandas as pd
from pathlib import Path

# ============================================================
# ITEMLET DATA PREPARATION
# ============================================================
# Purpose:
# 1. Load Itemlet dataset
# 2. Keep only relevant columns
# 3. Remove obvious leakage/risk-formula columns
# 4. Preserve project IDs and temporal information
# 5. Save a clean dataset for the next stages
#
# NOTE:
# We are NOT creating the risk/outcome label yet.
# That will be Step 6 after inspecting the available outcomes.
# ============================================================


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ITEMLET_FILE = BASE_DIR / "itemlet_dataset.csv"
DICTIONARY_FILE = BASE_DIR / "data_dictionary.csv"

OUTPUT_FILE = BASE_DIR / "itemlet_relevant.csv"


# ============================================================
# RELEVANT COLUMNS
# ============================================================

RELEVANT_COLUMNS = [

    # --------------------------------------------------------
    # PROJECT IDENTIFICATION
    # --------------------------------------------------------
    "project_id",
    "project_key",
    "project_name",

    # --------------------------------------------------------
    # ISSUE / TASK IDENTIFICATION
    # --------------------------------------------------------
    "issue_id",
    "issue_key",
    "issuetype_name",

    # --------------------------------------------------------
    # TASK STATE
    # --------------------------------------------------------
    "priority_name",
    "status_name",
    "status_statusCategory_name",

    # --------------------------------------------------------
    # TEMPORAL INFORMATION
    # IMPORTANT FOR DYNAMIC SNAPSHOTS
    # --------------------------------------------------------
    "created",
    "updated",
    "statuscategorychangedate",
    "resolutiondate",

    # --------------------------------------------------------
    # ESTIMATION / EFFORT
    # --------------------------------------------------------
    "story_points",
    "worklog_total",
    "Total Time Logged (hours)",
    "workratio",

    # --------------------------------------------------------
    # WORKFLOW BEHAVIOUR
    # --------------------------------------------------------
    "Transition Count",
    "Reassignment Count",
    "Reopen Count",
    "Worklog Count",
    "Updated By Count",
    "Assignee Count",

    # --------------------------------------------------------
    # DEPENDENCIES
    # --------------------------------------------------------
    "Issue Link Count",
    "Number of Inward Links",
    "Number of Outward Links",
    "Blocking Issues",
    "Blocked By Issues",

    # --------------------------------------------------------
    # SPRINT INFORMATION
    # --------------------------------------------------------
    "sprint_id",
    "sprint_name",
    "sprint_state",
    "Sprint Count",

    # --------------------------------------------------------
    # ASSIGNEE / WORKLOAD
    # --------------------------------------------------------
    "Assignee Account ID"
]


# ============================================================
# LOAD ITEMLET
# ============================================================

print("=" * 70)
print("ITEMLET DATA PREPARATION")
print("=" * 70)

print("\nLoading Itemlet dataset...")

df = pd.read_csv(
    ITEMLET_FILE,
    low_memory=False
)

print("Original rows   :", len(df))
print("Original columns:", len(df.columns))


# ============================================================
# CHECK REQUESTED COLUMNS
# ============================================================

print("\nChecking requested columns...")

missing_columns = [
    col for col in RELEVANT_COLUMNS
    if col not in df.columns
]

if missing_columns:

    print("\nERROR: The following columns were not found:")

    for col in missing_columns:
        print("  -", col)

    print("\nAvailable columns:")

    for col in df.columns:
        print("  -", col)

    raise ValueError(
        "\nSome requested columns do not exist in the Itemlet CSV."
    )


print("All requested columns found.")


# ============================================================
# SELECT RELEVANT DATA
# ============================================================

df = df[RELEVANT_COLUMNS].copy()

print("\nSelected columns:", len(df.columns))


# ============================================================
# CONVERT TEMPORAL COLUMNS
# ============================================================

DATE_COLUMNS = [
    "created",
    "updated",
    "statuscategorychangedate",
    "resolutiondate"
]

print("\nConverting date columns...")

for column in DATE_COLUMNS:

    df[column] = pd.to_datetime(
        df[column],
        errors="coerce",
        utc=True
    )


# ============================================================
# SORT BY PROJECT AND CREATION TIME
# ============================================================

print("Sorting records...")

df = df.sort_values(
    by=["project_id", "created"],
    na_position="last"
).reset_index(drop=True)


# ============================================================
# REMOVE DUPLICATE ISSUE RECORDS
# ============================================================
# We keep one record per issue.
#
# IMPORTANT:
# If Itemlet contains multiple historical records for the same
# issue, we will NOT blindly remove them. This check tells us
# whether that situation exists.
# ============================================================

duplicate_count = df["issue_id"].duplicated().sum()

print("\nDuplicate issue IDs:", duplicate_count)

if duplicate_count > 0:

    print(
        "WARNING: Multiple records exist for some issues."
    )

    print(
        "They are being retained for now because temporal/history "
        "information may be important for dynamic prediction."
    )


# ============================================================
# BASIC DATA QUALITY INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("DATASET SUMMARY")
print("=" * 70)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print(
    "Unique projects:",
    df["project_id"].nunique()
)

print(
    "Unique issues:",
    df["issue_id"].nunique()
)

print(
    "Date range:",
    df["created"].min(),
    "→",
    df["created"].max()
)


# ============================================================
# MISSING VALUE SUMMARY
# ============================================================

print("\nMissing values:")

missing_summary = (
    df.isna()
      .sum()
      .sort_values(ascending=False)
)

for column, count in missing_summary.items():

    if count > 0:
        percentage = (count / len(df)) * 100

        print(
            f"{column}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )


# ============================================================
# SAVE CLEAN DATASET
# ============================================================

print("\nSaving cleaned dataset...")

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 70)
print("COMPLETED")
print("=" * 70)

print("Output file:")
print(OUTPUT_FILE)

print("\nFinal shape:")
print(df.shape)

print("\nColumns retained:")

for column in df.columns:
    print("  ✓", column)

print("\nNext step:")
print(
    "Use this dataset to construct project-level temporal "
    "snapshots and investigate a defensible future outcome label."
)