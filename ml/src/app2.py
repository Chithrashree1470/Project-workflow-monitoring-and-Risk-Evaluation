import joblib
import pandas as pd

from flask import Flask, render_template, request
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.routes.task_risk import task_risk_bp


app = Flask(__name__)
app.register_blueprint(task_risk_bp)
# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "catboost_ver2_model.pkl"
DATASET_PATH = BASE_DIR / "project_risk_final_clean.csv"


# ============================================================
# LOAD MODEL AND TRAINING DATA
# ============================================================

model = joblib.load(MODEL_PATH)

training_df = pd.read_csv(DATASET_PATH)


# ============================================================
# INITIAL MODEL FEATURES
# ============================================================

INITIAL_FEATURES = [
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
# CREATE DEFAULT VALUES
# ============================================================

def get_default_values():

    defaults = {}

    for column in INITIAL_FEATURES:

        if column not in training_df.columns:
            raise ValueError(
                f"Column '{column}' not found in training dataset."
            )

        # Categorical → most frequent value
        if training_df[column].dtype == "object":

            mode = training_df[column].mode()

            if len(mode) > 0:
                defaults[column] = mode.iloc[0]
            else:
                defaults[column] = "Unknown"

        # Numerical → median
        else:

            defaults[column] = training_df[column].median()

    return defaults


DEFAULT_VALUES = get_default_values()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template("project_form.html")


# ============================================================
# PREDICT
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    # --------------------------------------------------------
    # User inputs
    # --------------------------------------------------------

    project_name = request.form["project_name"]

    project_type = request.form["project_type"]

    team_size = int(
        request.form["team_size"]
    )

    project_budget = float(
        request.form["project_budget"]
    )

    timeline = int(
        request.form["timeline"]
    )

    complexity_score = float(
        request.form["complexity_score"]
    )

    total_tasks = int(
        request.form["total_tasks"]
    )

    completed_tasks = int(
        request.form["completed_tasks"]
    )

    overdue_tasks = int(
        request.form["overdue_tasks"]
    )

    estimated_effort_hours = float(
        request.form["estimated_effort_hours"]
    )


    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    if completed_tasks > total_tasks:

        return "Error: Completed tasks cannot exceed total tasks."

    if overdue_tasks > total_tasks:

        return "Error: Overdue tasks cannot exceed total tasks."


    # ========================================================
    # START WITH DATASET DEFAULTS
    # ========================================================

    input_data = pd.DataFrame(
        [DEFAULT_VALUES],
        columns=INITIAL_FEATURES
    )


    # ========================================================
    # OVERRIDE DEFAULTS WITH USER VALUES
    # ========================================================

    input_data["Project_Type"] = project_type

    input_data["Team_Size"] = team_size

    input_data["Project_Budget_USD"] = project_budget

    input_data["Estimated_Timeline_Months"] = timeline

    input_data["Complexity_Score"] = complexity_score


    # ========================================================
    # TASK INFORMATION
    # ========================================================
    #
    # These are NOT model features for the initial model.
    #
    # They are collected now because they will later be used
    # by the dynamic risk system.
    #
    # For a brand-new project:
    # completed tasks and overdue tasks will normally be 0.
    # ========================================================

    completion_percentage = (
        completed_tasks / total_tasks
    ) * 100


    # ========================================================
    # OPTIONAL: USE ESTIMATED EFFORT TO DERIVE A VALUE
    # ========================================================
    #
    # Estimated_Effort_Hours is not currently one of the
    # 47 initial CatBoost features, so it is stored only for
    # logging/display at this stage.
    # ========================================================


    # ========================================================
    # ENSURE CATEGORICAL VALUES ARE STRINGS
    # ========================================================

    categorical_columns = input_data.select_dtypes(
        include=["object"]
    ).columns

    for column in categorical_columns:

        input_data[column] = (
            input_data[column]
            .fillna("Unknown")
            .astype(str)
        )


    # ========================================================
    # PREDICTION
    # ========================================================

    prediction = model.predict(input_data)

    predicted_risk = prediction[0][0]

    probabilities = model.predict_proba(
        input_data
    )[0]

    classes = model.classes_


    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print("\n" + "=" * 70)
    print("INITIAL PROJECT RISK PREDICTION")
    print("=" * 70)

    print("Project Name       :", project_name)
    print("Project Type       :", project_type)
    print("Team Size          :", team_size)
    print("Budget             :", project_budget)
    print("Timeline           :", timeline)
    print("Complexity         :", complexity_score)
    print("Total Tasks        :", total_tasks)
    print("Completed Tasks    :", completed_tasks)
    print("Overdue Tasks      :", overdue_tasks)
    print("Completion         :", f"{completion_percentage:.2f}%")
    print("Estimated Effort   :", estimated_effort_hours)

    print("\nPredicted Risk     :", predicted_risk)

    print("\nAI Confidence:")

    for cls, probability in zip(classes, probabilities):

        print(
            f"{cls:10} : {probability * 100:.2f}%"
        )

    print("=" * 70)


    # ========================================================
    # RETURN RESULT
    # ========================================================

    confidence_html = ""

    for cls, probability in zip(classes, probabilities):

        confidence_html += (
            f"<li>{cls}: "
            f"{probability * 100:.2f}%</li>"
        )


    return f"""
    <!DOCTYPE html>

    <html>

    <head>
        <title>Risk Prediction Result</title>
    </head>

    <body>

        <h1>AI-Based Predictive Workflow Monitoring System</h1>

        <h2>Project: {project_name}</h2>

        <h2>
            Initial Predicted Risk:
            {predicted_risk}
        </h2>

        <h3>AI Confidence</h3>

        <ul>
            {confidence_html}
        </ul>

        <hr>

        <h3>Project Information</h3>

        <p>Project Type: {project_type}</p>

        <p>Team Size: {team_size}</p>

        <p>Budget: ${project_budget:,.2f}</p>

        <p>Timeline: {timeline} months</p>

        <p>Complexity Score: {complexity_score}</p>

        <p>Total Tasks: {total_tasks}</p>

        <p>Completed Tasks: {completed_tasks}</p>

        <p>Overdue Tasks: {overdue_tasks}</p>

        <p>
            Current Completion:
            {completion_percentage:.2f}%
        </p>

        <p>
            Estimated Effort:
            {estimated_effort_hours} hours
        </p>

    </body>

    </html>
    """


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(debug=True)