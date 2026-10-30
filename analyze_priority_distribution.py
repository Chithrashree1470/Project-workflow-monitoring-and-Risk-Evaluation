# import pandas as pd
# from pathlib import Path

# # Dataset path
# BASE_DIR = Path(__file__).resolve().parent

# DATA_PATH = (
#     BASE_DIR
#     / "tawos_ml"
#     / "data"
#     / "tawos_phase1_10history_dataset.csv"
# )

# # Load dataset
# df = pd.read_csv(DATA_PATH, low_memory=False)

# print("=" * 70)
# print("TASK RISK DATASET - PRIORITY ANALYSIS")
# print("=" * 70)

# print("\nTotal records:", len(df))
# print("Unique tasks:", df["issue_id"].nunique())
# print("Unique projects:", df["project_id"].nunique())

# # Clean values
# df["priority"] = (
#     df["priority"]
#     .fillna("Unknown")
#     .astype(str)
#     .str.strip()
# )

# df["task_risk_level"] = (
#     df["task_risk_level"]
#     .fillna("Unknown")
#     .astype(str)
#     .str.strip()
# )

# # --------------------------------------------------
# # 1. PRIORITY DISTRIBUTION
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("1. PRIORITY DISTRIBUTION")
# print("=" * 70)

# priority_counts = df["priority"].value_counts()

# priority_distribution = pd.DataFrame({
#     "Count": priority_counts,
#     "Percentage": (
#         priority_counts / len(df) * 100
#     ).round(2)
# })

# print(priority_distribution.to_string())

# # --------------------------------------------------
# # 2. RISK LABEL DISTRIBUTION
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("2. OVERALL RISK LABEL DISTRIBUTION")
# print("=" * 70)

# risk_counts = df["task_risk_level"].value_counts()

# risk_distribution = pd.DataFrame({
#     "Count": risk_counts,
#     "Percentage": (
#         risk_counts / len(df) * 100
#     ).round(2)
# })

# print(risk_distribution.to_string())

# # --------------------------------------------------
# # 3. PRIORITY VS RISK LABEL
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("3. PRIORITY VS RISK LABEL COUNTS")
# print("=" * 70)

# cross_counts = pd.crosstab(
#     df["priority"],
#     df["task_risk_level"]
# )

# # Arrange columns consistently
# risk_order = ["Low", "Medium", "High", "Critical", "Unknown"]

# cross_counts = cross_counts.reindex(
#     columns=[
#         col for col in risk_order
#         if col in cross_counts.columns
#     ],
#     fill_value=0
# )

# print(cross_counts.to_string())

# # --------------------------------------------------
# # 4. RISK PERCENTAGE WITHIN EACH PRIORITY
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("4. RISK PERCENTAGE WITHIN EACH PRIORITY")
# print("=" * 70)

# cross_percentages = pd.crosstab(
#     df["priority"],
#     df["task_risk_level"],
#     normalize="index"
# ) * 100

# cross_percentages = cross_percentages.reindex(
#     columns=[
#         col for col in risk_order
#         if col in cross_percentages.columns
#     ],
#     fill_value=0
# )

# print(cross_percentages.round(2).to_string())

# # --------------------------------------------------
# # 5. UNIQUE TASK COUNTS PER PRIORITY
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("5. UNIQUE TASK COUNTS PER PRIORITY")
# print("=" * 70)

# unique_task_priority = (
#     df.groupby("priority")["issue_id"]
#     .nunique()
#     .sort_values(ascending=False)
# )

# print(unique_task_priority.to_string())

# # --------------------------------------------------
# # 6. UNIQUE TASKS VS HISTORICAL SNAPSHOTS
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("6. SNAPSHOT COUNTS PER PRIORITY")
# print("=" * 70)

# snapshot_counts = df.groupby("priority").size()

# snapshot_analysis = pd.DataFrame({
#     "Snapshots": snapshot_counts,
#     "Unique Tasks": unique_task_priority
# })

# snapshot_analysis["Avg Snapshots Per Task"] = (
#     snapshot_analysis["Snapshots"]
#     / snapshot_analysis["Unique Tasks"]
# ).round(2)

# print(snapshot_analysis.to_string())

# # --------------------------------------------------
# # 7. PRIORITY VS RISK USING UNIQUE TASKS
# # --------------------------------------------------

# print("\n" + "=" * 70)
# print("7. PRIORITY VS RISK - LATEST SNAPSHOT PER TASK")
# print("=" * 70)

# if "snapshot_date" in df.columns:
#     sort_columns = ["issue_id", "snapshot_date"]

#     if "snapshot_number" in df.columns:
#         sort_columns.append("snapshot_number")

#     latest_df = (
#         df.sort_values(sort_columns)
#         .groupby("issue_id", as_index=False)
#         .tail(1)
#     )

#     latest_counts = pd.crosstab(
#         latest_df["priority"],
#         latest_df["task_risk_level"]
#     )

#     latest_percentages = pd.crosstab(
#         latest_df["priority"],
#         latest_df["task_risk_level"],
#         normalize="index"
#     ) * 100

#     print("\nLatest snapshot counts:")
#     print(latest_counts.to_string())

#     print("\nLatest snapshot percentages:")
#     print(latest_percentages.round(2).to_string())

# else:
#     print("snapshot_date column not found.")

# # --------------------------------------------------
# # 8. SAVE REPORT
# # --------------------------------------------------

# OUTPUT_PATH = BASE_DIR / "priority_analysis_report.txt"

# with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
#     file.write("PRIORITY ANALYSIS REPORT\n\n")
#     file.write("PRIORITY DISTRIBUTION\n")
#     file.write(priority_distribution.to_string())
#     file.write("\n\nRISK DISTRIBUTION\n")
#     file.write(risk_distribution.to_string())
#     file.write("\n\nPRIORITY VS RISK COUNTS\n")
#     file.write(cross_counts.to_string())
#     file.write("\n\nPRIORITY VS RISK PERCENTAGES\n")
#     file.write(cross_percentages.round(2).to_string())
#     file.write("\n\nUNIQUE TASK COUNTS\n")
#     file.write(unique_task_priority.to_string())
#     file.write("\n\nSNAPSHOT ANALYSIS\n")
#     file.write(snapshot_analysis.to_string())

# print("\n" + "=" * 70)
# print("ANALYSIS COMPLETE")
# print("=" * 70)
# print("Report saved to:", OUTPUT_PATH)


import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "tawos_ml"
    / "data"
    / "tawos_phase1_10history_dataset.csv"
)

OUTPUT_PATH = BASE_DIR / "task_feature_analysis.txt"

FEATURES = [
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
    "changes_last_7_days"
]

CATEGORICAL = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

df = pd.read_csv(DATA_PATH, low_memory=False)

missing_columns = [
    col for col in FEATURES
    if col not in df.columns
]

if missing_columns:
    raise ValueError(f"Missing columns: {missing_columns}")

report = []

def write(message=""):
    print(message)
    report.append(str(message))


write("=" * 70)
write("TASK-LEVEL MODEL FEATURE ANALYSIS")
write("=" * 70)

write(f"\nTotal dataset rows: {len(df)}")
write(f"Unique tasks: {df['issue_id'].nunique()}")
write(f"Unique projects: {df['project_id'].nunique()}")

for feature in FEATURES:

    write("\n" + "=" * 70)
    write(f"FEATURE: {feature}")
    write("=" * 70)

    series = df[feature]

    write(f"Data type: {series.dtype}")
    write(f"Missing values: {series.isna().sum()}")
    write(f"Unique values: {series.nunique(dropna=False)}")

    if feature in CATEGORICAL:

        values = series.fillna("Unknown").unique()

        write("\nUnique values:")

        for value in sorted(map(str, values)):
            count = (
                series.fillna("Unknown")
                .astype(str)
                .eq(value)
                .sum()
            )

            write(f"  {value}: {count}")

    else:

        numeric = pd.to_numeric(
            series,
            errors="coerce"
        )

        write(f"Minimum: {numeric.min()}")
        write(f"Maximum: {numeric.max()}")
        write(f"Mean: {numeric.mean():.2f}")

        values = sorted(numeric.dropna().unique())

        write("\nUnique values:")

        for value in values:
            write(f"  {value}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
    file.write("\n".join(report))

print("\nReport saved to:", OUTPUT_PATH)