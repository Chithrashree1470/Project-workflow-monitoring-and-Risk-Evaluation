import pandas as pd
import numpy as np

# ==========================================
# Load Dataset
# ==========================================
df = pd.read_csv("project_risk_final_clean.csv")

# ==========================================
# Feature Engineering
# ==========================================

# 1. Task Completion Ratio
df["Task_Completion_Ratio"] = (
    df["Completed_Tasks"] /
    df["Total_Tasks"].replace(0, 1)
).round(2)

# 2. Schedule Variance
df["Schedule_Variance"] = (
    df["Actual_Effort_Hours"] /
    df["Estimated_Effort_Hours"].replace(0, 1)
).round(2)

# 3. Delay Severity
df["Delay_Severity"] = (
    df["Delay_Percentage"] *
    df["Average_Delay_Days"]
).round(2)

# 4. Workload Index
df["Workload_Index"] = (
    df["Estimated_Effort_Hours"] /
    df["Team_Size"].replace(0, 1)
).round(2)

# 5. Dependency Density
df["Dependency_Density"] = (
    df["External_Dependencies_Count"] /
    df["Total_Tasks"].replace(0, 1)
).round(2)

# 6. Budget Pressure
df["Budget_Pressure"] = (
    df["Budget_Utilization_Rate"] *
    df["Schedule_Pressure"]
).round(2)

# 7. Team Stability
df["Team_Stability"] = (
    100 - df["Team_Turnover_Rate"]
).round(2)

# 8. Resource Stress
df["Resource_Stress"] = (
    100 - df["Resource_Availability"]
).round(2)

# 9. Stakeholder Risk
df["Stakeholder_Risk"] = (
    df["Stakeholder_Count"] *
    df["Change_Request_Frequency"]
).round(2)

# 10. Technical Risk
df["Technical_Risk"] = (
    df["Technical_Debt_Level"] +
    df["Integration_Complexity"]
).round(2)

# 11. Risk Index
df["Risk_Index"] = (
    0.25 * df["Complexity_Score"] +
    0.25 * df["Technical_Debt_Level"] +
    0.20 * df["Delay_Percentage"] +
    0.15 * df["Team_Turnover_Rate"] +
    0.15 * df["Budget_Utilization_Rate"]
).round(2)

# 12. Project Health Score
df["Project_Health_Score"] = (
    0.30 * df["Completion_Percentage"] +
    0.20 * df["Resource_Availability"] +
    0.20 * df["Team_Stability"] +
    0.30 * (100 - df["Budget_Utilization_Rate"])
).round(2)

# 13. Delivery Efficiency
df["Delivery_Efficiency"] = (
    df["Completion_Percentage"] /
    (df["Average_Delay_Days"] + 1)
).round(2)

# 14. Productivity Score
df["Productivity_Score"] = (
    df["Completed_Tasks"] /
    df["Actual_Effort_Hours"].replace(0, 1)
).round(2)

# 15. Complexity per Team Member
df["Complexity_Per_Team"] = (
    df["Complexity_Score"] /
    df["Team_Size"].replace(0, 1)
).round(2)

# 16. Budget per Team Member
df["Budget_Per_Team_Member"] = (
    df["Project_Budget_USD"] /
    df["Team_Size"].replace(0, 1)
).round(2)

# 17. Timeline Efficiency
df["Timeline_Efficiency"] = (
    df["Estimated_Timeline_Months"] /
    (df["Current_Phase_Duration_Months"] + 1)
).round(2)

# 18. Dependency Risk Score
df["Dependency_Risk_Score"] = (
    df["External_Dependencies_Count"] *
    df["Integration_Complexity"]
).round(2)

# ==========================================
# Replace NaN and Infinity
# ==========================================

df.replace([np.inf, -np.inf], 0, inplace=True)
df.fillna(0, inplace=True)

# ==========================================
# Save Dataset
# ==========================================

df.to_csv("project_risk_feature_engineered.csv", index=False)

print("=" * 60)
print("FEATURE ENGINEERING COMPLETED")
print("=" * 60)

print("\nNew Dataset Shape:")
print(df.shape)

print("\nNew Features Added:")

new_features = [
    "Task_Completion_Ratio",
    "Schedule_Variance",
    "Delay_Severity",
    "Workload_Index",
    "Dependency_Density",
    "Budget_Pressure",
    "Team_Stability",
    "Resource_Stress",
    "Stakeholder_Risk",
    "Technical_Risk",
    "Risk_Index",
    "Project_Health_Score",
    "Delivery_Efficiency",
    "Productivity_Score",
    "Complexity_Per_Team",
    "Budget_Per_Team_Member",
    "Timeline_Efficiency",
    "Dependency_Risk_Score"
]

for feature in new_features:
    print("✓", feature)

print("\nDataset saved as:")
print("project_risk_feature_engineered.csv")