import mysql.connector
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PROJECT_IDS = [
    34, 33, 18, 22, 28,
    44, 21, 12, 14, 24
]

if len(PROJECT_IDS) != 10:
    raise ValueError("Exactly 10 Project_ID values are required.")

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="MYSQL@2027job",
    database="tawos_test"
)

project_ids_sql = ",".join(str(int(x)) for x in PROJECT_IDS)

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

print("=" * 70)
print("EXTRACTING ALL TAWOS ISSUES")
print("=" * 70)
print(f"Projects selected : {len(PROJECT_IDS)}")
print("Issue limit       : NONE")
print()
print("Running query...")

df = pd.read_sql(query, conn)

output = DATA_DIR / "tawos_10projects_full_issues.csv"
df.to_csv(output, index=False)

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)

print("Projects :", df["Project_ID"].nunique())
print("Issues   :", len(df))

print("\nIssues per project:")
print(df.groupby("Project_ID").size())

print("\nOutput:")
print(output)

conn.close()