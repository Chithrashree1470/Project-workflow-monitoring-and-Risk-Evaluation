# import pandas as pd
# import joblib

# # Load model
# model = joblib.load("catboost_final_model.pkl")

# # Load dataset
# df = pd.read_csv("project_risk_final_clean.csv")

# # Remove Project_ID
# df = df.drop(columns=["Project_ID"])

# # Separate features and target
# X = df.drop("Risk_Level", axis=1)
# y = df["Risk_Level"]

# # Convert categorical columns to string
# categorical_columns = X.select_dtypes(include=["object"]).columns
# for col in categorical_columns:
#     X[col] = X[col].astype(str)

# # Take the first project
# sample = X.iloc[[0]]

# # Actual risk
# actual = y.iloc[0]

# # Predict
# prediction = model.predict(sample)

# print("=" * 60)
# print("AI RISK PREDICTION")
# print("=" * 60)

# print("Actual Risk     :", actual)
# print("Predicted Risk  :", prediction[0])

# if actual == prediction[0]:
#     print("\n✅ Prediction is Correct")
# else:
#     print("\n❌ Prediction is Incorrect")

import pandas as pd
import joblib

# Load model
model = joblib.load("catboost_final_model.pkl")

# Load dataset
df = pd.read_csv("project_risk_final_clean.csv")

# Remove target and Project_ID
X = df.drop(columns=["Project_ID", "Risk_Level"])

# Take the first project
new_project = X.iloc[[0]].copy()

# Modify some values to simulate a new project
new_project["Team_Size"] = 20
new_project["Delay_Percentage"] = 40
new_project["Employee_Workload"] = 90
new_project["Completion_Percentage"] = 35

# Predict
prediction = model.predict(new_project)

print("Predicted Risk:", prediction[0])