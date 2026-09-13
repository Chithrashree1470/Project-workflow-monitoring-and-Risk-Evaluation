import pandas as pd
import numpy as np

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

DATA_PATH = (
    BASE_DIR
    / "data"
    / "tawos_phase1_history_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "phase1_catboost_without_sprint.pkl"
)

IMPORTANCE_PATH = (
    BASE_DIR
    / "phase1_feature_importance_without_sprint.csv"
)


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 - CATBOOST WITHOUT SPRINT")
print("=" * 70)

df = pd.read_csv(
    DATA_PATH,
    low_memory=False
)

print("\nRows    :", len(df))
print("Columns :", len(df.columns))


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
    "assignee"
]


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required = [
    "project_id",
    "issue_id",
    "task_risk_level"
] + FEATURES

missing = [
    col
    for col in required
    if col not in df.columns
]

if missing:

    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# CLEAN
# ============================================================

df = df.dropna(
    subset=[
        "project_id",
        "issue_id",
        "task_risk_level"
    ]
).copy()


for col in CATEGORICAL:

    df[col] = (
        df[col]
        .fillna("Unknown")
        .astype(str)
    )


print(
    "\nUsable rows:",
    len(df)
)

print(
    "Projects:",
    df["project_id"].nunique()
)

print(
    "Issues:",
    df["issue_id"].nunique()
)


# ============================================================
# PROJECT SPLIT
#
# IMPORTANT:
# EXACT SAME RANDOM SEED AND SPLIT STRATEGY AS THE
# WITH-SPRINT MODEL.
# ============================================================

projects = sorted(
    df["project_id"]
    .unique()
)

rng = np.random.RandomState(42)

rng.shuffle(projects)

TEST_PROJECT_COUNT = 2

test_projects = sorted(
    projects[:TEST_PROJECT_COUNT]
)

train_projects = sorted(
    projects[TEST_PROJECT_COUNT:]
)


train_df = df[
    df["project_id"].isin(
        train_projects
    )
].copy()

test_df = df[
    df["project_id"].isin(
        test_projects
    )
].copy()


print("\n" + "=" * 70)
print("PROJECT-LEVEL TRAIN / TEST SPLIT")
print("=" * 70)

print(
    "Training projects:",
    len(train_projects)
)

print(
    "Testing projects :",
    len(test_projects)
)

print(
    "\nTraining project IDs:",
    train_projects
)

print(
    "Testing project IDs :",
    test_projects
)

print(
    "\nTraining snapshots:",
    len(train_df)
)

print(
    "Testing snapshots :",
    len(test_df)
)


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\nTraining target distribution:")

print(
    train_df[
        "task_risk_level"
    ].value_counts()
)

print("\nTesting target distribution:")

print(
    test_df[
        "task_risk_level"
    ].value_counts()
)


# ============================================================
# X / Y
# ============================================================

X_train = train_df[
    FEATURES
].copy()

y_train = train_df[
    "task_risk_level"
].copy()

X_test = test_df[
    FEATURES
].copy()

y_test = test_df[
    "task_risk_level"
].copy()


# ============================================================
# CLASS WEIGHTS
# ============================================================

class_counts = (
    y_train
    .value_counts()
)

total = len(
    y_train
)

num_classes = len(
    class_counts
)

class_weights = {}

for label in [
    "Low",
    "Medium",
    "High",
    "Critical"
]:

    count = class_counts.get(
        label,
        1
    )

    class_weights[label] = (
        total
        /
        (num_classes * count)
    )


print("\nCalculated class weights:")

for label in [
    "Low",
    "Medium",
    "High",
    "Critical"
]:

    print(
        f"{label:10s}: "
        f"{class_weights[label]:.3f}"
    )


weights = [
    class_weights[label]
    for label in [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]
]


# ============================================================
# CATEGORICAL INDEX
# ============================================================

cat_indices = [
    FEATURES.index(
        col
    )
    for col in CATEGORICAL
]


print(
    "\nCategorical features:",
    len(CATEGORICAL)
)

for col in CATEGORICAL:

    print(
        " ✓",
        col
    )


# ============================================================
# TRAIN
# ============================================================

print("\n" + "=" * 70)
print("TRAINING CATBOOST")
print("=" * 70)

model = CatBoostClassifier(

    iterations=700,

    depth=6,

    learning_rate=0.05,

    loss_function="MultiClass",

    eval_metric="MultiClass",

    class_weights=weights,

    l2_leaf_reg=5,

    random_seed=42,

    verbose=100
)


model.fit(

    X_train,
    y_train,

    cat_features=cat_indices,

    eval_set=(
        X_test,
        y_test
    ),

    use_best_model=True
)


# ============================================================
# PREDICT
# ============================================================

pred = (
    model
    .predict(X_test)
    .ravel()
)


# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    y_test,
    pred
)

macro_f1 = f1_score(
    y_test,
    pred,
    average="macro"
)

weighted_f1 = f1_score(
    y_test,
    pred,
    average="weighted"
)


print("\n" + "=" * 70)
print("TAWOS PHASE 1 PERFORMANCE - WITHOUT SPRINT")
print("=" * 70)

print(
    f"\nAccuracy    : {accuracy * 100:.2f}%"
)

print(
    f"Macro F1    : {macro_f1:.4f}"
)

print(
    f"Weighted F1 : {weighted_f1:.4f}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        pred,
        labels=[
            "Low",
            "Medium",
            "High",
            "Critical"
        ],
        zero_division=0
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

class_names = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

cm = confusion_matrix(
    y_test,
    pred,
    labels=class_names
)

cm_df = pd.DataFrame(
    cm,
    index=[
        f"Actual {x}"
        for x in class_names
    ],
    columns=[
        f"Predicted {x}"
        for x in class_names
    ]
)

print(
    cm_df
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)

importance = pd.DataFrame({

    "feature":
        FEATURES,

    "importance":
        model.get_feature_importance()
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print(
    importance.to_string(
        index=False
    )
)


# ============================================================
# SAVE
# ============================================================

model.save_model(
    MODEL_PATH
)

importance.to_csv(
    IMPORTANCE_PATH,
    index=False
)


print("\n" + "=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)

print(
    "\nModel saved:",
    MODEL_PATH
)

print(
    "Feature importance saved:",
    IMPORTANCE_PATH
)