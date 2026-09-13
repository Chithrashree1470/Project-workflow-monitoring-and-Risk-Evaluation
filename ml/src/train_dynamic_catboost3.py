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
    BASE_DIR
    / "dynamic_catboost_v3_model.pkl"
)

IMPORTANCE_PATH = (
    BASE_DIR
    / "dynamic_feature_importance_v3.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("DYNAMIC PROJECT RISK - CATBOOST V3")
print("=" * 70)


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading V3 dynamic dataset...")

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
).reset_index(drop=True)

print("Usable rows :", len(df))
print("Projects    :", df["project_id"].nunique())


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
# CATEGORICAL FEATURES
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
# V2 weighting helped accuracy compared with the unweighted
# baseline, but excessive weighting can hurt overall accuracy.
#
# V3 uses moderate weights.
# ============================================================

CLASS_WEIGHTS = {

    "Critical": 1.00,
    "High": 1.05,
    "Low": 0.95,
    "Medium": 1.05
}


print("\nClass weights:")

for label, weight in CLASS_WEIGHTS.items():

    print(
        f" {label:10} : {weight}"
    )


# ============================================================
# TRAINING
# ============================================================

print("\n" + "=" * 70)
print("TRAINING DYNAMIC CATBOOST V3")
print("=" * 70)


model = CatBoostClassifier(

    # Slightly shallower trees to reduce overfitting
    depth=5,

    # Smaller learning rate
    learning_rate=0.04,

    # More iterations to compensate for lower learning rate
    iterations=1200,

    # Regularization
    l2_leaf_reg=7,

    loss_function="MultiClass",

    # We care about balanced class performance
    eval_metric="TotalF1",

    random_seed=42,

    class_weights=[
        CLASS_WEIGHTS["Critical"],
        CLASS_WEIGHTS["High"],
        CLASS_WEIGHTS["Low"],
        CLASS_WEIGHTS["Medium"]
    ],

    cat_features=cat_features,

    # Reduce console output
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
).reset_index(drop=True)


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
print("DYNAMIC CATBOOST V3 TRAINING COMPLETE")
print("=" * 70)

print("\nModel saved as:")
print(MODEL_PATH)

print("\nFeature importance saved as:")
print(IMPORTANCE_PATH)