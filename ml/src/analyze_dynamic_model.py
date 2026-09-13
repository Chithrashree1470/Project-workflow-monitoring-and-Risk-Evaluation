import pandas as pd
import numpy as np
import joblib
import sys

from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)

from sklearn.tree import DecisionTreeClassifier


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR.parent.parent
    / "dataset"
    / "dynamic_tawos_training_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "dynamic_tawos_catboost_model.pkl"
)

OUTPUT_PATH = (
    BASE_DIR
    / "dynamic_tawos_model_analysis.txt"
)


# ============================================================
# TEE OUTPUT
# ============================================================

class Tee:

    def __init__(self, terminal, file):

        self.terminal = terminal
        self.file = file

    def write(self, message):

        self.terminal.write(message)
        self.file.write(message)

    def flush(self):

        self.terminal.flush()
        self.file.flush()


log_file = open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8"
)

original_stdout = sys.stdout

sys.stdout = Tee(
    original_stdout,
    log_file
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("TAWOS DYNAMIC CATBOOST MODEL ANALYSIS")
print("=" * 70)


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading TAWOS dynamic dataset...")

df = pd.read_csv(
    DATASET_PATH,
    low_memory=False
)

print("Rows    :", len(df))
print("Columns :", len(df.columns))
print("Projects:", df["project_id"].nunique())
print("Tasks   :", df["issue_id"].nunique())


print("\nDetected columns:")
print(df.columns.tolist())


# ============================================================
# LOAD MODEL
# ============================================================

print("\n" + "=" * 70)
print("LOADING MODEL")
print("=" * 70)

model = joblib.load(
    MODEL_PATH
)

print("\nModel loaded:")
print(MODEL_PATH)

print("\nModel classes:")
print(model.classes_)


# ============================================================
# TARGET / FEATURES
# ============================================================

TARGET = "task_risk_level"


EXCLUDED_COLUMNS = [

    "project_id",
    "issue_id",
    "issue_key",
    "snapshot_date",

    # Future outcome
    "delay_days",

    # Target
    TARGET
]


FEATURES = [
    column
    for column in df.columns
    if column not in EXCLUDED_COLUMNS
]


X = df[FEATURES].copy()

y = df[TARGET].copy()


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


print("\nModel features:", len(FEATURES))

for feature in FEATURES:

    print(" ✓", feature)


print(
    "\nCategorical features:",
    categorical_columns
)


# ============================================================
# PROJECT-LEVEL TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("RECREATING PROJECT-LEVEL TEST SPLIT")
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


train_df = df.loc[
    train_mask
].copy()


test_df = df.loc[
    test_mask
].copy()


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
# VERIFY PROJECT LEAKAGE
# ============================================================

print("\n" + "=" * 70)
print("PROJECT SPLIT LEAKAGE CHECK")
print("=" * 70)


train_project_set = set(
    train_projects
)

test_project_set = set(
    test_projects
)


project_overlap = (
    train_project_set
    &
    test_project_set
)


print(
    "Projects appearing in both train/test:",
    len(project_overlap)
)


if len(project_overlap) == 0:

    print(
        "✓ No project-level leakage detected."
    )

else:

    print(
        "!!! PROJECT LEAKAGE DETECTED !!!"
    )

    print(
        project_overlap
    )


# ============================================================
# VERIFY TASK LEAKAGE
# ============================================================

print("\n" + "=" * 70)
print("TASK-LEVEL LEAKAGE CHECK")
print("=" * 70)


train_task_set = set(
    train_df["issue_id"]
)

test_task_set = set(
    test_df["issue_id"]
)


task_overlap = (
    train_task_set
    &
    test_task_set
)


print(
    "Tasks appearing in both train/test:",
    len(task_overlap)
)


if len(task_overlap) == 0:

    print(
        "✓ No task-level leakage detected."
    )

else:

    print(
        "!!! TASK-LEVEL LEAKAGE DETECTED !!!"
    )


# ============================================================
# GENERATE PREDICTIONS
# ============================================================

print("\n" + "=" * 70)
print("GENERATING PREDICTIONS")
print("=" * 70)


y_pred = model.predict(
    X_test
).ravel()


probabilities = model.predict_proba(
    X_test
)


class_names = list(
    model.classes_
)


# ============================================================
# BASIC PERFORMANCE
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


print("\n" + "=" * 70)
print("MODEL PERFORMANCE")
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


print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        labels=class_names,
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
    labels=class_names
)


matrix_df = pd.DataFrame(
    matrix,
    index=[
        f"Actual {c}"
        for c in class_names
    ],
    columns=[
        f"Predicted {c}"
        for c in class_names
    ]
)


print(matrix_df)


# ============================================================
# PREDICTION DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("PREDICTION DISTRIBUTION")
print("=" * 70)


actual_distribution = (
    y_test
    .value_counts()
    .reindex(class_names)
)


prediction_distribution = (
    pd.Series(y_pred)
    .value_counts()
    .reindex(class_names)
    .fillna(0)
)


distribution_df = pd.DataFrame({

    "Actual":
        actual_distribution,

    "Predicted":
        prediction_distribution

})


distribution_df["Actual %"] = (
    distribution_df["Actual"]
    /
    len(y_test)
    *
    100
)


distribution_df["Predicted %"] = (
    distribution_df["Predicted"]
    /
    len(y_test)
    *
    100
)


print(
    distribution_df
)


# ============================================================
# CONFIDENCE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("CONFIDENCE ANALYSIS")
print("=" * 70)


max_probability = (
    probabilities.max(axis=1)
)


sorted_probabilities = np.sort(
    probabilities,
    axis=1
)


confidence_margin = (
    sorted_probabilities[:, -1]
    -
    sorted_probabilities[:, -2]
)


print(
    f"\nAverage maximum probability: "
    f"{max_probability.mean() * 100:.2f}%"
)


print(
    f"Median maximum probability : "
    f"{np.median(max_probability) * 100:.2f}%"
)


print(
    f"Minimum maximum probability: "
    f"{max_probability.min() * 100:.2f}%"
)


print(
    f"Maximum maximum probability: "
    f"{max_probability.max() * 100:.2f}%"
)


print(
    f"\nAverage probability margin: "
    f"{confidence_margin.mean() * 100:.2f}%"
)


# ============================================================
# CONFIDENCE BUCKETS
# ============================================================

print("\nConfidence buckets:")


confidence_buckets = pd.cut(

    max_probability,

    bins=[
        0,
        0.40,
        0.50,
        0.60,
        0.70,
        0.80,
        0.90,
        1.00
    ],

    labels=[
        "<40%",
        "40-50%",
        "50-60%",
        "60-70%",
        "70-80%",
        "80-90%",
        "90-100%"
    ],

    include_lowest=True
)


confidence_table = (

    pd.DataFrame({

        "confidence":
            confidence_buckets,

        "correct":
            y_test.to_numpy()
            == y_pred

    })

    .groupby(
        "confidence",
        observed=False
    )

    .agg(

        predictions=(
            "correct",
            "count"
        ),

        correct=(
            "correct",
            "sum"
        )

    )

)


confidence_table["accuracy"] = (
    confidence_table["correct"]
    /
    confidence_table["predictions"]
    *
    100
)


print(
    confidence_table
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)


importance = (
    model.get_feature_importance()
)


importance_df = pd.DataFrame({

    "Feature":
        FEATURES,

    "Importance":
        importance

})


importance_df = (
    importance_df
    .sort_values(
        "Importance",
        ascending=False
    )
)


print(
    importance_df.to_string(
        index=False
    )
)


# ============================================================
# SUSPICIOUS FEATURE ANALYSIS
# ============================================================
#
# These features are particularly suspicious because they
# describe where the snapshot occurs in the task lifetime.
# ============================================================

print("\n" + "=" * 70)
print("SUSPICIOUS TEMPORAL FEATURE ANALYSIS")
print("=" * 70)


SUSPICIOUS_FEATURES = [

    "snapshot_number",

    "task_age_days",

    "days_until_estimation",

    "estimated_duration_days",

    "age_to_estimation_ratio",

    "timespent_to_estimation_ratio"

]


available_suspicious = [

    feature

    for feature in SUSPICIOUS_FEATURES

    if feature in df.columns

]


print(
    "\nSuspicious features found:"
)


for feature in available_suspicious:

    print(
        " ✓",
        feature
    )


# ============================================================
# TARGET CORRELATION
# ============================================================
#
# Since the target is categorical, use the actual numerical
# delay as the reference for this diagnostic.
#
# This does NOT mean delay_days is a model feature.
# ============================================================

print("\n" + "=" * 70)
print("FEATURE vs FINAL DELAY CORRELATION")
print("=" * 70)


numeric_features = [

    feature

    for feature in available_suspicious

    if pd.api.types.is_numeric_dtype(
        df[feature]
    )
]


correlation_results = []


for feature in numeric_features:

    correlation = (
        df[feature]
        .corr(
            df["delay_days"]
        )
    )

    correlation_results.append({

        "Feature": feature,

        "Correlation with final delay":
            correlation

    })


correlation_df = pd.DataFrame(
    correlation_results
)


if not correlation_df.empty:

    correlation_df = (
        correlation_df
        .sort_values(
            "Correlation with final delay",
            key=lambda x: x.abs(),
            ascending=False
        )
    )


    print(
        correlation_df.to_string(
            index=False
        )
    )


# ============================================================
# SINGLE-FEATURE LEAKAGE TEST
# ============================================================
#
# A shallow decision tree is deliberately used here.
#
# If one suspicious feature by itself predicts the final
# target extremely well, that is strong evidence that the
# feature contains information about the eventual outcome.
# ============================================================

print("\n" + "=" * 70)
print("SINGLE-FEATURE LEAKAGE TEST")
print("=" * 70)


single_feature_results = []


for feature in available_suspicious:

    if not pd.api.types.is_numeric_dtype(
        df[feature]
    ):

        continue


    feature_train = (
        train_df[[feature]]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )


    feature_test = (
        test_df[[feature]]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )


    single_model = DecisionTreeClassifier(

        max_depth=3,

        random_state=42

    )


    single_model.fit(
        feature_train,
        y_train
    )


    single_pred = (
        single_model
        .predict(feature_test)
    )


    single_accuracy = (
        accuracy_score(
            y_test,
            single_pred
        )
    )


    single_feature_results.append({

        "Feature":
            feature,

        "Accuracy":
            single_accuracy * 100

    })


single_feature_df = pd.DataFrame(
    single_feature_results
)


if not single_feature_df.empty:

    single_feature_df = (
        single_feature_df
        .sort_values(
            "Accuracy",
            ascending=False
        )
    )


    print(
        single_feature_df.to_string(
            index=False
        )
    )


# ============================================================
# TARGET BY SNAPSHOT NUMBER
# ============================================================

if "snapshot_number" in df.columns:

    print("\n" + "=" * 70)
    print("RISK DISTRIBUTION BY SNAPSHOT NUMBER")
    print("=" * 70)


    snapshot_risk = pd.crosstab(

        df["snapshot_number"],

        df[TARGET],

        normalize="index"

    ) * 100


    print(
        snapshot_risk.round(2)
    )


# ============================================================
# TARGET BY TASK AGE
# ============================================================

if "task_age_days" in df.columns:

    print("\n" + "=" * 70)
    print("RISK DISTRIBUTION BY TASK AGE")
    print("=" * 70)


    age_bins = pd.qcut(

        df["task_age_days"],

        q=10,

        duplicates="drop"

    )


    age_risk = pd.crosstab(

        age_bins,

        df[TARGET],

        normalize="index"

    ) * 100


    print(
        age_risk.round(2)
    )


# ============================================================
# MOST UNCERTAIN PREDICTIONS
# ============================================================

print("\n" + "=" * 70)
print("MOST UNCERTAIN PREDICTIONS")
print("=" * 70)


uncertain_indices = np.argsort(
    confidence_margin
)[:20]


uncertain_df = test_df.iloc[
    uncertain_indices
].copy()


uncertain_df["actual_risk"] = (
    y_test.iloc[
        uncertain_indices
    ].to_numpy()
)


uncertain_df["predicted_risk"] = (
    y_pred[
        uncertain_indices
    ]
)


uncertain_df["confidence"] = (
    max_probability[
        uncertain_indices
    ]
    *
    100
)


uncertain_df["margin"] = (
    confidence_margin[
        uncertain_indices
    ]
    *
    100
)


uncertain_columns = [

    "project_id",
    "issue_id",
    "snapshot_date",
    "snapshot_number",
    "task_age_days",
    "days_until_estimation",
    "actual_risk",
    "predicted_risk",
    "confidence",
    "margin"

]


uncertain_columns = [

    column

    for column in uncertain_columns

    if column in uncertain_df.columns

]


print(
    uncertain_df[
        uncertain_columns
    ].to_string(
        index=False
    )
)


# ============================================================
# FINAL DIAGNOSTIC SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("LEAKAGE DIAGNOSTIC SUMMARY")
print("=" * 70)


print(
    f"\nModel accuracy: "
    f"{accuracy * 100:.2f}%"
)


print(
    f"Macro F1: "
    f"{macro_f1:.4f}"
)


print(
    f"Weighted F1: "
    f"{weighted_f1:.4f}"
)


print(
    "\nProject overlap:",
    len(project_overlap)
)


print(
    "Task overlap:",
    len(task_overlap)
)


if not correlation_df.empty:

    print(
        "\nCorrelation with final delay:"
    )

    for _, row in correlation_df.iterrows():

        print(
            f" {row['Feature']:35} "
            f"{row['Correlation with final delay']:.4f}"
        )


if not single_feature_df.empty:

    print(
        "\nSingle-feature prediction accuracy:"
    )

    for _, row in single_feature_df.iterrows():

        print(
            f" {row['Feature']:35} "
            f"{row['Accuracy']:.2f}%"
        )


# ============================================================
# INTERPRETATION FLAGS
# ============================================================

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)


if len(task_overlap) > 0:

    print(
        "\n!!! TASK LEAKAGE EXISTS."
    )

    print(
        "The same task appears in both train and test."
    )

else:

    print(
        "\n✓ No task-level train/test overlap."
    )


if len(project_overlap) > 0:

    print(
        "!!! PROJECT LEAKAGE EXISTS."
    )

else:

    print(
        "✓ No project-level train/test overlap."
    )


if not single_feature_df.empty:

    suspicious_high = (
        single_feature_df[
            single_feature_df["Accuracy"] >= 70
        ]
    )


    if len(suspicious_high) > 0:

        print(
            "\n!!! STRONG LEAKAGE WARNING"
        )

        print(
            "At least one suspicious temporal feature "
            "achieves >=70% accuracy by itself:"
        )


        for _, row in suspicious_high.iterrows():

            print(
                f"  {row['Feature']} : "
                f"{row['Accuracy']:.2f}%"
            )

    else:

        print(
            "\nNo suspicious temporal feature "
            "alone exceeds 70% accuracy."
        )


print(
    "\nDo NOT judge the 94% model as valid until "
    "the temporal leakage diagnostics are reviewed."
)


# ============================================================
# RESTORE STDOUT / CLOSE FILE
# ============================================================

sys.stdout = original_stdout

log_file.close()


print("\nAnalysis saved to:")
print(OUTPUT_PATH)