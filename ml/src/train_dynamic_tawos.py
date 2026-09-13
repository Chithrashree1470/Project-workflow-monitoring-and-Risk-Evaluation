import pandas as pd
import numpy as np
import joblib

from pathlib import Path

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

DATASET_PATH = (
    BASE_DIR.parent.parent
    / "dataset"
    / "tawos_phase1_training_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "dynamic_tawos_catboost_model.pkl"
)

IMPORTANCE_PATH = (
    BASE_DIR
    / "dynamic_tawos_feature_importance.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("DYNAMIC TAWOS PROJECT RISK - CATBOOST")
print("=" * 70)


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading TAWOS dynamic dataset...")

df = pd.read_csv(DATASET_PATH)

print("Rows    :", len(df))
print("Columns :", len(df.columns))

print("\nDetected columns:")
print(df.columns.tolist())


# ============================================================
# BASIC VALIDATION
# ============================================================

REQUIRED_COLUMNS = [
    "project_id",
    "issue_id",
    "snapshot_date",
    "task_risk_level"
]

missing = [
    column
    for column in REQUIRED_COLUMNS
    if column not in df.columns
]

if missing:

    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# DATE CONVERSION
# ============================================================

df["snapshot_date"] = pd.to_datetime(
    df["snapshot_date"],
    errors="coerce",
    utc=True
)


# ============================================================
# CLEANING
# ============================================================

df = df.dropna(
    subset=[
        "project_id",
        "issue_id",
        "snapshot_date",
        "task_risk_level"
    ]
).copy()


print("\nUsable rows :", len(df))

print(
    "Projects    :",
    df["project_id"].nunique()
)

print(
    "Tasks       :",
    df["issue_id"].nunique()
)


# ============================================================
# TARGET
# ============================================================

TARGET = "task_risk_level"


# ============================================================
# FEATURES
# ============================================================
#
# These are prediction-time features.
#
# We explicitly exclude:
#
# project_id       -> identifier
# issue_id         -> identifier
# issue_key        -> identifier
# snapshot_date    -> reference timestamp
# delay_days       -> FUTURE information
# task_risk_level  -> target
#
# ============================================================

EXCLUDED_COLUMNS = [

    "project_id",
    "issue_id",
    "issue_key",
    "snapshot_date",

    # Future outcome
    "delay_days",

    # Target
    "task_risk_level"
]


FEATURES = [
    column
    for column in df.columns
    if column not in EXCLUDED_COLUMNS
]


X = df[FEATURES].copy()

y = df[TARGET].copy()


print("\nDynamic model features:", len(FEATURES))

print("\nFeatures used:")

for feature in FEATURES:

    print(" ✓", feature)


# ============================================================
# HANDLE CATEGORICAL FEATURES
# ============================================================

categorical_columns = X.select_dtypes(
    include=["object"]
).columns.tolist()


for column in categorical_columns:

    X[column] = (
        X[column]
        .fillna("Unknown")
        .astype(str)
    )


cat_features = [
    X.columns.get_loc(column)
    for column in categorical_columns
]


print(
    "\nCategorical features:",
    len(categorical_columns)
)

if categorical_columns:

    for column in categorical_columns:

        print(
            " ✓",
            column
        )


# ============================================================
# PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================
#
# IMPORTANT:
#
# All snapshots belonging to the same project remain in
# the same split.
#
# This prevents snapshots from the same project appearing
# in both training and testing.
# ============================================================

print("\n" + "=" * 70)
print("PROJECT-LEVEL TRAIN / TEST SPLIT")
print("=" * 70)


projects = df["project_id"].unique()


rng = np.random.RandomState(42)

rng.shuffle(projects)


split_index = int(
    len(projects) * 0.80
)


train_projects = projects[:split_index]

test_projects = projects[split_index:]


train_mask = df["project_id"].isin(
    train_projects
)

test_mask = df["project_id"].isin(
    test_projects
)


X_train = X.loc[train_mask]

X_test = X.loc[test_mask]

y_train = y.loc[train_mask]

y_test = y.loc[test_mask]


print(
    "Training projects:",
    len(train_projects)
)

print(
    "Testing projects :",
    len(test_projects)
)

print(
    "Training snapshots:",
    len(X_train)
)

print(
    "Testing snapshots :",
    len(X_test)
)


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\nTraining risk distribution:")

print(
    y_train.value_counts()
)


print("\nTesting risk distribution:")

print(
    y_test.value_counts()
)


# ============================================================
# CLASS WEIGHTS
# ============================================================
#
# Low has fewer snapshots because low-delay tasks tend to have
# shorter lifetimes.
#
# Start with moderate weighting rather than aggressive weights.
# ============================================================

class_weights = {

    "Critical": 1.0,

    "High": 1.05,

    "Medium": 1.10,

    "Low": 1.20
}


print("\nClass weights:")

for class_name, weight in class_weights.items():

    print(
        f" {class_name:<10}: {weight}"
    )


# ============================================================
# TRAIN CATBOOST
# ============================================================

print("\n" + "=" * 70)
print("TRAINING DYNAMIC TAWOS CATBOOST")
print("=" * 70)


model = CatBoostClassifier(

    depth=6,

    learning_rate=0.05,

    iterations=800,

    l2_leaf_reg=5,

    loss_function="MultiClass",

    eval_metric="Accuracy",

    random_seed=42,

    class_weights=class_weights,

    cat_features=cat_features,

    verbose=100
)


model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICTION
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC TAWOS MODEL PERFORMANCE")
print("=" * 70)


y_pred = model.predict(
    X_test
)

y_pred = y_pred.ravel()


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
        y_pred,
        labels=model.classes_,
        zero_division=0
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)


matrix = confusion_matrix(
    y_test,
    y_pred,
    labels=model.classes_
)


matrix_df = pd.DataFrame(

    matrix,

    index=[
        f"Actual {c}"
        for c in model.classes_
    ],

    columns=[
        f"Predicted {c}"
        for c in model.classes_
    ]
)


print(matrix_df)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)


importance = model.get_feature_importance()


importance_df = pd.DataFrame({

    "Feature": FEATURES,

    "Importance": importance

})


importance_df = (
    importance_df
    .sort_values(
        "Importance",
        ascending=False
    )
)


for _, row in importance_df.iterrows():

    print(
        f"{row['Feature']:35} "
        f"{row['Importance']:.4f}"
    )


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

importance_df.to_csv(
    IMPORTANCE_PATH,
    index=False
)


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("DYNAMIC TAWOS CATBOOST TRAINING COMPLETE")
print("=" * 70)


print("\nModel saved as:")
print(MODEL_PATH)


print("\nFeature importance saved as:")
print(IMPORTANCE_PATH)