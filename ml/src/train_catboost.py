import pandas as pd
import joblib

from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ==========================
# Load Dataset
# ==========================

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
df = pd.read_csv(BASE_DIR / "project_risk_final_clean.csv")

df = df.drop(columns=["Project_ID"])

X = df.drop("Risk_Level", axis=1)
y = df["Risk_Level"]

categorical_columns = X.select_dtypes(include=["object"]).columns

for col in categorical_columns:
    X[col] = X[col].astype(str)

cat_features = [X.columns.get_loc(col) for col in categorical_columns]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==========================
# Train Final Model
# ==========================

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

model.fit(X_train, y_train)

# ==========================
# Prediction
# ==========================

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "="*70)
print("FINAL MODEL ACCURACY")
print("="*70)
print(f"Accuracy : {accuracy*100:.2f}%")

print("\n" + "="*70)
print("CLASSIFICATION REPORT")
print("="*70)
print(classification_report(y_test, y_pred))

print("\n" + "="*70)
print("CONFUSION MATRIX")
print("="*70)
print(confusion_matrix(y_test, y_pred))

joblib.dump(model, "catboost_final_model.pkl")

print("\nModel saved as catboost_final_model.pkl")