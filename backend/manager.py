import re

from flask import Blueprint, jsonify, request

manager_bp = Blueprint("manager", __name__)

def extract_resume_text():

    uploaded = request.files.get(
        "Manager_Resume"
    )

    if not uploaded:
        return ""

    if not uploaded.filename:
        return ""

    filename = (
        uploaded.filename
        .lower()
    )

    try:

        if filename.endswith(".txt"):

            return (
                uploaded
                .read()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )

        if filename.endswith(".pdf"):

            from pypdf import PdfReader

            reader = PdfReader(
                uploaded
            )

            text = []

            for page in reader.pages:

                text.append(
                    page.extract_text()
                    or ""
                )

            return "\n".join(text)

        if filename.endswith(".docx"):

            from docx import Document

            document = Document(
                uploaded
            )

            return "\n".join(

                paragraph.text

                for paragraph
                in document.paragraphs

            )

    except Exception as error:

        print(
            "Resume extraction error:",
            error
        )

    return ""


# ============================================================
# MANAGER EXPERIENCE FROM RESUME
# ============================================================

def manager_experience_from_resume(
    resume_text
):

    if not resume_text:
        return "Mid-level PM"

    text = (
        resume_text
        .lower()
    )

    certified_terms = [
        "pmp",
        "prince2",
        "project management professional",
        "certified project manager",
        "capm"
    ]

    if any(
        term in text
        for term in certified_terms
    ):

        return "Certified PM"

    years = []

    patterns = [

        r"(\d+(?:\.\d+)?)\+?\s*years",
        r"(\d+(?:\.\d+)?)\+?\s*yrs"

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text
        )

        for match in matches:

            try:

                years.append(
                    float(match)
                )

            except ValueError:
                pass

    maximum_years = (
        max(years)
        if years
        else 0
    )

    if maximum_years < 2:
        return "Junior PM"

    if maximum_years < 5:
        return "Mid-level PM"

    return "Senior PM"


@manager_bp.route("/api/manager-experience", methods=["POST"])
def api_manager_experience():
    try:
        resume_text = extract_resume_text()
        experience = manager_experience_from_resume(resume_text)

        return jsonify({
            "success": True,
            "experience": experience
        })

    except Exception as error:
        print("Manager experience error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to analyze the resume."
        }), 500
