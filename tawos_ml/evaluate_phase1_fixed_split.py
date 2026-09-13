import pandas as pd
import json
from pathlib import Path

from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR / "data" / "tawos_phase1_history_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR / "phase1_catboost_with_sprint.pkl"
)

SPLIT_PATH = (
    BASE_DIR / "splits" / "phase1_phase2_test_split.json"
)

# ============================================================
# FEATURES
# ============================================================

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

TARGET = "task_risk_level"

CATEGORICAL_FEATURES = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 - FIXED SPLIT EVALUATION")
print("=" * 70)

df = pd.read_csv(
    DATASET_PATH,
    low_memory=False
)

with open(SPLIT_PATH, "r") as f:
    split = json.load(f)

train_projects = split["train_projects"]
test_projects = split["test_projects"]

print("\nTraining projects:", train_projects)
print("Testing projects :", test_projects)

# ============================================================
# TEST DATA
# ============================================================

test_df = df[
    df["project_id"].isin(test_projects)
].copy()

for col in CATEGORICAL_FEATURES:
    test_df[col] = (
        test_df[col]
        .fillna("Unknown")
        .astype(str)
    )

X_test = test_df[FEATURES]
y_test = test_df[TARGET]

print("\nTest snapshots:", len(test_df))
print("Test issues   :", test_df["issue_id"].nunique())

print("\nTarget distribution:")
print(y_test.value_counts())

# ============================================================
# LOAD MODEL
# ============================================================

model = CatBoostClassifier()

model.load_model(MODEL_PATH)

print("\nModel loaded:")
print(MODEL_PATH)

# ============================================================
# PREDICT
# ============================================================

predictions = model.predict(X_test).flatten()

# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    y_test,
    predictions
)

macro_f1 = f1_score(
    y_test,
    predictions,
    average="macro"
)

weighted_f1 = f1_score(
    y_test,
    predictions,
    average="weighted"
)

print("\n" + "=" * 70)
print("PHASE 1 PERFORMANCE - FIXED SPLIT")
print("=" * 70)

print(f"\nAccuracy    : {accuracy * 100:.2f}%")
print(f"Macro F1    : {macro_f1:.4f}")
print(f"Weighted F1 : {weighted_f1:.4f}")

# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        predictions
    )
)

# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

labels = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

cm = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)

print(
    pd.DataFrame(
        cm,
        index=[f"Actual {x}" for x in labels],
        columns=[f"Predicted {x}" for x in labels]
    )
)

print("\nEvaluation complete.")