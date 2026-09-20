import pandas as pd
from catboost import Pool


def explain_prediction(model, feature_row, predicted_risk, top_n=8):
    """Generate SHAP explanations in the structure expected by result.html."""
    if not isinstance(feature_row, pd.DataFrame):
        feature_row = pd.DataFrame([feature_row])

    feature_names = list(feature_row.columns)
    feature_row = feature_row[feature_names].copy()

    categorical_indices = set(model.get_cat_feature_indices())
    categorical_features = [
        i for i in range(len(feature_names))
        if i in categorical_indices
    ]

    pool = Pool(
        data=feature_row,
        cat_features=categorical_features
    )

    shap_values = model.get_feature_importance(
        pool,
        type="ShapValues"
    )[0][:-1]

    explanations = []

    for feature, value, shap_value in zip(
        feature_names,
        feature_row.iloc[0].values,
        shap_values
    ):
        shap_value = float(shap_value)

        explanations.append({
            "factor": feature.replace("_", " "),
            "value": value,
            "shap_value": shap_value,
            "abs_impact": abs(shap_value),
            "impact": (
                "Increases risk"
                if shap_value > 0
                else "Reduces risk"
            )
        })

    explanations.sort(
        key=lambda item: item["abs_impact"],
        reverse=True
    )

    top_factors = explanations[:top_n]

    protective_factors = [
        item
        for item in top_factors
        if item["shap_value"] < 0
    ]

    problems = []
    for item in top_factors:
        if item["shap_value"] > 0:
            item = dict(item)
            item["problem"] = (
                f"{item["factor"]} contributed positively to the predicted risk."
            )
            item["suggestion"] = (
                f"Review {item["factor"]} and consider appropriate corrective action."
            )
            problems.append(item)

    try:
        probabilities = model.predict_proba(
            feature_row
        )[0]
        confidence = round(
            float(max(probabilities)) * 100,
            2
        )
    except Exception:
        confidence = 0.0

    return {
        "predicted_risk": str(predicted_risk),
        "confidence": confidence,
        "top_factors": top_factors,
        "protective_factors": protective_factors,
        "problems": problems,
        "explanations": explanations
    }
