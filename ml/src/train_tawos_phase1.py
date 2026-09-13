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
    / "tawos_phase1_catboost_model.pkl"
)

IMPORTANCE_PATH = (
    BASE_DIR
    / "tawos_phase1_feature_importance.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 - LEAKAGE-FREE CATBOOST")
print("=" * 70)


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading Phase 1 dataset...")

df = pd.read_csv(DATASET_PATH)

print("Rows    :", len(df))
print("Columns :", len(df.columns))

print("\nDetected columns:")
print(df.columns.tolist())


# ============================================================
# BASIC CLEANING
# ============================================================

required_columns = [
    "ID",
    "Issue_Key",
    "Project_ID",
    "Type",
    "Priority",
    "Story_Point",
    "estimated_duration_days",
    "has_assignee",
    "has_sprint",
    "task_risk_level"
]

missing = [
    c for c in required_columns
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


df = df.dropna(
    subset=[
        "Project_ID",
        "task_risk_level"
    ]
).copy()


print("\nUsable rows :", len(df))
print(
    "Projects    :",
    df["Project_ID"].nunique()
)


# ============================================================
# TARGET
# ============================================================

TARGET = "task_risk_level"


# ============================================================
# FEATURES
# ============================================================
#
# IMPORTANT:
#
# delay_days is the value used to CREATE the target.
# It MUST NOT be used as a model feature.
#
# Resolution_Date, Last_Updated, Timespent, Status and
# Assignee_ID are also excluded because Phase 1 is intended
# to represent information available at task creation.
# ============================================================

FEATURES = [

    "Type",

    "Priority",

    "Story_Point",

    "estimated_duration_days",

    "has_assignee",

    "has_sprint"

]


X = df[FEATURES].copy()
y = df[TARGET].copy()


print(
    "\nPhase 1 model features:",
    len(FEATURES)
)

print("\nFeatures used:")

for feature in FEATURES:
    print(" ✓", feature)


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

X["Type"] = (
    X["Type"]
    .fillna("Unknown")
    .astype(str)
)

X["Priority"] = (
    X["Priority"]
    .fillna("Unknown")
    .astype(str)
)


X["Story_Point"] = pd.to_numeric(
    X["Story_Point"],
    errors="coerce"
).fillna(0)


X["estimated_duration_days"] = pd.to_numeric(
    X["estimated_duration_days"],
    errors="coerce"
)


X["estimated_duration_days"] = (
    X["estimated_duration_days"]
    .fillna(
        X["estimated_duration_days"].median()
    )
)


X["has_assignee"] = pd.to_numeric(
    X["has_assignee"],
    errors="coerce"
).fillna(0)


X["has_sprint"] = pd.to_numeric(
    X["has_sprint"],
    errors="coerce"
).fillna(0)


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

categorical_columns = [
    "Type",
    "Priority"
]


cat_features = [
    X.columns.get_loc(column)
    for column in categorical_columns
]


print(
    "\nCategorical features:",
    len(categorical_columns)
)

for column in categorical_columns:
    print(" ✓", column)


# ============================================================
# PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("PROJECT-LEVEL TRAIN / TEST SPLIT")
print("=" * 70)


projects = df["Project_ID"].unique()

rng = np.random.RandomState(42)

rng.shuffle(projects)


split_index = int(
    len(projects) * 0.80
)


train_projects = projects[:split_index]

test_projects = projects[split_index:]


train_mask = df["Project_ID"].isin(
    train_projects
)

test_mask = df["Project_ID"].isin(
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
    "Training tasks   :",
    len(X_train)
)

print(
    "Testing tasks    :",
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
# TRAIN CATBOOST
# ============================================================

print("\n" + "=" * 70)
print("TRAINING TAWOS PHASE 1 CATBOOST")
print("=" * 70)


model = CatBoostClassifier(

    depth=6,

    learning_rate=0.05,

    iterations=700,

    l2_leaf_reg=5,

    loss_function="MultiClass",

    eval_metric="Accuracy",

    random_seed=42,

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
print("TAWOS PHASE 1 MODEL PERFORMANCE")
print("=" * 70)


y_pred = model.predict(
    X_test
).ravel()


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
print("TAWOS PHASE 1 TRAINING COMPLETE")
print("=" * 70)

print("\nModel saved as:")
print(MODEL_PATH)

print("\nFeature importance saved as:")
print(IMPORTANCE_PATH)