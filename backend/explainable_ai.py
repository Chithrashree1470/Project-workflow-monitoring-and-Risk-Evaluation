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
    shap_array = np.asarray(shap_result)

    # CatBoost SHAP layouts vary by objective/version. Normalize the result
    # to one contribution per input feature without assuming a fixed class axis.
    expected_feature_count = len(feature_names)
    class_index = 0

    try:
        if hasattr(model, "classes_"):
            classes = list(model.classes_)
            predicted_text = str(predicted_risk)
            class_index = next(
                (
                    i for i, value in enumerate(classes)
                    if str(value) == predicted_text
                ),
                0
            )
    except Exception:
        class_index = 0

    if shap_array.ndim == 1:
        # Single row, features + expected value.
        row_values = shap_array

    elif shap_array.ndim == 2:
        # Usually (samples, features + 1), but accept a single-row vector
        # represented as (1, features + 1).
        if shap_array.shape[0] == 1:
            row_values = shap_array[0]
        elif shap_array.shape[1] == 1:
            row_values = shap_array[:, 0]
        else:
            raise ValueError(
                f"Unexpected 2D SHAP output shape: {shap_array.shape}"
            )

    elif shap_array.ndim == 3:
        # Common layouts include (classes, samples, features + 1) and
        # (samples, classes, features + 1). Detect the single-sample axis.
        if shap_array.shape[1] == 1:
            # (classes, samples, features + 1)
            safe_class_index = min(max(class_index, 0), shap_array.shape[0] - 1)
            row_values = shap_array[safe_class_index, 0, :]
        elif shap_array.shape[0] == 1:
            # (samples, classes, features + 1)
            safe_class_index = min(max(class_index, 0), shap_array.shape[1] - 1)
            row_values = shap_array[0, safe_class_index, :]
        else:
            raise ValueError(
                f"Cannot identify the single input row in SHAP output shape: "
                f"{shap_array.shape}"
            )

    else:
        raise ValueError(
            f"Unexpected SHAP output shape: {shap_array.shape}"
        )

    row_values = np.asarray(row_values).reshape(-1)

    # The final SHAP value is the expected/base value when present.
    if row_values.size == expected_feature_count + 1:
        shap_values = row_values[:-1]
    elif row_values.size == expected_feature_count:
        shap_values = row_values
    else:
        raise ValueError(
            "SHAP feature count does not match input features: "
            f"received {row_values.size} values for "
            f"{expected_feature_count} features "
            f"(shape={shap_array.shape})"
        )

    explanations = []

    for feature, value, shap_value in zip(
        feature_names,
        feature_row.iloc[0].values,
        shap_values
    ):
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
