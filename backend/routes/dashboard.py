from flask import Blueprint, render_template

from backend.supabase_client import supabase

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def dashboard():

    try:

        response = (

            supabase

            .table("projects")

            .select("*")

            .order(
                "id",
                desc=True
            )

            .execute()

        )

        projects = (
            response.data or []
        )

    except Exception as error:

        print(
            "Dashboard error:",
            error
        )

        projects = []

    counts = {

        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0

    }

    for project in projects:

        risk = str(
            project.get(
                "predicted_risk",
                ""
            )
        ).strip()

        if risk in counts:

            counts[risk] += 1

    return render_template(

        "dashboard.html",

        projects=projects,

        counts=counts

    )
