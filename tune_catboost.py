import pandas as pd
import joblib

from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ============================================================
# Load Dataset
# ============================================================
df = pd.read_csv("project_risk_feature_engineered.csv")

# Remove identifier column
df = df.drop(columns=["Project_ID"])

# Features and Target
X = df.drop("Risk_Level", axis=1)
y = df["Risk_Level"]

# Find categorical columns
categorical_columns = X.select_dtypes(include=["object"]).columns

# Convert categorical columns to string
for col in categorical_columns:
    X[col] = X[col].astype(str)

# Convert categorical column names to indices
cat_features = [X.columns.get_loc(col) for col in categorical_columns]

# Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ============================================================
# Base Model
# ============================================================
model = CatBoostClassifier(
    loss_function="MultiClass",
    eval_metric="Accuracy",
    random_seed=42,
    verbose=False,
    cat_features=cat_features
)
# ============================================================
# Hyperparameter Grid
# ============================================================
param_grid = {
    "depth": [4, 6, 8, 10],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "iterations": [300, 500, 700, 1000],
    "l2_leaf_reg": [1, 3, 5, 7, 9]
}

print("=" * 70)
print("STARTING CATBOOST GRID SEARCH")
print("=" * 70)

# ============================================================
# Grid Search
# ============================================================
grid_result = model.grid_search(
    param_grid,
    X=X_train,
    y=y_train,
    cv=5,
    shuffle=True,
    partition_random_seed=42,
    verbose=True
)

print("\n" + "=" * 70)
print("BEST PARAMETERS")
print("=" * 70)
print(grid_result["params"])

# ============================================================
# Train Final Model Using Best Parameters
# ============================================================
best_model = CatBoostClassifier(
    **grid_result["params"],
    loss_function="MultiClass",
    eval_metric="Accuracy",
    random_seed=42,
    verbose=100,
    cat_features=cat_features
)

best_model.fit(
    X_train,
    y_train,
    cat_features=cat_features
)

# ============================================================
# Evaluate
# ============================================================
y_pred = best_model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 70)
print("FINAL MODEL ACCURACY")
print("=" * 70)
print(f"Accuracy : {accuracy * 100:.2f}%")

# ============================================================
# Save Model
# ============================================================
joblib.dump(best_model, "catboost_best_model.pkl")

print("\nBest model saved as catboost_best_model.pkl")