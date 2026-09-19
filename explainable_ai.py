"""Explainable AI and actionable recommendations for project risk.

This module keeps the trained CatBoost model as the prediction engine and
adds a SHAP-based explanation layer.  It also translates important risk
factors into plain-language problems and manager-facing suggestions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap


# Human-readable names used on the result page.
DISPLAY_NAMES = {
    "Project_Type": "Project Type",
    "Team_Size": "Team Size",
    "Project_Budget_USD": "Project Budget",
    "Estimated_Timeline_Months": "Estimated Timeline",
    "Complexity_Score": "Complexity Score",
    "Stakeholder_Count": "Stakeholder Count",
    "Methodology_Used": "Methodology",
    "Team_Experience_Level": "Team Experience",
    "External_Dependencies_Count": "External Dependencies",
    "Change_Request_Frequency": "Change Request Frequency",
    "Project_Phase": "Project Phase",
    "Requirement_Stability": "Requirement Stability",
    "Team_Turnover_Rate": "Team Turnover Rate",
    "Resource_Availability": "Resource Availability",
    "Technical_Debt_Level": "Technical Debt",
    "Integration_Complexity": "Integration Complexity",
    "Organizational_Maturity": "Organizational Maturity",
    "Stakeholder_Engagement_Level": "Stakeholder Engagement",
    "Risk_Management_Maturity": "Risk Management Maturity",
    "Workflow_Execution_Metrics": "Workflow Execution Metrics",
    "Technology_Familiarity": "Technology Familiarity",
    "Project_Manager_Experience": "Project Manager Experience",
    "Total_Tasks": "Total Tasks",
    "Completed_Tasks": "Completed Tasks",
    "Pending_Tasks": "Pending Tasks",
    "Overdue_Tasks": "Overdue Tasks",
    "Completion_Percentage": "Completion Percentage",
    "Delay_Percentage": "Delay Percentage",
    "Average_Delay_Days": "Average Delay Days",
    "Employee_Workload": "Employee Workload",
    "Estimated_Effort_Hours": "Estimated Effort Hours",
    "Actual_Effort_Hours": "Actual Effort Hours",
    "Project_Progress": "Project Progress",
}


def _display_name(feature: str) -> str:
    return DISPLAY_NAMES.get(feature, feature.replace("_", " "))


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _recommendation_for_feature(feature: str, value, row: pd.Series):
    """Return (problem, explanation, suggestion) for a risk-driving feature."""
    v = _number(value, None)

    rules = {
        "Overdue_Tasks": (
            v is not None and v > 0,
            "Overdue tasks are increasing delivery pressure.",
            "Prioritize overdue tasks, review their deadlines, and remove blockers before assigning new work."
        ),
        "Delay_Percentage": (
            v is not None and v >= 10,
            "A noticeable share of tasks are delayed.",
            "Review delayed tasks, identify the cause of delay, and re-plan the affected deadlines."
        ),
        "Employee_Workload": (
            v is not None and v >= 70,
            "Employee workload is high and may create additional delays.",
            "Redistribute pending work among available team members and avoid overloading the same employees."
        ),
        "Completion_Percentage": (
            v is not None and v < 50,
            "Less than half of the planned work is completed.",
            "Review project progress, prioritize critical tasks, and verify that task allocation matches project priorities."
        ),
        "Complexity_Score": (
            v is not None and v >= 7,
            "The project has a high calculated complexity level.",
            "Break complex work into smaller tasks and consider assigning experienced team members to the most difficult work."
        ),
        "External_Dependencies_Count": (
            v is not None and v >= 5,
            "The project has several external dependencies that can delay delivery.",
            "Review dependency owners and due dates, and prepare a fallback plan for critical external dependencies."
        ),
        "Actual_Effort_Hours": (
            v is not None and _number(row.get("Estimated_Effort_Hours")) > 0 and v > _number(row.get("Estimated_Effort_Hours")) * 1.15,
            "Actual effort is substantially higher than the estimated effort.",
            "Re-estimate the remaining work and review resource allocation before committing to the current deadline."
        ),
        "Team_Turnover_Rate": (
            v is not None and v >= 15,
            "High team turnover can create knowledge gaps and delivery disruption.",
            "Plan knowledge transfer, document critical work, and stabilize ownership of important tasks."
        ),
        "Requirement_Stability": (
            isinstance(value, str) and value.lower() in {"low", "unstable", "volatile"},
            "Requirements are not stable, increasing the chance of rework.",
            "Confirm the current scope with stakeholders and control new changes through a clear change-review process."
        ),
        "Technical_Debt_Level": (
            v is not None and v >= 7,
            "Technical debt is high and may increase maintenance and delivery effort.",
            "Prioritize the most risky technical-debt items and reserve controlled time for remediation."
        ),
        "Integration_Complexity": (
            v is not None and v >= 7,
            "Integration complexity is high and may create coordination or compatibility issues.",
            "Break integrations into smaller milestones, test interfaces early, and identify fallback integration paths."
        ),
        "Stakeholder_Count": (
            v is not None and v >= 10,
            "A large stakeholder group can increase coordination and approval effort.",
            "Define clear stakeholder ownership, approval responsibilities, and a regular communication schedule."
        ),
        "Change_Request_Frequency": (
            v is not None and v >= 5,
            "Frequent change requests can increase rework and schedule pressure.",
            "Review change requests by impact and priority before adding them to the active scope."
        ),
        "Resource_Availability": (
            isinstance(value, str) and value.lower() in {"low", "limited", "poor"},
            "Available resources are limited for the current project needs.",
            "Review resource allocation and move available capacity toward critical project tasks."
        ),
        "Team_Size": (
            v is not None and v >= 20,
            "A large team can increase coordination overhead.",
            "Clarify ownership, split work into smaller workstreams, and use clear communication channels."
        ),
        "Estimated_Timeline_Months": (
            v is not None and v <= 3 and _number(row.get("Total_Tasks")) >= 50,
            "The planned timeline is short relative to the amount of work.",
            "Review schedule pressure and consider phasing the delivery or reprioritizing lower-priority tasks."
        ),
    }

    rule = rules.get(feature)
    if not rule or not rule[0]:
        return None
    return {
        "feature": feature,
        "factor": _display_name(feature),
        "problem": rule[1],
        "explanation": rule[1],
        "suggestion": rule[2],
    }


# Additional model-specific explanations. These make the UI useful even when
# SHAP selects a feature that is not part of the basic workflow metrics.
ADDITIONAL_RULES = {
    "Project_Budget_USD": ("The project budget is an important risk factor.", "Review remaining budget, committed spend, and contingency before adding new scope."),
    "Past_Similar_Projects": ("The project has a relevant history of similar-project outcomes.", "Review lessons learned from similar projects and reuse proven planning practices."),
    "Vendor_Reliability_Score": ("Vendor reliability can affect delivery continuity.", "Review vendor performance and prepare alternatives for critical vendor dependencies."),
    "Historical_Risk_Incidents": ("Previous risk incidents are contributing to the model's assessment.", "Review previous incidents and confirm that their preventive actions are in place."),
    "Communication_Frequency": ("Communication patterns can affect coordination.", "Set a regular communication cadence for the project team and key stakeholders."),
    "Regulatory_Compliance_Level": ("Compliance requirements can add delivery constraints.", "Identify required approvals early and track compliance activities as project milestones."),
    "Geographical_Distribution": ("Distributed teams can increase coordination overhead.", "Define clear working hours, ownership, documentation, and communication routines."),
    "Stakeholder_Engagement_Level": ("Stakeholder engagement affects decisions and approvals.", "Schedule regular stakeholder reviews and clarify decision ownership."),
    "Schedule_Pressure": ("Schedule pressure can increase the chance of delay or rework.", "Prioritize critical-path work and review whether lower-priority scope can be phased."),
    "Budget_Utilization_Rate": ("Budget utilization is an important indicator of financial pressure.", "Compare current spend with completed work and reserve budget for high-priority remaining work."),
    "Executive_Sponsorship": ("Executive sponsorship affects escalation and decision support.", "Confirm an available sponsor for major blockers and timely escalations."),
    "Market_Volatility": ("Market volatility can affect assumptions and delivery conditions.", "Review external assumptions regularly and prepare contingency actions for major changes."),
    "Organizational_Change_Frequency": ("Frequent organizational changes can disrupt ownership and priorities.", "Confirm current ownership and communicate changes before they affect active tasks."),
    "Previous_Delivery_Success_Rate": ("Previous delivery performance is influencing the risk assessment.", "Review lessons from previous delivery cycles and apply corrective practices to the current plan."),
    "Org_Process_Maturity": ("Process maturity affects how consistently work is planned and controlled.", "Standardize key workflow, review, and escalation procedures for the project."),
    "Data_Security_Requirements": ("Security requirements can add validation and approval work.", "Identify security checkpoints early and include them in the delivery plan."),
    "Key_Stakeholder_Availability": ("Limited stakeholder availability can slow decisions and approvals.", "Agree on backup approvers and schedule critical reviews in advance."),
    "Tech_Environment_Stability": ("An unstable technical environment can interrupt delivery.", "Stabilize the environment and track recurring technical issues before critical milestones."),
    "Resource_Contention_Level": ("Resources are competing across work, which can delay the project.", "Resolve resource conflicts and prioritize capacity for critical-path tasks."),
    "Industry_Volatility": ("Industry conditions can introduce external uncertainty.", "Review external assumptions and maintain contingency plans for major changes."),
    "Client_Experience_Level": ("Client experience can affect requirement clarification and approvals.", "Use clear demonstrations, written decisions, and frequent requirement confirmation."),
    "Change_Control_Maturity": ("Change-control maturity affects how safely new scope is introduced.", "Use an impact-review process for scope changes and document approved decisions."),
    "Team_Colocation": ("Team distribution can influence communication and coordination.", "Use shared documentation and predictable communication windows for distributed members."),
    "Documentation_Quality": ("Documentation quality affects knowledge continuity and handovers.", "Document key decisions, interfaces, task ownership, and operational procedures."),
    "Current_Phase_Duration_Months": ("The current project phase has accumulated duration that may indicate pressure.", "Review phase completion criteria and remove blockers before extending the phase further."),
    "Seasonal_Risk_Factor": ("Seasonal conditions can affect planned delivery activities.", "Include known seasonal constraints in the schedule and plan contingency time."),
    "Average_Delay_Days": ("Average task delay is contributing to delivery pressure.", "Identify the most delayed tasks, address their blockers, and update estimates where necessary."),
    "Total_Tasks": ("The project contains a large amount of task-level work.", "Group tasks into manageable workstreams and focus monitoring on critical-path items."),
    "Pending_Tasks": ("A substantial amount of work remains pending.", "Prioritize pending tasks by project impact and assign clear owners and deadlines."),
    "Estimated_Effort_Hours": ("The estimated effort is an important planning baseline.", "Compare estimates with actual performance and recalibrate remaining effort when necessary."),
    "Project_Progress": ("Current project progress is influencing the risk assessment.", "Review progress against planned milestones and address gaps on critical deliverables."),
    "Methodology_Used": ("The selected delivery methodology influences workflow and control practices.", "Confirm that the team's workflow and review practices match the selected methodology."),
    "Project_Phase": ("The current project phase changes which risks require attention.", "Review the phase-specific completion criteria and unresolved risks before moving forward."),
    "Priority_Level": ("Project priority affects how resources and decisions should be handled.", "Protect capacity for high-priority deliverables and make trade-offs explicit."),
    "Funding_Source": ("Funding conditions can influence project continuity.", "Confirm funding milestones and communicate any financial constraints early."),
}


def _fallback_for_feature(feature: str, value):
    """Fallback wording so every important SHAP factor remains understandable."""
    factor = _display_name(feature)
    if feature in ADDITIONAL_RULES:
        problem, suggestion = ADDITIONAL_RULES[feature]
        return {
            "feature": feature,
            "factor": factor,
            "problem": problem,
            "explanation": problem,
            "suggestion": suggestion,
        }
    return {
        "feature": feature,
        "factor": factor,
        "problem": f"{factor} is contributing to the predicted risk.",
        "explanation": f"The model identified {factor} as an important contributor for this prediction.",
        "suggestion": f"Review the current {factor.lower()} value and take corrective action if it is outside the project's planned range.",
    }


def explain_prediction(model, input_df: pd.DataFrame, predicted_risk: str, top_n: int = 8):
    """Generate SHAP explanations and actionable recommendations.

    For multiclass CatBoost, explanations are taken from the class predicted by
    the model. Positive SHAP values indicate that the feature pushes the model
    toward the predicted class; negative values push away from it.
    """
    if input_df.empty:
        return {
            "confidence": 0.0,
            "top_factors": [],
            "problems": [],
            "protective_factors": [],
        }

    probabilities = model.predict_proba(input_df)[0]
    classes = [str(c) for c in model.classes_]
    try:
        class_index = classes.index(str(predicted_risk))
    except ValueError:
        class_index = int(np.argmax(probabilities))
        predicted_risk = classes[class_index]

    confidence = float(probabilities[class_index]) * 100.0

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(input_df)
    values = np.asarray(shap_values)

    if values.ndim == 3:
        class_values = values[0, :, class_index]
    elif values.ndim == 2:
        class_values = values[0, :]
    else:
        class_values = values.reshape(-1)

    row = input_df.iloc[0]
    records = []
    for feature, shap_value in zip(input_df.columns, class_values):
        records.append({
            "feature": feature,
            "factor": _display_name(feature),
            "value": str(row[feature]),
            "shap_value": float(shap_value),
            "impact": "Increases risk" if shap_value > 0 else "Reduces risk",
        })

    positive = sorted(
        [r for r in records if r["shap_value"] > 0],
        key=lambda r: abs(r["shap_value"]),
        reverse=True,
    )
    negative = sorted(
        [r for r in records if r["shap_value"] < 0],
        key=lambda r: abs(r["shap_value"]),
        reverse=True,
    )

    top_factors = positive[:top_n]
    for factor in top_factors:
        factor["shap_value_display"] = round(factor["shap_value"], 4)

    # Recommendations are generated for important SHAP factors first.
    problems = []
    seen = set()
    for factor in top_factors:
        item = _recommendation_for_feature(
            factor["feature"],
            row[factor["feature"]],
            row,
        )
        if item is None:
            item = _fallback_for_feature(
                factor["feature"],
                row[factor["feature"]],
            )
        item["shap_value"] = factor["shap_value"]
        item["value"] = factor["value"]
        if item["feature"] not in seen:
            problems.append(item)
            seen.add(item["feature"])

    # Also surface concrete problems present in the input even if their SHAP
    # contribution is just outside the top-N list.
    for feature in [
        "Overdue_Tasks", "Delay_Percentage", "Employee_Workload",
        "Completion_Percentage", "Complexity_Score", "Actual_Effort_Hours",
        "External_Dependencies_Count", "Team_Turnover_Rate",
        "Requirement_Stability", "Technical_Debt_Level",
        "Integration_Complexity", "Change_Request_Frequency",
        "Resource_Availability", "Stakeholder_Count",
    ]:
        if feature not in input_df.columns or feature in seen:
            continue
        item = _recommendation_for_feature(feature, row[feature], row)
        if item is not None:
            item["shap_value"] = next(
                (r["shap_value"] for r in records if r["feature"] == feature),
                0.0,
            )
            item["value"] = str(row[feature])
            problems.append(item)
            seen.add(feature)

    return {
        "confidence": round(confidence, 2),
        "predicted_class": predicted_risk,
        "top_factors": top_factors,
        "problems": problems,
        "protective_factors": negative[:5],
    }
