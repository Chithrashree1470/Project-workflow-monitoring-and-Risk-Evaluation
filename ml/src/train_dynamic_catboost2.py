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
    / "dynamic_training_dataset_v3.csv"
)

MODEL_PATH = (
    BASE_DIR / "dynamic_catboost_v2_weighted_model.pkl"
)


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("DYNAMIC PROJECT RISK - CATBOOST V2 WEIGHTED")
print("=" * 70)

print("\nLoading dynamic dataset...")

df = pd.read_csv(DATASET_PATH)

print("Rows    :", len(df))
print("Columns :", len(df.columns))


# ============================================================
# BASIC CLEANING
# ============================================================

df["snapshot_date"] = pd.to_datetime(
    df["snapshot_date"],
    errors="coerce",
    utc=True
)

df = df.dropna(
    subset=[
        "project_id",
        "snapshot_date",
        "dynamic_risk_level"
    ]
)

print("Usable rows :", len(df))
print(
    "Projects    :",
    df["project_id"].nunique()
)


# ============================================================
# TARGET
# ============================================================

TARGET = "dynamic_risk_level"


# ============================================================
# FEATURES
# ============================================================

EXCLUDED_COLUMNS = [
    "project_id",
    "snapshot_date",

    # Future information
    "future_completed_30d",
    "future_delayed_30d",
    "future_delayed_rate",

    # Target
    "dynamic_risk_level"
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


# ============================================================
# PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================
#
# IMPORTANT:
#
# We split PROJECTS, not snapshots.
#
# Every snapshot belonging to a project goes entirely
# into either the training set or testing set.
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
# CHECK TARGET DISTRIBUTION
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
# Give slightly more importance to the classes that have
# historically been harder for the model to distinguish.
#
# Low receives a slightly lower weight because it has been
# the easiest class to predict.
# ============================================================

class_weights = {
    "Critical": 1.00,
    "High": 1.15,
    "Low": 0.90,
    "Medium": 1.15
}


print("\nClass weights:")

for risk, weight in class_weights.items():
    print(f" {risk:10} : {weight}")


# ============================================================
# TRAIN CATBOOST
# ============================================================

print("\n" + "=" * 70)
print("TRAINING WEIGHTED DYNAMIC CATBOOST")
print("=" * 70)


model = CatBoostClassifier(

    # Slightly deeper than the original model
    depth=5,

    # Slower learning
    learning_rate=0.05,

    # More boosting iterations
    iterations=1000,

    # Regularization
    l2_leaf_reg=5,

    loss_function="MultiClass",

    # Focus evaluation on balanced class performance
    eval_metric="TotalF1",

    random_seed=42,

    cat_features=cat_features,

    # Class weighting
    class_weights=class_weights,

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
print("DYNAMIC MODEL PERFORMANCE")
print("=" * 70)


y_pred = model.predict(X_test)

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


importance_df = importance_df.sort_values(
    "Importance",
    ascending=False
)


for _, row in importance_df.iterrows():

    print(
        f"{row['Feature']:35} "
        f"{row['Importance']:.4f}"
    )


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

importance_path = (
    BASE_DIR
    / "dynamic_feature_importance_v2_weighted.csv"
)


importance_df.to_csv(
    importance_path,
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
print("WEIGHTED DYNAMIC CATBOOST TRAINING COMPLETE")
print("=" * 70)

print("\nModel saved as:")
print(MODEL_PATH)

print("\nFeature importance saved as:")
print(importance_path)