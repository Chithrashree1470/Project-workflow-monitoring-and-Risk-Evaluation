import mysql.connector
import pandas as pd
from pathlib import Path
import csv

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
ORDER BY cl.Issue_ID, cl.Creation_Date, cl.ID
"""

print("=" * 70)
print("EXTRACTING ALL CHANGE HISTORY")
print("=" * 70)
print(f"Projects selected : {len(PROJECT_IDS)}")
print("Issue limit       : NONE")
print("Change-log limit  : NONE")
print()
print("Querying change_log...")

df = pd.read_sql(query, conn)

output = DATA_DIR / "tawos_10projects_full_changelog.csv"
df.to_csv(
    output,
    index=False,
    quoting=csv.QUOTE_ALL,
    escapechar="\\"
)
print("\n" + "=" * 70)
print("FULL CHANGE HISTORY COMPLETE")
print("=" * 70)

print(f"Change records : {len(df):,}")
print(f"Issues         : {df['Issue_ID'].nunique():,}")
print(f"Fields         : {df['Field'].nunique():,}")

print("\nChange records per project:")

# Determine project for reporting
issue_projects = pd.read_sql(
    f"""
    SELECT ID, Project_ID
    FROM issue
    WHERE Project_ID IN ({project_ids_sql})
    """,
    conn
)

df_report = df.merge(
    issue_projects,
    left_on="Issue_ID",
    right_on="ID",
    how="left"
)

print(df_report.groupby("Project_ID").size())

print("\nTop changed fields:")
print(df["Field"].value_counts().head(25))

print("\nOutput:")
print(output)

conn.close()