from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from backend.services.project_workflow import run_project_prediction

project_bp = Blueprint(
    "project",
    __name__
)


@project_bp.route("/")
def home():
    return render_template("project_form.html")


@project_bp.route(
    "/predict",
    methods=["POST"]
)
@project_bp.route("/predict", methods=["POST"])
def predict():
    try:
        result_data = run_project_prediction(request.form)

        session["result"] = result_data

        if request.accept_mimetypes.best == "application/json":
            return jsonify({
                "success": True,
                **result_data
            }), 201

        return render_template(
            "result.html",
            result=result_data
        )

    except Exception as e:
        import traceback
        print("Prediction error:", e)
        traceback.print_exc()

        if request.accept_mimetypes.best == "application/json":
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

        return "Prediction error: " + str(e), 400

@project_bp.route("/result")
def result():
    result_data = session.get("result")

    if not result_data:
        return redirect(
            url_for("project.home")
        )

    return render_template(
        "result.html",
        result=result_data
    )
