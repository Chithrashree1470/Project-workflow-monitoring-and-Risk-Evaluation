
import numpy as np
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
        i
        for i in range(len(feature_names))
        if i in categorical_indices
    ]

    pool = Pool(
        data=feature_row,
        cat_features=categorical_features
    )

    shap_result = model.get_feature_importance(
        pool,
        type="ShapValues"
    )

    # CatBoost returns:
    #   Binary/regression: (samples, features + 1)
    #   Multiclass:        (classes, samples, features + 1)
    #
    # We only have one input row, so select that row while
    # preserving the feature contributions.

    shap_array = np.asarray(shap_result)

    if shap_array.ndim == 2:
        # Shape: (samples, features + 1)
        shap_values = shap_array[0, :-1]

    elif shap_array.ndim == 3:
        # Shape: (classes, samples, features + 1)
        #
        # Select the class corresponding to the predicted class
        # when possible.
        class_index = 0

        try:
            if hasattr(model, "classes_"):
                classes = list(model.classes_)

                if predicted_risk in classes:
                    class_index = classes.index(predicted_risk)
                elif str(predicted_risk) in [str(c) for c in classes]:
                    class_index = [
                        str(c) for c in classes
                    ].index(str(predicted_risk))
        except Exception:
            class_index = 0

        shap_values = shap_array[class_index, 0, :-1]

    else:
        raise ValueError(
            f"Unexpected SHAP output shape: {shap_array.shape}"
        )

    explanations = []

    for feature, value, shap_value in zip(
        feature_names,
        feature_row.iloc[0].values,
        shap_values
    ):
        # Convert NumPy scalar safely to Python float.
        shap_value = float(np.asarray(shap_value).item())

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
                f"{item['factor']} contributed positively "
                f"to the predicted risk."
            )

            item["suggestion"] = (
                f"Review {item['factor']} and consider "
                f"appropriate corrective action."
            )

            problems.append(item)

    try:
        probabilities = np.asarray(
            model.predict_proba(feature_row)
        )[0]

        confidence = round(
            float(np.max(probabilities)) * 100,
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

