import mysql.connector
import pandas as pd
import csv
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
    cl.ID,
    cl.Issue_ID,
    cl.Field,
    cl.From_Value,
    cl.To_Value,
    cl.From_String,
    cl.To_String,
    cl.Change_Type,
    cl.Creation_Date,
    cl.Author_ID
FROM change_log cl
INNER JOIN issue i
    ON cl.Issue_ID = i.ID
WHERE i.Project_ID IN ({project_ids_sql})
ORDER BY
    cl.Issue_ID,
    cl.Creation_Date,
    cl.ID
"""


# ============================================================
# EXTRACTION
# ============================================================

print("=" * 70)
print("EXTRACTING ALL CHANGE HISTORY - 39 PROJECTS")
print("=" * 70)

print(f"Projects selected : {len(PROJECT_IDS)}")
print("Issue limit       : NONE")
print("Change-log limit  : NONE")
print()
print("Querying change_log...")

df = pd.read_sql(
    query,
    conn
)


# ============================================================
# REPORT
# ============================================================

print("\n" + "=" * 70)
print("CHANGE HISTORY EXTRACTION COMPLETE")
print("=" * 70)

print(
    f"Change records : {len(df):,}"
)

print(
    f"Issues         : {df['Issue_ID'].nunique():,}"
)

print(
    f"Fields         : {df['Field'].nunique():,}"
)

print("\nTop changed fields:")
print(
    df["Field"]
    .value_counts()
    .head(25)
)


# ============================================================
# SAVE
# ============================================================

output = (
    DATA_DIR /
    "tawos_39projects_full_changelog.csv"
)

df.to_csv(
    output,
    index=False,
    quoting=csv.QUOTE_ALL,
    escapechar="\\"
)

print("\nOutput:")
print(output)

conn.close()