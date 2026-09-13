import joblib
import pandas as pd

from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "catboost_ver2_model.pkl"
DATASET_PATH = BASE_DIR / "project_risk_final_clean.csv"


# ============================================================
# LOAD MODEL + DATASET
# ============================================================

print("=" * 70)
print("ANALYZING INITIAL CATBOOST MODEL")
print("=" * 70)

model = joblib.load(MODEL_PATH)
df = pd.read_csv(DATASET_PATH)


# ============================================================
# MODEL FEATURES
# ============================================================

model_features = list(model.feature_names_)

print("\n" + "=" * 70)
print("1. MODEL FEATURES")
print("=" * 70)

print("Number of features:", len(model_features))

for i, feature in enumerate(model_features, start=1):
    print(f"{i:2}. {feature}")


# ============================================================
# DATASET INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("2. DATASET INFORMATION")
print("=" * 70)

print("Rows    :", len(df))
print("Columns :", len(df.columns))


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("3. RISK LEVEL DISTRIBUTION")
print("=" * 70)

risk_counts = df["Risk_Level"].value_counts()
risk_percent = df["Risk_Level"].value_counts(normalize=True) * 100

for risk in risk_counts.index:

    print(
        f"{risk:10} : "
        f"{risk_counts[risk]:4} projects "
        f"({risk_percent[risk]:.2f}%)"
    )


# ============================================================
# CHECK FOR MISSING VALUES
# ============================================================

print("\n" + "=" * 70)
print("4. MISSING VALUES IN MODEL FEATURES")
print("=" * 70)

missing = df[model_features].isnull().sum()

missing = missing[missing > 0]

if len(missing) == 0:

    print("No missing values.")

else:

    for feature, count in missing.items():

        percentage = count / len(df) * 100

        print(
            f"{feature:40} : "
            f"{count} ({percentage:.2f}%)"
        )


# ============================================================
# PREPARE DATA FOR PREDICTION
# ============================================================

X = df[model_features].copy()
y = df["Risk_Level"].copy()


categorical_columns = X.select_dtypes(
    include=["object"]
).columns

for column in categorical_columns:

    X[column] = (
        X[column]
        .fillna("Unknown")
        .astype(str)
    )


# ============================================================
# MODEL PREDICTIONS
# ============================================================

print("\n" + "=" * 70)
print("5. MODEL PREDICTIONS ON FULL DATASET")
print("=" * 70)

predictions = model.predict(X)

predicted_classes = predictions.ravel()


# ============================================================
# PREDICTION DISTRIBUTION
# ============================================================

prediction_counts = pd.Series(
    predicted_classes
).value_counts()

prediction_percent = pd.Series(
    predicted_classes
).value_counts(normalize=True) * 100


for risk in model.classes_:

    count = prediction_counts.get(risk, 0)
    percentage = prediction_percent.get(risk, 0)

    print(
        f"{risk:10} : "
        f"{count:4} predictions "
        f"({percentage:.2f}%)"
    )


# ============================================================
# TRAINING-DATA ACCURACY
# ============================================================

accuracy = accuracy_score(
    y,
    predicted_classes
)

print("\nFull-dataset accuracy:")
print(f"{accuracy * 100:.2f}%")


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "=" * 70)
print("6. CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y,
        predicted_classes
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print("\n" + "=" * 70)
print("7. CONFUSION MATRIX")
print("=" * 70)

matrix = confusion_matrix(
    y,
    predicted_classes,
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
print("8. FEATURE IMPORTANCE")
print("=" * 70)

importance = model.get_feature_importance()

importance_df = pd.DataFrame({
    "Feature": model_features,
    "Importance": importance
})

importance_df = importance_df.sort_values(
    "Importance",
    ascending=False
)

for _, row in importance_df.iterrows():

    print(
        f"{row['Feature']:40} "
        f"{row['Importance']:.4f}"
    )


# ============================================================
# SAVE FEATURE IMPORTANCE
# ============================================================

importance_path = (
    BASE_DIR / "initial_feature_importance.csv"
)

importance_df.to_csv(
    importance_path,
    index=False
)


# ============================================================
# PROBABILITY ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("9. PREDICTION CONFIDENCE")
print("=" * 70)

probabilities = model.predict_proba(X)

max_probabilities = probabilities.max(axis=1)

print(
    "Average maximum probability : "
    f"{max_probabilities.mean() * 100:.2f}%"
)

print(
    "Minimum maximum probability : "
    f"{max_probabilities.min() * 100:.2f}%"
)

print(
    "Maximum maximum probability : "
    f"{max_probabilities.max() * 100:.2f}%"
)


# ============================================================
# MEDIUM PREDICTION ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("10. MEDIUM PREDICTION ANALYSIS")
print("=" * 70)

medium_mask = (
    predicted_classes == "Medium"
)

medium_count = medium_mask.sum()

print(
    "Projects predicted Medium:",
    medium_count
)

print(
    "Percentage predicted Medium:",
    f"{medium_count / len(df) * 100:.2f}%"
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

print(
    "\nFeature importance saved to:"
)

print(importance_path)