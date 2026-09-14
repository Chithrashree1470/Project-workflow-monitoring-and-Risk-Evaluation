import pandas as pd
import numpy as np
import joblib

from pathlib import Path

from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATASET_FILE = (
    DATA_DIR /
    "tawos_10projects_full_history_dataset.csv"
)

MODEL_FILE = (
    BASE_DIR /
    "phase1_10_full_history_catboost.pkl"
)

FEATURE_IMPORTANCE_FILE = (
    BASE_DIR /
    "phase1_10_full_history_feature_importance.csv"
)


# ============================================================
# PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================

TRAIN_PROJECTS = [
    12, 14, 18, 22,
    24, 33, 34, 44
]

TEST_PROJECTS = [
    21, 28
]


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


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

CATEGORICAL_FEATURES = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]


# ============================================================
# TARGET
# ============================================================

TARGET = "task_risk_level"


# ============================================================
# CATBOOST SETTINGS
# ============================================================

RANDOM_SEED = 42

MODEL_PARAMS = {
    "iterations": 500,
    "depth": 7,
    "learning_rate": 0.05,
    "loss_function": "MultiClass",
    "eval_metric": "MultiClass",
    "random_seed": RANDOM_SEED,
    "verbose": 100
}


# ============================================================
# START
# ============================================================

print("=" * 80)
print("CATBOOST TRAINING - 10 PROJECTS FULL HISTORY")
print("=" * 80)

print("\nDataset:")
print(DATASET_FILE)

print("\nTrain projects:")
print(TRAIN_PROJECTS)

print("\nTest projects:")
print(TEST_PROJECTS)

print("\nNumber of features:")
print(len(FEATURES))


# ============================================================
# LOAD DATASET
# ============================================================

print("\n" + "=" * 80)
print("LOADING DATASET")
print("=" * 80)

df = pd.read_csv(
    DATASET_FILE,
    low_memory=False
)

print("\nDataset shape:")
print(df.shape)

print("\nProjects:")
print(sorted(df["project_id"].unique()))

print("\nTotal projects:")
print(df["project_id"].nunique())

print("\nTotal issues:")
print(df["issue_id"].nunique())

print("\nTotal snapshots:")
print(len(df))


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = (
    FEATURES
    + [
        TARGET,
        "project_id",
        "issue_id",
        "snapshot_date",
        "snapshot_number"
    ]
)

missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:

    raise ValueError(
        "Missing required columns: "
        + str(missing_columns)
    )


# ============================================================
# REMOVE INVALID TARGET ROWS
# ============================================================

df = df.dropna(
    subset=[TARGET]
).copy()


# ============================================================
# PROJECT SPLIT
# ============================================================

train_df = df[
    df["project_id"].isin(TRAIN_PROJECTS)
].copy()

test_df = df[
    df["project_id"].isin(TEST_PROJECTS)
].copy()


# ============================================================
# SAFETY CHECK
# ============================================================

train_projects_found = set(
    train_df["project_id"].unique()
)

test_projects_found = set(
    test_df["project_id"].unique()
)

overlap = (
    train_projects_found
    &
    test_projects_found
)

if overlap:

    raise RuntimeError(
        "Project leakage detected: "
        + str(overlap)
    )


# ============================================================
# SPLIT REPORT
# ============================================================

print("\n" + "=" * 80)
print("PROJECT-LEVEL SPLIT")
print("=" * 80)

print("\nTraining projects:")
print(sorted(train_projects_found))

print("\nTesting projects:")
print(sorted(test_projects_found))

print("\nTraining snapshots:")
print(f"{len(train_df):,}")

print("Testing snapshots:")
print(f"{len(test_df):,}")

print("\nTraining issues:")
print(
    train_df["issue_id"].nunique()
)

print("Testing issues:")
print(
    test_df["issue_id"].nunique()
)


# ============================================================
# VERIFY NO ISSUE OVERLAP
# ============================================================

train_issues = set(
    train_df["issue_id"]
)

test_issues = set(
    test_df["issue_id"]
)

issue_overlap = (
    train_issues
    &
    test_issues
)

if issue_overlap:

    raise RuntimeError(
        "Issue leakage detected. "
        f"{len(issue_overlap)} issues appear "
        "in both train and test."
    )

print(
    "\nIssue overlap:",
    len(issue_overlap)
)


# ============================================================
# PREPARE X / Y
# ============================================================

X_train = train_df[
    FEATURES
].copy()

y_train = train_df[
    TARGET
].copy()

X_test = test_df[
    FEATURES
].copy()

y_test = test_df[
    TARGET
].copy()


# ============================================================
# CLEAN FEATURES
# ============================================================

for col in CATEGORICAL_FEATURES:

    X_train[col] = (
        X_train[col]
        .fillna("Unknown")
        .astype(str)
    )

    X_test[col] = (
        X_test[col]
        .fillna("Unknown")
        .astype(str)
    )


# ============================================================
# NUMERIC FEATURES
# ============================================================

numeric_features = [
    col
    for col in FEATURES
    if col not in CATEGORICAL_FEATURES
]

for col in numeric_features:

    X_train[col] = pd.to_numeric(
        X_train[col],
        errors="coerce"
    )

    X_test[col] = pd.to_numeric(
        X_test[col],
        errors="coerce"
    )

    X_train[col] = X_train[col].fillna(0)
    X_test[col] = X_test[col].fillna(0)


# ============================================================
# CATBOOST CATEGORY INDICES
# ============================================================

cat_feature_indices = [
    FEATURES.index(col)
    for col in CATEGORICAL_FEATURES
]


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 80)
print("TRAINING TARGET DISTRIBUTION")
print("=" * 80)

print(
    y_train.value_counts()
)

print("\nTraining percentages:")

print(
    (
        y_train.value_counts(
            normalize=True
        )
        * 100
    ).round(2)
)


print("\n" + "=" * 80)
print("TEST TARGET DISTRIBUTION")
print("=" * 80)

print(
    y_test.value_counts()
)

print("\nTesting percentages:")

print(
    (
        y_test.value_counts(
            normalize=True
        )
        * 100
    ).round(2)
)


# ============================================================
# TRAIN MODEL
# ============================================================

print("\n" + "=" * 80)
print("TRAINING CATBOOST")
print("=" * 80)

print("\nModel parameters:")

for key, value in MODEL_PARAMS.items():

    print(
        f"{key}: {value}"
    )


model = CatBoostClassifier(
    **MODEL_PARAMS
)


model.fit(
    X_train,
    y_train,
    cat_features=cat_feature_indices
)


# ============================================================
# PREDICTION
# ============================================================

print("\n" + "=" * 80)
print("GENERATING TEST PREDICTIONS")
print("=" * 80)

y_pred = model.predict(
    X_test
)

y_pred = np.array(
    y_pred
).reshape(-1)


# ============================================================
# CLASS PROBABILITIES
# ============================================================

y_proba = model.predict_proba(
    X_test
)

class_names = list(
    model.classes_
)


# ============================================================
# EVALUATION
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


print("\n" + "=" * 80)
print("MODEL PERFORMANCE")
print("=" * 80)

print(
    f"\nAccuracy   : {accuracy:.4f}"
)

print(
    f"Macro F1   : {macro_f1:.4f}"
)

print(
    f"Weighted F1: {weighted_f1:.4f}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "=" * 80)
print("CLASSIFICATION REPORT")
print("=" * 80)

report = classification_report(
    y_test,
    y_pred,
    labels=class_names,
    digits=4
)

print(report)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n" + "=" * 80)
print("CONFUSION MATRIX")
print("=" * 80)

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=class_names
)

cm_df = pd.DataFrame(
    cm,
    index=[
        f"Actual_{x}"
        for x in class_names
    ],
    columns=[
        f"Predicted_{x}"
        for x in class_names
    ]
)

print(cm_df)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 80)
print("FEATURE IMPORTANCE")
print("=" * 80)

importance = model.get_feature_importance()

feature_importance_df = pd.DataFrame({

    "feature":
        FEATURES,

    "importance":
        importance
})

feature_importance_df = (
    feature_importance_df
    .sort_values(
        "importance",
        ascending=False
    )
    .reset_index(drop=True)
)

print(
    feature_importance_df
)


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

feature_importance_df.to_csv(
    FEATURE_IMPORTANCE_FILE,
    index=False
)

print(
    "\nFeature importance saved to:"
)

print(
    FEATURE_IMPORTANCE_FILE
)


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_FILE
)

print(
    "\nModel saved to:"
)

print(
    MODEL_FILE
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)

print(
    f"\nTraining snapshots : {len(X_train):,}"
)

print(
    f"Testing snapshots  : {len(X_test):,}"
)

print(
    f"Training issues    : "
    f"{train_df['issue_id'].nunique():,}"
)

print(
    f"Testing issues     : "
    f"{test_df['issue_id'].nunique():,}"
)

print(
    f"Training projects  : "
    f"{train_df['project_id'].nunique()}"
)

print(
    f"Testing projects   : "
    f"{test_df['project_id'].nunique()}"
)

print(
    f"\nAccuracy           : {accuracy:.4f}"
)

print(
    f"Macro F1           : {macro_f1:.4f}"
)

print(
    f"Weighted F1        : {weighted_f1:.4f}"
)

print(
    "\nModel:"
)

print(
    MODEL_FILE
)

print(
    "\nFeature importance:"
)

print(
    FEATURE_IMPORTANCE_FILE
)

print("=" * 80)