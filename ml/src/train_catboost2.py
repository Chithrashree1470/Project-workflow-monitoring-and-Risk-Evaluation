import pandas as pd
import joblib

from pathlib import Path
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "project_risk_final_clean.csv"
MODEL_PATH = BASE_DIR / "catboost_ver2_model.pkl"


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("INITIAL PROJECT RISK - CATBOOST")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print("Rows    :", len(df))
print("Columns :", len(df.columns))


# ============================================================
# INITIAL-PREDICTION FEATURES
# ============================================================
#
# These are features that should reasonably be available
# when the project is initially assessed.
#
# Execution-time information is deliberately excluded.
# ============================================================

initial_features = [

    "Project_Type",
    "Team_Size",
    "Project_Budget_USD",
    "Estimated_Timeline_Months",
    "Complexity_Score",
    "Stakeholder_Count",
    "Methodology_Used",

    "Team_Experience_Level",
    "Past_Similar_Projects",

    "External_Dependencies_Count",
    "Change_Request_Frequency",

    "Project_Phase",
    "Requirement_Stability",
    "Team_Turnover_Rate",
    "Vendor_Reliability_Score",
    "Historical_Risk_Incidents",
    "Communication_Frequency",

    "Regulatory_Compliance_Level",
    "Technology_Familiarity",
    "Geographical_Distribution",
    "Stakeholder_Engagement_Level",

    "Schedule_Pressure",
    "Executive_Sponsorship",
    "Funding_Source",
    "Market_Volatility",
    "Integration_Complexity",

    "Resource_Availability",
    "Priority_Level",
    "Organizational_Change_Frequency",
    "Cross_Functional_Dependencies",

    "Previous_Delivery_Success_Rate",
    "Technical_Debt_Level",
    "Project_Manager_Experience",
    "Org_Process_Maturity",

    "Data_Security_Requirements",
    "Key_Stakeholder_Availability",
    "Tech_Environment_Stability",

    "Contract_Type",
    "Resource_Contention_Level",
    "Industry_Volatility",
    "Client_Experience_Level",

    "Change_Control_Maturity",
    "Risk_Management_Maturity",
    "Team_Colocation",
    "Documentation_Quality",

    "Project_Start_Month",
    "Seasonal_Risk_Factor"
]


# ============================================================
# CHECK FEATURES
# ============================================================

missing_features = [
    col
    for col in initial_features
    if col not in df.columns
]

if missing_features:

    print("\nERROR: Missing required features:")

    for col in missing_features:
        print(" -", col)

    raise ValueError(
        "Some initial-model features are missing."
    )


# ============================================================
# TARGET
# ============================================================

target = "Risk_Level"

if target not in df.columns:
    raise ValueError(
        "Risk_Level column not found."
    )


# ============================================================
# CREATE X AND Y
# ============================================================

X = df[initial_features].copy()
y = df[target].copy()


print("\nInitial model features:", len(initial_features))

print("\nFeatures used:")

for feature in initial_features:
    print(" ✓", feature)


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

categorical_columns = X.select_dtypes(
    include=["object"]
).columns

for col in categorical_columns:
    X[col] = X[col].fillna("Unknown").astype(str)

cat_features = [
    X.columns.get_loc(col)
    for col in categorical_columns
]


print("\nCategorical features:", len(categorical_columns))


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================
#
# 80% → training
# 20% → testing
#
# stratify=y keeps the Risk_Level distribution similar
# in both sets.
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.20,

    random_state=42,

    stratify=y
)


print("\nDataset split:")
print("Training rows:", len(X_train))
print("Testing rows :", len(X_test))


# ============================================================
# TRAIN CATBOOST
# ============================================================

print("\n" + "=" * 70)
print("TRAINING CATBOOST")
print("=" * 70)

model = CatBoostClassifier(

    depth=4,

    learning_rate=0.1,

    iterations=500,

    l2_leaf_reg=3,

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
# TEST SET PREDICTION
# ============================================================

y_pred = model.predict(X_test)


# ============================================================
# EVALUATION
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)


print("\n" + "=" * 70)
print("INITIAL MODEL PERFORMANCE")
print("=" * 70)

print(
    f"Accuracy : {accuracy * 100:.2f}%"
)


print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        y_pred
    )
)


print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)

print(
    "\nModel saved as:"
)

print(MODEL_PATH)

print("\n" + "=" * 70)
print("INITIAL CATBOOST TRAINING COMPLETE")
print("=" * 70)