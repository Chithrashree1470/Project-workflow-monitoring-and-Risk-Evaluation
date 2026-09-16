import mysql.connector
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# ALL 39 TAWOS PROJECTS
# ============================================================

PROJECT_IDS = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
    31, 32, 33, 34, 35, 36, 42, 43, 44
]

EXPECTED_PROJECT_COUNT = 39

if len(PROJECT_IDS) != EXPECTED_PROJECT_COUNT:
    raise ValueError(
        f"Expected {EXPECTED_PROJECT_COUNT} Project_ID values, "
        f"but found {len(PROJECT_IDS)}."
    )

if len(set(PROJECT_IDS)) != len(PROJECT_IDS):
    raise ValueError("Duplicate Project_ID values detected.")


# ============================================================
# DATABASE
# ============================================================

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="MYSQL@2027job",
    database="tawos_test"
)

project_ids_sql = ",".join(
    str(int(x))
    for x in PROJECT_IDS
)


# ============================================================
# QUERY
# ============================================================

query = f"""
SELECT
    ID,
    Issue_Key,
    Project_ID,
    Type,
    Priority,
    Status,
    Resolution,
    Creation_Date,
    Estimation_Date,
    Resolution_Date,
    Last_Updated,
    Story_Point,
    Timespent,
    In_Progress_Minutes,
    Total_Effort_Minutes,
    Resolution_Time_Minutes,
    Assignee_ID
FROM issue
WHERE Project_ID IN ({project_ids_sql})
ORDER BY Project_ID, ID
"""


# ============================================================
# EXTRACTION
# ============================================================

print("=" * 70)
print("EXTRACTING ALL TAWOS ISSUES - 39 PROJECTS")
print("=" * 70)

print(f"Projects selected : {len(PROJECT_IDS)}")
print("Issue limit       : NONE")
print()
print("Running query...")

df = pd.read_sql(query, conn)


# ============================================================
# VALIDATION
# ============================================================

found_projects = sorted(
    df["Project_ID"].dropna().unique()
)

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)

print("Projects found :", len(found_projects))
print("Issues         :", f"{len(df):,}")

print("\nProject IDs found:")
print(found_projects)

missing_projects = sorted(
    set(PROJECT_IDS)
    -
    set(found_projects)
)

if missing_projects:
    print("\nWARNING - Projects with no issues:")
    print(missing_projects)


print("\nIssues per project:")
print(
    df.groupby("Project_ID")
    .size()
)


# ============================================================
# SAVE
# ============================================================

output = (
    DATA_DIR /
    "tawos_39projects_full_issues.csv"
)

df.to_csv(
    output,
    index=False
)

print("\nOutput:")
print(output)

conn.close()