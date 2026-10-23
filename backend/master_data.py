
from flask import Blueprint, jsonify, request
import json
import re

from .supabase_client import supabase

EMPLOYEE_MASTER_TABLE = "employees"
CLIENT_MASTER_TABLE = "clients"

master_data_bp = Blueprint("master_data", __name__)


def _clean(value):
    return str(value or "").strip()


def _normalise_values(value):
    """
    Convert a value containing skills or project types into a set
    of lowercase terms.

    Supports:
    - Supabase arrays / Python lists
    - JSON-encoded arrays
    - JSON objects with enabled values
    - Comma, semicolon, pipe, or newline-separated text
    """
    if value is None:
        return set()

    if isinstance(value, (list, tuple, set)):
        values = set()

        for item in value:
            values.update(_normalise_values(item))

        return values

    if isinstance(value, dict):
        values = set()

        for key, enabled in value.items():
            if enabled:
                values.update(_normalise_values(key))

        return values

    text = str(value).strip()

    if not text:
        return set()

    if text.startswith(("[", "{")):
        try:
            parsed = json.loads(text)

            if isinstance(parsed, (list, dict)):
                return _normalise_values(parsed)

        except (ValueError, TypeError):
            pass

    # Split common delimiters and normalize case.
    parts = re.split(r"[,;|\n\r]+", text)

    return {
        part.strip().casefold()
        for part in parts
        if part.strip()
    }


def _matches_project_type(employee, project_type):
    """
    Recommend an employee if the requested project type matches
    their recorded skills OR their recorded project_types.

    No role or department fallback is used.
    """
    requested = _clean(project_type).casefold()

    if not requested:
        return False

    skills = _normalise_values(employee.get("skills"))
    project_types = _normalise_values(employee.get("project_types"))

    all_terms = skills | project_types

    # Exact matching, or a phrase contained within a recorded term.
    return any(
        requested == term
        or requested in term
        or term in requested
        for term in all_terms
    )


def _employee_payload(employee):
    return {
        "employee_id": employee.get("employee_id", ""),
        "employee_name": (
            employee.get("employee_name")
            or employee.get("name")
            or ""
        ),
        "email": employee.get("email", ""),
        "role": employee.get("role", ""),
        "department": employee.get("department", ""),
        "experience_level": employee.get("experience_level", ""),
        "years_experience": employee.get("years_experience", 0),
        "skills": employee.get("skills", ""),
        "project_types": employee.get("project_types", ""),
    }


def get_employee_by_id(employee_id):
    employee_id = _clean(employee_id)

    if not employee_id:
        return None

    response = (
        supabase.table(EMPLOYEE_MASTER_TABLE)
        .select("*")
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def get_client_by_id(client_id):
    client_id = _clean(client_id)

    if not client_id:
        return None

    response = (
        supabase.table(CLIENT_MASTER_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def get_employees_capable_for_project_type(project_type):
    """
    Return employees matching the requested project type against
    skills or project_types.

    An unknown project type returns an empty recommendation list;
    the manager can still add valid employees manually.
    """
    project_type = _clean(project_type)

    if not project_type:
        return []

    response = (
        supabase.table(EMPLOYEE_MASTER_TABLE)
        .select("*")
        .execute()
    )

    employees = response.data or []

    matches = [
        employee
        for employee in employees
        if _matches_project_type(employee, project_type)
    ]

    matches.sort(
        key=lambda employee: (
            -safe_experience(employee.get("years_experience")),
            _clean(
                employee.get("employee_name")
                or employee.get("name")
            ).casefold(),
            _clean(employee.get("employee_id")).casefold(),
        )
    )

    return matches


def safe_experience(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


@master_data_bp.route("/api/employee/<employee_id>")
def api_employee(employee_id):
    try:
        employee = get_employee_by_id(employee_id)

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee ID not found.",
            }), 404

        return jsonify({
            "success": True,
            "employee": _employee_payload(employee),
        })

    except Exception as error:
        print("Employee lookup error:", error)

        return jsonify({
            "success": False,
            "message": (
                "Unable to look up employee. "
                "Check the Flask terminal and employees table."
            ),
        }), 500


@master_data_bp.route("/api/client/<client_id>")
def api_client(client_id):
    try:
        client = get_client_by_id(client_id)

        if not client:
            return jsonify({
                "success": False,
                "message": "Client ID not found.",
            }), 404

        return jsonify({
            "success": True,
            "client": {
                "client_id": client.get("client_id", ""),
                "client_name": (
                    client.get("client_name")
                    or client.get("name")
                    or ""
                ),
                "organization": client.get("organization", ""),
                "role": client.get("role", ""),
                "email": client.get("email", ""),
            },
        })

    except Exception as error:
        print("Client lookup error:", error)

        return jsonify({
            "success": False,
            "message": (
                "Unable to look up client. "
                "Check the Flask terminal and clients table."
            ),
        }), 500


@master_data_bp.route("/api/employees/capable", methods=["GET"])
def api_capable_employees():
    project_type = _clean(request.args.get("project_type"))

    if not project_type:
        return jsonify({
            "success": True,
            "project_type": "",
            "count": 0,
            "employees": [],
        })

    try:
        employees = get_employees_capable_for_project_type(project_type)

        payload = [
            _employee_payload(employee)
            for employee in employees
        ]

        return jsonify({
            "success": True,
            "project_type": project_type,
            "count": len(payload),
            "employees": payload,
        })

    except Exception as error:
        print("Capable employee lookup error:", error)

        return jsonify({
            "success": False,
            "message": (
                "Unable to load employee recommendations. "
                "Check the Flask terminal and employees table."
            ),
            "employees": [],
        }), 500
