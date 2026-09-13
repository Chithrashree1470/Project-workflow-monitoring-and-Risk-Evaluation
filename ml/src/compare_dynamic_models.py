import pandas as pd
import numpy as np

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
DATASET_DIR = BASE_DIR.parent.parent / "dataset"

V2_PATH = DATASET_DIR / "dynamic_training_dataset_v2.csv"
V3_PATH = DATASET_DIR / "dynamic_training_dataset_v3.csv"


# ============================================================
# CONFIG
# ============================================================

TARGET = "dynamic_risk_level"
PROJECT_ID = "project_id"

RANDOM_STATE = 42
TEST_PROJECT_RATIO = 0.20

MODEL_PARAMS = {
    "depth": 6,
    "learning_rate": 0.1,
    "iterations": 700,
    "l2_leaf_reg": 3,
    "loss_function": "MultiClass",
    "eval_metric": "Accuracy",
    "random_seed": RANDOM_STATE,
    "verbose": 200
}


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("DYNAMIC CATBOOST V2 vs V3 COMPARISON")
print("=" * 70)

print("\nLoading datasets...")

v2 = pd.read_csv(V2_PATH)
v3 = pd.read_csv(V3_PATH)

print("\nV2:")
print("Rows    :", len(v2))
print("Projects:", v2[PROJECT_ID].nunique())
print("Columns :", len(v2.columns))

print("\nV3:")
print("Rows    :", len(v3))
print("Projects:", v3[PROJECT_ID].nunique())
print("Columns :", len(v3.columns))


# ============================================================
# COMMON PROJECTS
# ============================================================

common_projects = sorted(
    set(v2[PROJECT_ID])
    &
    set(v3[PROJECT_ID])
)

print("\nCommon projects:", len(common_projects))

v2 = v2[
    v2[PROJECT_ID].isin(common_projects)
].copy()

v3 = v3[
    v3[PROJECT_ID].isin(common_projects)
].copy()


# ============================================================
# SAME PROJECT-LEVEL TRAIN / TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("COMMON PROJECT-LEVEL TRAIN / TEST SPLIT")
print("=" * 70)

rng = np.random.RandomState(
    RANDOM_STATE
)

projects = np.array(
    common_projects
)

rng.shuffle(projects)

test_count = int(
    len(projects) *
    TEST_PROJECT_RATIO
)

test_projects = set(
    projects[:test_count]
)

train_projects = set(
    projects[test_count:]
)

print(
    "Training projects:",
    len(train_projects)
)

print(
    "Testing projects :",
    len(test_projects)
)


# ============================================================
# SPLIT DATASETS
# ============================================================

def split_dataset(df):

    train = df[
        df[PROJECT_ID].isin(
            train_projects
        )
    ].copy()

    test = df[
        df[PROJECT_ID].isin(
            test_projects
        )
    ].copy()

    return train, test


v2_train, v2_test = split_dataset(v2)
v3_train, v3_test = split_dataset(v3)

print("\nV2 train snapshots:", len(v2_train))
print("V2 test snapshots :", len(v2_test))

print("\nV3 train snapshots:", len(v3_train))
print("V3 test snapshots :", len(v3_test))


# ============================================================
# FEATURE SELECTION
# ============================================================

def get_features(df):

    excluded = {
        PROJECT_ID,
        "snapshot_date",
        "future_completed_30d",
        "future_delayed_30d",
        "future_delayed_rate",
        TARGET
    }

    return [
        column
        for column in df.columns
        if column not in excluded
    ]


v2_features = get_features(v2)
v3_features = get_features(v3)

print("\n" + "=" * 70)
print("FEATURE COUNTS")
print("=" * 70)

print(
    "V2 features:",
    len(v2_features)
)

print(
    "V3 features:",
    len(v3_features)
)


# ============================================================
# TRAIN / EVALUATE FUNCTION
# ============================================================

def train_and_evaluate(
    train_df,
    test_df,
    features,
    version
):

    print("\n" + "=" * 70)
    print(f"TRAINING {version}")
    print("=" * 70)

    X_train = train_df[
        features
    ].copy()

    y_train = train_df[
        TARGET
    ]

    X_test = test_df[
        features
    ].copy()

    y_test = test_df[
        TARGET
    ]

    # --------------------------------------------------------
    # Handle categorical features
    # --------------------------------------------------------

    categorical_columns = (
        X_train
        .select_dtypes(
            include=["object"]
        )
        .columns
        .tolist()
    )

    for column in categorical_columns:

        X_train[column] = (
            X_train[column]
            .astype(str)
        )

        X_test[column] = (
            X_test[column]
            .astype(str)
        )

    cat_features = [
        X_train.columns.get_loc(
            column
        )
        for column in categorical_columns
    ]

    print(
        "\nCategorical features:",
        len(cat_features)
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = CatBoostClassifier(
        **MODEL_PARAMS,
        cat_features=cat_features
    )

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

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

    report = classification_report(
        y_test,
        y_pred
    )

    matrix = confusion_matrix(
        y_test,
        y_pred,
        labels=[
            "Critical",
            "High",
            "Low",
            "Medium"
        ]
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print(f"{version} PERFORMANCE")
    print("=" * 70)

    print(
        f"\nAccuracy : {accuracy * 100:.2f}%"
    )

    print(
        f"Macro F1 : {macro_f1:.4f}"
    )

    print(
        f"Weighted F1 : {weighted_f1:.4f}"
    )

    print("\nClassification report:")
    print(report)

    print("Confusion matrix:")
    print(
        pd.DataFrame(
            matrix,
            index=[
                "Actual Critical",
                "Actual High",
                "Actual Low",
                "Actual Medium"
            ],
            columns=[
                "Pred Critical",
                "Pred High",
                "Pred Low",
                "Pred Medium"
            ]
        )
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance = pd.DataFrame({
        "Feature": features,
        "Importance": model.get_feature_importance()
    })

    importance = (
        importance
        .sort_values(
            "Importance",
            ascending=False
        )
        .reset_index(drop=True)
    )

    print("\nTop 15 features:")

    print(
        importance.head(15).to_string(
            index=False
        )
    )

    return {
        "model": model,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "report": report,
        "matrix": matrix,
        "importance": importance
    }


# ============================================================
# TRAIN V2
# ============================================================

v2_result = train_and_evaluate(
    v2_train,
    v2_test,
    v2_features,
    "V2"
)


# ============================================================
# TRAIN V3
# ============================================================

v3_result = train_and_evaluate(
    v3_train,
    v3_test,
    v3_features,
    "V3"
)


# ============================================================
# FINAL COMPARISON
# ============================================================

print("\n" + "=" * 70)
print("V2 vs V3 PERFORMANCE")
print("=" * 70)

comparison = pd.DataFrame({

    "Metric": [
        "Accuracy",
        "Macro F1",
        "Weighted F1"
    ],

    "V2": [
        v2_result["accuracy"],
        v2_result["macro_f1"],
        v2_result["weighted_f1"]
    ],

    "V3": [
        v3_result["accuracy"],
        v3_result["macro_f1"],
        v3_result["weighted_f1"]
    ]

})

comparison["V2"] = comparison["V2"].apply(
    lambda x: (
        f"{x * 100:.2f}%"
        if "Accuracy" in comparison.loc[
            comparison["V2"].astype(str) == str(x),
            "Metric"
        ].values
        else f"{x:.4f}"
    )
)

# Print clean comparison separately
print("\nMetric                    V2          V3")
print("-" * 55)

print(
    f"Accuracy              "
    f"{v2_result['accuracy'] * 100:>7.2f}%   "
    f"{v3_result['accuracy'] * 100:>7.2f}%"
)

print(
    f"Macro F1              "
    f"{v2_result['macro_f1']:>10.4f}   "
    f"{v3_result['macro_f1']:>10.4f}"
)

print(
    f"Weighted F1           "
    f"{v2_result['weighted_f1']:>10.4f}   "
    f"{v3_result['weighted_f1']:>10.4f}"
)


# ============================================================
# IMPROVEMENT
# ============================================================

accuracy_change = (
    v3_result["accuracy"]
    -
    v2_result["accuracy"]
)

macro_f1_change = (
    v3_result["macro_f1"]
    -
    v2_result["macro_f1"]
)

weighted_f1_change = (
    v3_result["weighted_f1"]
    -
    v2_result["weighted_f1"]
)

print("\n" + "=" * 70)
print("V3 IMPROVEMENT")
print("=" * 70)

print(
    f"Accuracy change   : "
    f"{accuracy_change * 100:+.2f} percentage points"
)

print(
    f"Macro F1 change   : "
    f"{macro_f1_change:+.4f}"
)

print(
    f"Weighted F1 change: "
    f"{weighted_f1_change:+.4f}"
)


# ============================================================
# DECISION
# ============================================================

print("\n" + "=" * 70)
print("PRELIMINARY DECISION")
print("=" * 70)

if (
    v3_result["macro_f1"] >
    v2_result["macro_f1"]
    and
    v3_result["accuracy"] >
    v2_result["accuracy"]
):

    print(
        "V3 performs better than V2 "
        "on both Accuracy and Macro F1."
    )

elif (
    v3_result["macro_f1"] >
    v2_result["macro_f1"]
):

    print(
        "V3 improves Macro F1, "
        "but does not improve Accuracy."
    )

else:

    print(
        "V3 does not improve Macro F1 "
        "over V2."
    )


print("\n" + "=" * 70)
print("COMPARISON COMPLETE")
print("=" * 70)