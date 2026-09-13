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
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "tawos_phase2_history_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "phase2_catboost_with_sprint.pkl"
)

IMPORTANCE_PATH = (
    BASE_DIR
    / "phase2_feature_importance_with_sprint.csv"
)

# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("TAWOS PHASE 2 - HISTORICAL CATBOOST WITH SPRINT")
print("=" * 70)

df = pd.read_csv(DATASET_PATH)

print("\nRows    :", len(df))
print("Columns :", len(df))
print("Projects:", df["project_id"].nunique())
print("Issues  :", df["issue_id"].nunique())

# ============================================================
# FEATURES
# ============================================================

FEATURES = [

    # Phase 1 features
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
    "changes_last_7_days",

    # Phase 2 historical features
    "total_change_count",
    "distinct_assignee_count",
    "distinct_status_count",
    "distinct_priority_count",
    "distinct_sprint_count",
    "status_transition_count",
    "reassignment_count",
    "recent_total_changes_7d",
    "recent_status_changes_7d",
    "recent_assignee_changes_7d",
    "recent_priority_changes_7d",
    "recent_sprint_changes_7d",
    "recent_timespent_changes_7d",
    "days_since_last_status_change",
    "days_since_last_assignee_change",
    "days_since_last_priority_change",
    "days_since_last_sprint_change"
]

TARGET = "task_risk_level"

# ============================================================
# SAFETY CHECK
# ============================================================

missing = [
    col for col in FEATURES + [TARGET]
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )

# Make categorical values explicit
CATEGORICAL_FEATURES = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]

for col in CATEGORICAL_FEATURES:
    df[col] = df[col].fillna("Unknown").astype(str)

print("\nFeature count:", len(FEATURES))

print("\nCategorical features:")

for col in CATEGORICAL_FEATURES:
    print(" ✓", col)

# ============================================================
# PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("PROJECT-LEVEL TRAIN / TEST SPLIT")
print("=" * 70)

projects = sorted(df["project_id"].unique())

rng = np.random.RandomState(42)
rng.shuffle(projects)

split_index = int(len(projects) * 0.8)

train_projects = sorted(projects[:split_index])
test_projects = sorted(projects[split_index:])

train_df = df[
    df["project_id"].isin(train_projects)
].copy()

test_df = df[
    df["project_id"].isin(test_projects)
].copy()

print("\nTraining projects:", len(train_projects))
print("Testing projects :", len(test_projects))

print("\nTraining project IDs:", train_projects)
print("Testing project IDs :", test_projects)

print("\nTraining snapshots:", len(train_df))
print("Testing snapshots :", len(test_df))

print("\nTraining issues:",
      train_df["issue_id"].nunique())

print("Testing issues :",
      test_df["issue_id"].nunique())

# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\nTraining target distribution:")
print(train_df[TARGET].value_counts())

print("\nTesting target distribution:")
print(test_df[TARGET].value_counts())

# ============================================================
# CLASS WEIGHTS
# Same strategy as Phase 1
# ============================================================

class_counts = train_df[TARGET].value_counts()

total = len(train_df)
num_classes = len(class_counts)

class_weights = {}

for cls in class_counts.index:

    weight = (
        total
        /
        (num_classes * class_counts[cls])
    )

    class_weights[cls] = weight

print("\nCalculated class weights:")

for cls, weight in class_weights.items():
    print(f"{cls:<10}: {weight:.3f}")

# ============================================================
# PREPARE DATA
# ============================================================

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]

cat_indices = [
    FEATURES.index(col)
    for col in CATEGORICAL_FEATURES
]

# ============================================================
# TRAIN CATBOOST
# ============================================================

print("\n" + "=" * 70)
print("TRAINING PHASE 2 CATBOOST")
print("=" * 70)

model = CatBoostClassifier(

    iterations=700,

    depth=8,

    learning_rate=0.05,

    loss_function="MultiClass",

    eval_metric="MultiClass",

    random_seed=42,

    class_weights=[
        class_weights.get(cls, 1.0)
        for cls in sorted(class_counts.index)
    ],

    cat_features=cat_indices,

    verbose=100,

    l2_leaf_reg=5,

    random_strength=1,

    early_stopping_rounds=100
)

model.fit(
    X_train,
    y_train,
    eval_set=(X_test, y_test),
    use_best_model=True
)

# ============================================================
# PREDICTION
# ============================================================

predictions = model.predict(X_test)

predictions = predictions.flatten()

# ============================================================
# PERFORMANCE
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
print("TAWOS PHASE 2 PERFORMANCE")
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

labels = sorted(y_test.unique())

cm = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)

cm_df = pd.DataFrame(
    cm,
    index=[
        f"Actual {x}"
        for x in labels
    ],
    columns=[
        f"Predicted {x}"
        for x in labels
    ]
)

print(cm_df)

# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)

importance = pd.DataFrame({

    "feature": FEATURES,

    "importance": model.feature_importances_

}).sort_values(
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

model.save_model(MODEL_PATH)

importance.to_csv(
    IMPORTANCE_PATH,
    index=False
)

print("\n" + "=" * 70)
print("PHASE 2 TRAINING COMPLETE")
print("=" * 70)

print("\nModel saved:")
print(MODEL_PATH)

print("\nFeature importance saved:")
print(IMPORTANCE_PATH)