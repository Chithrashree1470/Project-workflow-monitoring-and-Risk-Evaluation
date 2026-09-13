import joblib
import pandas as pd
from flask import Flask, render_template, request
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
model = joblib.load(BASE_DIR / "catboost_final_model.pkl")

reference_df = pd.read_csv(BASE_DIR / "project_risk_final_clean.csv")
reference_df = reference_df.drop(columns=["Project_ID", "Risk_Level"])
@app.route("/")
def home():
    return render_template("project_form.html")


@app.route("/predict", methods=["POST"])
def predict():

    project_name = request.form["project_name"]
    project_type = request.form["project_type"]
    team_size = request.form["team_size"]
    budget = request.form["project_budget"]
    timeline = request.form["timeline"]
    complexity_score = request.form["complexity_score"]
    total_tasks = request.form["total_tasks"]
    completed_tasks = request.form["completed_tasks"]
    overdue_tasks = request.form["overdue_tasks"]
    estimated_effort_hours = request.form["estimated_effort_hours"]

    print("\n========== PROJECT DETAILS ==========")
    print("Project Name :", project_name)
    print("Project Type :", project_type)
    print("Team Size :", team_size)
    print("Project Budget :", budget)
    print("Estimated Timeline :", timeline)
    print("Complexity Score :", complexity_score)
    print("Total Tasks :", total_tasks)
    print("Completed Tasks :", completed_tasks)
    print("Overdue Tasks :", overdue_tasks)
    print("Estimated Effort Hours :", estimated_effort_hours)
    print("=====================================")

    print("=====================================")

# Prepare input for AI model
    input_data = prepare_features(request.form)

# Predict risk
    prediction = model.predict(input_data)

    predicted_risk = prediction[0][0]
    classes = model.classes_
    probability = model.predict_proba(input_data)[0]

    print("\nPredicted Risk :", predicted_risk)

    print("\n========== AI CONFIDENCE ==========")
    for cls, prob in zip(classes, probability):
        print(f"{cls:10} : {prob*100:.2f}%")
    print("===================================")

    return f"""
<h2>Project Name: {project_name}</h2>
<h2>Predicted Risk: {predicted_risk}</h2>
"""
def prepare_features(form):

    # Start with one valid row
    features = reference_df.iloc[[0]].copy()

    # Replace with user values
    features["Project_Type"] = form["project_type"]
    features["Team_Size"] = int(form["team_size"])
    features["Project_Budget_USD"] = float(form["project_budget"])
    features["Estimated_Timeline_Months"] = int(form["timeline"])
    features["Complexity_Score"] = int(form["complexity_score"])

    features["Total_Tasks"] = int(form["total_tasks"])
    features["Completed_Tasks"] = int(form["completed_tasks"])
    features["Overdue_Tasks"] = int(form["overdue_tasks"])
    features["Estimated_Effort_Hours"] = float(form["estimated_effort_hours"])

    # Automatically calculated values
    features["Pending_Tasks"] = (
        features["Total_Tasks"] - features["Completed_Tasks"]
    )

    features["Completion_Percentage"] = (
        features["Completed_Tasks"] /
        features["Total_Tasks"]
    ) * 100

    return features

if __name__ == "__main__":
    app.run(debug=True)