import json
from pathlib import Path

import joblib
import pandas as pd

from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "tawos_39projects_full_history_phase1.csv"
SPLIT_FILE = DATA_DIR / "tawos_39project_split.json"

MODEL_FILE = DATA_DIR / "phase1_39projects_full_history_catboost.pkl"
IMPORTANCE_FILE = DATA_DIR / "phase1_39projects_full_history_feature_importance.csv"
METRICS_FILE = DATA_DIR / "phase1_39projects_full_history_metrics.txt"
PREDICTIONS_FILE = DATA_DIR / "phase1_39projects_full_history_predictions.csv"


# ============================================================
# PHASE 1 FEATURES
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

CATEGORICAL_FEATURES = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

TARGET = "task_risk_level"

PROJECT_COLUMN = "project_id"


# ============================================================
# CATBOOST SETTINGS
# Same configuration used in the previous experiment
# ============================================================

MODEL_PARAMS = {
    "iterations": 500,
    "depth": 7,
    "learning_rate": 0.05,
    "loss_function": "MultiClass",
    "eval_metric": "MultiClass",
    "random_seed": 42,
    "verbose": 100
}


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("PHASE 1 - 39 PROJECTS - FULL HISTORY / ALL SNAPSHOTS")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(INPUT_FILE)

print("Dataset shape:", df.shape)
print("Projects:", df[PROJECT_COLUMN].nunique())

print("\nProject IDs:")
print(sorted(df[PROJECT_COLUMN].dropna().unique().tolist()))


# ============================================================
# LOAD FIXED PROJECT SPLIT
# ============================================================

print("\nLoading fixed project split...")

with open(SPLIT_FILE, "r") as f:
    split = json.load(f)

TRAIN_PROJECTS = split["train_projects"]
TEST_PROJECTS = split["test_projects"]

print("\nTrain projects:")
print(TRAIN_PROJECTS)

print("\nTest projects:")
print(TEST_PROJECTS)

print("\nTrain project count:", len(TRAIN_PROJECTS))
print("Test project count:", len(TEST_PROJECTS))


# ============================================================
# VALIDATE SPLIT
# ============================================================

train_set = set(TRAIN_PROJECTS)
test_set = set(TEST_PROJECTS)

if train_set & test_set:
    raise ValueError("ERROR: Train/test project overlap detected.")

all_projects = set(df[PROJECT_COLUMN].dropna().astype(int).unique())

if train_set | test_set != all_projects:
    missing = all_projects - (train_set | test_set)
    extra = (train_set | test_set) - all_projects

    raise ValueError(
        f"Project split does not match dataset.\n"
        f"Missing: {missing}\n"
        f"Extra: {extra}"
    )


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = FEATURES + [TARGET, PROJECT_COLUMN]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# CLEAN DATA
# ============================================================

print("\nCleaning data...")

data = df[required_columns].copy()

for col in CATEGORICAL_FEATURES:
    data[col] = data[col].fillna("Unknown").astype(str)

numeric_features = [
    col for col in FEATURES
    if col not in CATEGORICAL_FEATURES
]

for col in numeric_features:
    data[col] = pd.to_numeric(
        data[col],
        errors="coerce"
    ).fillna(0)


# ============================================================
# TRAIN / TEST SPLIT BY PROJECT
# ============================================================

train_df = data[
    data[PROJECT_COLUMN].isin(TRAIN_PROJECTS)
].copy()

test_df = data[
    data[PROJECT_COLUMN].isin(TEST_PROJECTS)
].copy()

print("\nTraining rows:", len(train_df))
print("Testing rows:", len(test_df))

print("\nTraining projects:", train_df[PROJECT_COLUMN].nunique())
print("Testing projects:", test_df[PROJECT_COLUMN].nunique())


# ============================================================
# FEATURES AND TARGET
# ============================================================

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


# ============================================================
# DISPLAY TARGET DISTRIBUTION
# ============================================================

print("\nTraining target distribution:")
print(y_train.value_counts())

print("\nTesting target distribution:")
print(y_test.value_counts())


# ============================================================
# CATBOOST CATEGORICAL INDICES
# ============================================================

cat_feature_indices = [
    FEATURES.index(col)
    for col in CATEGORICAL_FEATURES
]


# ============================================================
# TRAIN MODEL
# ============================================================

print("\n" + "=" * 70)
print("TRAINING CATBOOST")
print("=" * 70)

model = CatBoostClassifier(
    **MODEL_PARAMS,
    cat_features=cat_feature_indices
)

model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICTIONS
# ============================================================

print("\nGenerating predictions...")

y_pred = model.predict(X_test)

# CatBoost returns shape (n, 1)
y_pred = y_pred.ravel()

y_prob = model.predict_proba(X_test)

classes = list(model.classes_)


# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

macro_f1 = f1_score(
    y_test,
    y_pred,
    average="macro"
)

weighted_f1 = f1_score(
    y_test,
    y_pred,
    average="weighted"
)

report = classification_report(
    y_test,
    y_pred,
    digits=4
)

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=classes
)


# ============================================================
# PRINT RESULTS
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1 RESULTS")
print("=" * 70)

print(f"\nAccuracy:    {accuracy:.4f}")
print(f"Macro F1:    {macro_f1:.4f}")
print(f"Weighted F1: {weighted_f1:.4f}")

print("\nClassification Report:")
print(report)

print("\nClasses:")
print(classes)

print("\nConfusion Matrix:")
print(cm)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

importance = model.get_feature_importance()

importance_df = pd.DataFrame({
    "feature": FEATURES,
    "importance": importance
})

importance_df = importance_df.sort_values(
    "importance",
    ascending=False
)

print("\nFeature Importance:")
print(importance_df.to_string(index=False))


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_FILE
)

print(f"\nModel saved to:")
print(MODEL_FILE)


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

importance_df.to_csv(
    IMPORTANCE_FILE,
    index=False
)

print("\nFeature importance saved to:")
print(IMPORTANCE_FILE)


# ============================================================
# SAVE METRICS
# ============================================================

with open(METRICS_FILE, "w") as f:

    f.write("PHASE 1 - 39 PROJECTS - FULL HISTORY\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"Dataset rows: {len(data)}\n")
    f.write(f"Training rows: {len(train_df)}\n")
    f.write(f"Testing rows: {len(test_df)}\n\n")

    f.write(
        f"Training projects ({len(TRAIN_PROJECTS)}): "
        f"{TRAIN_PROJECTS}\n"
    )

    f.write(
        f"Testing projects ({len(TEST_PROJECTS)}): "
        f"{TEST_PROJECTS}\n\n"
    )

    f.write(f"Accuracy: {accuracy:.4f}\n")
    f.write(f"Macro F1: {macro_f1:.4f}\n")
    f.write(f"Weighted F1: {weighted_f1:.4f}\n\n")

    f.write("Classification Report:\n")
    f.write(report)

    f.write("\nConfusion Matrix:\n")
    f.write(str(cm))

    f.write("\n\nFeature Importance:\n")
    f.write(
        importance_df.to_string(index=False)
    )


print("\nMetrics saved to:")
print(METRICS_FILE)


# ============================================================
# SAVE PREDICTIONS
# ============================================================

predictions_df = test_df.copy()

predictions_df["actual_risk"] = y_test.values
predictions_df["predicted_risk"] = y_pred

for i, class_name in enumerate(classes):
    predictions_df[
        f"prob_{class_name.lower()}"
    ] = y_prob[:, i]

predictions_df.to_csv(
    PREDICTIONS_FILE,
    index=False
)

print("\nPredictions saved to:")
print(PREDICTIONS_FILE)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("PHASE 1 COMPLETE")
print("=" * 70)

print(f"""
Accuracy:    {accuracy:.4f}
Macro F1:    {macro_f1:.4f}
Weighted F1: {weighted_f1:.4f}

Train projects: {len(TRAIN_PROJECTS)}
Test projects:  {len(TEST_PROJECTS)}

Model:
{MODEL_FILE}
""")