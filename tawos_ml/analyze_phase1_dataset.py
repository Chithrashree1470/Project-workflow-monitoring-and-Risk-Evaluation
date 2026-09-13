import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score
from sklearn.feature_selection import mutual_info_classif
from catboost import CatBoostClassifier

import matplotlib.pyplot as plt


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "tawos_phase1_history_dataset.csv"

OUTPUT_DIR = BASE_DIR / "analysis"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("TAWOS PHASE 1 - EDA / LEAKAGE ANALYSIS")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(
    DATA_PATH,
    low_memory=False
)

print("Rows    :", len(df))
print("Columns :", len(df.columns))

print("\nColumns:")
for col in df.columns:
    print(" ✓", col)


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("1. BASIC INFORMATION")
print("=" * 70)

print("Projects :", df["project_id"].nunique())
print("Issues   :", df["issue_id"].nunique())
print("Snapshots:", len(df))

print("\nTarget distribution:")
print(df["task_risk_level"].value_counts())

print("\nTarget percentages:")
print(
    (
        df["task_risk_level"]
        .value_counts(normalize=True)
        * 100
    ).round(2)
)


# ============================================================
# TARGET ENCODING
# ============================================================

target_order = {
    "Low": 0,
    "Medium": 1,
    "High": 2,
    "Critical": 3
}

df["risk_numeric"] = (
    df["task_risk_level"]
    .map(target_order)
)


# ============================================================
# 2. TASK AGE VS RISK
# ============================================================

print("\n" + "=" * 70)
print("2. TASK AGE VS FINAL RISK")
print("=" * 70)

print("\nCorrelation:")

age_corr = df[
    ["task_age_days", "risk_numeric"]
].corr().iloc[0, 1]

print(
    f"task_age_days vs risk_numeric: "
    f"{age_corr:.4f}"
)


print("\nTask age by risk:")

age_by_risk = (
    df.groupby("task_risk_level")[
        "task_age_days"
    ]
    .agg(
        [
            "count",
            "mean",
            "median",
            "min",
            "max"
        ]
    )
)

print(age_by_risk)


# ============================================================
# AGE BINS
# ============================================================

print("\nRisk distribution by task age:")

df["age_bin"] = pd.cut(
    df["task_age_days"],
    bins=[
        -0.001,
        1,
        3,
        7,
        14,
        30,
        90,
        np.inf
    ],
    labels=[
        "0-1",
        "1-3",
        "3-7",
        "7-14",
        "14-30",
        "30-90",
        "90+"
    ]
)

age_risk = pd.crosstab(
    df["age_bin"],
    df["task_risk_level"],
    normalize="index"
) * 100

print(
    age_risk.round(2)
)


# ============================================================
# PLOT AGE VS RISK
# ============================================================

plt.figure(figsize=(10, 6))

for risk in [
    "Low",
    "Medium",
    "High",
    "Critical"
]:

    subset = df[
        df["task_risk_level"] == risk
    ]

    plt.hist(
        subset["task_age_days"],
        bins=50,
        alpha=0.4,
        label=risk
    )

plt.xlabel("Task Age (days)")
plt.ylabel("Number of Snapshots")
plt.title("Task Age Distribution by Risk")
plt.legend()
plt.tight_layout()

age_plot = (
    OUTPUT_DIR /
    "age_vs_risk.png"
)

plt.savefig(age_plot)
plt.close()

print(
    "\nSaved:",
    age_plot
)


# ============================================================
# 3. AGE-ONLY BASELINE
# ============================================================

print("\n" + "=" * 70)
print("3. AGE-ONLY PREDICTION TEST")
print("=" * 70)

age_data = df[
    [
        "task_age_days",
        "task_risk_level"
    ]
].dropna()

X_age = age_data[
    ["task_age_days"]
]

y_age = age_data[
    "task_risk_level"
]

X_train, X_test, y_train, y_test = train_test_split(
    X_age,
    y_age,
    test_size=0.2,
    random_state=42,
    stratify=y_age
)

age_model = CatBoostClassifier(
    iterations=300,
    depth=5,
    learning_rate=0.05,
    loss_function="MultiClass",
    verbose=False,
    random_seed=42
)

age_model.fit(
    X_train,
    y_train
)

age_pred = age_model.predict(X_test).ravel()

age_accuracy = accuracy_score(
    y_test,
    age_pred
)

age_macro_f1 = f1_score(
    y_test,
    age_pred,
    average="macro"
)

print(
    f"\nAge-only accuracy : "
    f"{age_accuracy * 100:.2f}%"
)

print(
    f"Age-only Macro F1 : "
    f"{age_macro_f1:.4f}"
)


# ============================================================
# 4. HISTORICAL FEATURE ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("4. HISTORICAL FEATURE ANALYSIS")
print("=" * 70)

numeric_features = [

    "task_age_days",
    "story_points",
    "timespent",

    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days"
]


print("\nCorrelation with risk:")

correlations = {}

for feature in numeric_features:

    corr = df[
        [feature, "risk_numeric"]
    ].corr().iloc[0, 1]

    correlations[feature] = corr

    print(
        f"{feature:30s}: "
        f"{corr:.4f}"
    )


# ============================================================
# FEATURE STATISTICS BY CLASS
# ============================================================

print("\nFeature medians by risk:")

median_table = (
    df.groupby("task_risk_level")[
        numeric_features
    ]
    .median()
    .T
)

print(
    median_table.round(3)
)


# ============================================================
# 5. PROJECT-LEVEL TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("5. TARGET DISTRIBUTION BY PROJECT")
print("=" * 70)

project_distribution = pd.crosstab(
    df["project_id"],
    df["task_risk_level"],
    normalize="index"
) * 100

print(
    project_distribution.round(2)
)


project_counts = (
    df.groupby("project_id")[
        "issue_id"
    ]
    .nunique()
    .sort_values(
        ascending=False
    )
)

print("\nIssues per project:")
print(project_counts)


# ============================================================
# PROJECT RISK PLOT
# ============================================================

project_distribution.plot(
    kind="bar",
    stacked=True,
    figsize=(12, 7)
)

plt.xlabel("Project")
plt.ylabel("Percentage")
plt.title("Risk Distribution by Project")
plt.tight_layout()

project_plot = (
    OUTPUT_DIR /
    "project_risk_distribution.png"
)

plt.savefig(project_plot)
plt.close()

print(
    "\nSaved:",
    project_plot
)


# ============================================================
# 6. SNAPSHOT #1 ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("6. SNAPSHOT #1 ANALYSIS")
print("=" * 70)

snapshot1 = df[
    df["snapshot_number"] == 1
].copy()

print(
    "Snapshot #1 rows    :",
    len(snapshot1)
)

print(
    "Snapshot #1 issues  :",
    snapshot1["issue_id"].nunique()
)

print("\nSnapshot #1 target distribution:")

print(
    snapshot1[
        "task_risk_level"
    ].value_counts()
)

print("\nSnapshot #1 percentages:")

print(
    (
        snapshot1[
            "task_risk_level"
        ]
        .value_counts(normalize=True)
        * 100
    ).round(2)
)


# ============================================================
# SNAPSHOT #1 MODEL
# ============================================================

snapshot_features = [

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


X = snapshot1[
    snapshot_features
].copy()

y = snapshot1[
    "task_risk_level"
]


categorical_features = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint"
]


for col in categorical_features:

    X[col] = (
        X[col]
        .fillna("Unknown")
        .astype(str)
    )


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


cat_indices = [
    X.columns.get_loc(col)
    for col in categorical_features
]


snapshot_model = CatBoostClassifier(
    iterations=500,
    depth=6,
    learning_rate=0.05,
    loss_function="MultiClass",
    verbose=False,
    random_seed=42
)

snapshot_model.fit(
    X_train,
    y_train,
    cat_features=cat_indices
)

snapshot_pred = (
    snapshot_model
    .predict(X_test)
    .ravel()
)


snapshot_accuracy = accuracy_score(
    y_test,
    snapshot_pred
)

snapshot_macro_f1 = f1_score(
    y_test,
    snapshot_pred,
    average="macro"
)


print(
    "\nSnapshot #1 accuracy : "
    f"{snapshot_accuracy * 100:.2f}%"
)

print(
    "Snapshot #1 Macro F1 : "
    f"{snapshot_macro_f1:.4f}"
)


# ============================================================
# 7. FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("7. FEATURE IMPORTANCE")
print("=" * 70)

importance = pd.DataFrame({

    "feature":
        snapshot_features,

    "importance":
        snapshot_model
        .get_feature_importance()
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


importance_file = (
    OUTPUT_DIR /
    "phase1_feature_importance.csv"
)

importance.to_csv(
    importance_file,
    index=False
)

print(
    "\nSaved:",
    importance_file
)


# ============================================================
# 8. MUTUAL INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("8. NUMERIC FEATURE INFORMATION")
print("=" * 70)

mi_features = [
    "task_age_days",
    "story_points",
    "story_points_missing",
    "timespent",
    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days"
]

mi_df = snapshot1[
    mi_features
].fillna(0)

label_encoder = LabelEncoder()

y_encoded = label_encoder.fit_transform(
    snapshot1[
        "task_risk_level"
    ]
)

mi_scores = mutual_info_classif(
    mi_df,
    y_encoded,
    random_state=42
)

mi_table = pd.DataFrame({

    "feature":
        mi_features,

    "mutual_information":
        mi_scores
}).sort_values(
    "mutual_information",
    ascending=False
)

print(
    mi_table.to_string(
        index=False
    )
)


mi_file = (
    OUTPUT_DIR /
    "phase1_mutual_information.csv"
)

mi_table.to_csv(
    mi_file,
    index=False
)


# ============================================================
# 9. LEAKAGE CHECK
# ============================================================

print("\n" + "=" * 70)
print("9. EXPLICIT LEAKAGE CHECK")
print("=" * 70)

forbidden = [

    "actual_duration_days",
    "task_risk_level",
    "issue_id",
    "issue_key",
    "project_id",
    "snapshot_date",
    "snapshot_number"
]


print(
    "\nColumns forbidden from model:"
)

for col in forbidden:

    if col in df.columns:

        print(
            " !",
            col
        )


print(
    "\nAllowed Phase 1 candidate features:"
)

for col in snapshot_features:

    print(
        " ✓",
        col
    )


# ============================================================
# 10. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("EDA / LEAKAGE ANALYSIS SUMMARY")
print("=" * 70)

print(
    f"\nAge-risk correlation : "
    f"{age_corr:.4f}"
)

print(
    f"Age-only accuracy    : "
    f"{age_accuracy * 100:.2f}%"
)

print(
    f"Age-only Macro F1    : "
    f"{age_macro_f1:.4f}"
)

print(
    f"Snapshot #1 accuracy : "
    f"{snapshot_accuracy * 100:.2f}%"
)

print(
    f"Snapshot #1 Macro F1 : "
    f"{snapshot_macro_f1:.4f}"
)

print("\nTop features:")

print(
    importance.head(10).to_string(
        index=False
    )
)

print("\nAnalysis files saved to:")

print(
    OUTPUT_DIR
)

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)