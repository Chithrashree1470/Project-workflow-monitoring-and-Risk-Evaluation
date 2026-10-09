from flask import Blueprint, render_template, request, redirect, url_for, session
from backend.services.access_service import authenticate_project_access

access_bp = Blueprint("access", __name__)


@access_bp.route("/project/<project_id>/login", methods=["GET", "POST"])
def project_login(project_id):
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        access = authenticate_project_access(project_id, username, password)
        if not access:
            return render_template("project_login.html", project_id=project_id, error="Invalid project credentials."), 401
        session[f"project_access_{project_id}"] = access
        return redirect(url_for("project_details.project_details", project_id=project_id))
    return render_template("project_login.html", project_id=project_id, error=None)


@access_bp.route("/project/<project_id>/logout")
def project_logout(project_id):
    session.pop(f"project_access_{project_id}", None)
    return redirect(url_for("project_details.project_details", project_id=project_id))
