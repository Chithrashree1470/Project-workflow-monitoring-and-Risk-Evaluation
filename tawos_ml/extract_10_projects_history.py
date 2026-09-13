import mysql.connector
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# PROJECT_IDS = [
#     34, 33, 18, 22, 28,
#     44, 21, 12, 14, 24,
#     20, 36, 19, 43, 4,
#     42, 3, 8, 13, 17,
#     16, 1, 32, 11, 25,
#     31, 30, 27, 26, 7
# ]

PROJECT_IDS = [
    34, 33, 18, 22, 28,
    44, 21, 12, 14, 24
]

MAX_ISSUES_PER_PROJECT = 2000

if len(PROJECT_IDS) != 10:
    raise ValueError("Exactly 10 Project_ID values are required.")

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="MYSQL@2027job",
    database="tawos_test"
)

# These are controlled integer IDs, so inserting them directly is safe.
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
INNER JOIN (
    SELECT ID
    FROM (
        SELECT
            i.ID,
            ROW_NUMBER() OVER (
                PARTITION BY i.Project_ID
                ORDER BY i.ID
            ) AS rn
        FROM issue i
        WHERE i.Project_ID IN ({project_ids_sql})
    ) AS ranked
    WHERE rn <= {MAX_ISSUES_PER_PROJECT}
) AS selected_issues
    ON cl.Issue_ID = selected_issues.ID
ORDER BY cl.Issue_ID, cl.Creation_Date
"""

print("=" * 70)
print("EXTRACTING CHANGE HISTORY")
print("=" * 70)
print(f"Projects selected       : {len(PROJECT_IDS)}")
print(f"Max issues per project  : {MAX_ISSUES_PER_PROJECT}")
print(f"Maximum issues          : {len(PROJECT_IDS) * MAX_ISSUES_PER_PROJECT}")
print()
print("Querying change_log...")

df = pd.read_sql(query, conn)

output = DATA_DIR / "tawos_10projects_changelog.csv"
df.to_csv(output, index=False)

print("\n" + "=" * 70)
print("10-PROJECT CHANGE HISTORY COMPLETE")
print("=" * 70)

print(f"Change records : {len(df):,}")
print(f"Issues         : {df['Issue_ID'].nunique():,}")
print(f"Fields         : {df['Field'].nunique():,}")

print("\nImportant fields:")
print(df["Field"].value_counts().head(25))

print("\nOutput:")
print(output)

conn.close()