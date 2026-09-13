import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

df = pd.read_csv(
    BASE_DIR / "itemlet_relevant.csv",
    low_memory=False
)
# Number of records for each issue
counts = df.groupby("issue_id").size()

print("=" * 60)
print("ISSUE RECORD ANALYSIS")
print("=" * 60)

print("Total rows:", len(df))
print("Unique issues:", df["issue_id"].nunique())

print("\nRecords per issue:")
print(counts.describe())

print("\nDistribution:")
print(counts.value_counts().sort_index().head(20))

# Show one issue with many records
issue_id = counts.idxmax()

print("\nIssue with most records:", issue_id)
print("Number of records:", counts.max())

sample = df[df["issue_id"] == issue_id]

print("\nSample records:")
print(
    sample[
        [
            "issue_id",
            "project_id",
            "created",
            "updated",
            "status_name",
            "resolutiondate",
            "story_points",
            "worklog_total",
            "Transition Count",
            "Reassignment Count",
            "Reopen Count"
        ]
    ].to_string(index=False)
)