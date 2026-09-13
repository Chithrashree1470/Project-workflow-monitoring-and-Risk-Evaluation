import pandas as pd

INPUT_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\tawos_issue.csv"

OUTPUT_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\tawos_issue_ml.csv"

KEEP_COLUMNS = [
    "ID",
    "Issue_Key",
    "Type",
    "Priority",
    "Status",
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date",
    "Last_Updated",
    "Story_Point",
    "Timespent",
    "Assignee_ID",
    "Project_ID",
    "Sprint_ID"
]

df = pd.read_csv(INPUT_FILE)

missing = [col for col in KEEP_COLUMNS if col not in df.columns]

if missing:
    print("Missing columns:", missing)
else:
    df = df[KEEP_COLUMNS]
    df.to_csv(OUTPUT_FILE, index=False)

    print("Done!")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Saved to:")
    print(OUTPUT_FILE)