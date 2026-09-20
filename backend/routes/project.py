from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session
)

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
def predict():
    try:
        result_data = run_project_prediction(request.form)

        session["result"] = result_data

        return render_template(
            "result.html",
            result=result_data
        )

    except Exception as error:
        print()
        print("Prediction error:", error)

        return (
            "Prediction error: " + str(error),
            400
        )


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
