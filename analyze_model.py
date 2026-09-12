import joblib
import pandas as pd

# ==========================================
# LOAD ORIGINAL 72% MODEL
# ==========================================

model = joblib.load("catboost_final_model.pkl")

# ==========================================
# LOAD ORIGINAL DATASET
# ==========================================

df = pd.read_csv("project_risk_final_clean.csv")

print("\n==========================================")
print("ORIGINAL DATASET")
print("==========================================")

print("Rows:", df.shape[0])
print("Columns:", df.shape[1])

# ==========================================
# MODEL FEATURES
# ==========================================

print("\n==========================================")
print("FEATURES USED BY 72% MODEL")
print("==========================================")

features = list(model.feature_names_)

for i, feature in enumerate(features, start=1):
    print(f"{i:02d}. {feature}")

print("\nTotal model features:", len(features))

# ==========================================
# FEATURE IMPORTANCE
# ==========================================

print("\n==========================================")
print("FEATURE IMPORTANCE")
print("==========================================")

importance = model.get_feature_importance()

feature_importance = pd.DataFrame({
    "Feature": features,
    "Importance": importance
})

feature_importance = feature_importance.sort_values(
    by="Importance",
    ascending=False
)

for _, row in feature_importance.iterrows():
    print(
        f"{row['Feature']:40} "
        f"{row['Importance']:.4f}"
    )

# ==========================================
# SAVE FEATURE IMPORTANCE
# ==========================================

feature_importance.to_csv(
    "feature_importance_72_model.csv",
    index=False
)

print("\n==========================================")
print("DONE")
print("==========================================")

print(
    "\nSaved: feature_importance_72_model.csv"
)