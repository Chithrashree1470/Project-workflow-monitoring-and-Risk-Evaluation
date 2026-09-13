import pandas as pd

df = pd.read_csv("project_risk_final.csv")

categorical_cols = [
    "Tech_Environment_Stability",
    "Change_Control_Maturity",
    "Risk_Management_Maturity"
]

for col in categorical_cols:
    df[col] = df[col].fillna("Unknown")

df.to_csv("project_risk_feature_engineered.csv", index=False)

print("Dataset cleaned successfully!")
print(df.isnull().sum().sum())