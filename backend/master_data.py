from flask import Blueprint, jsonify

from .supabase_client import supabase

# These two tables are the master records used by the project form.
# The manager enters only an ID; the application retrieves the
# remaining employee/client information automatically.
EMPLOYEE_MASTER_TABLE = "employees"
CLIENT_MASTER_TABLE = "clients"


def get_employee_by_id(employee_id):
    employee_id = (employee_id or "").strip()

    if not employee_id:
        return None

    response = (
        supabase
        .table(EMPLOYEE_MASTER_TABLE)
        .select("*")
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def get_client_by_id(client_id):
    client_id = (client_id or "").strip()

    if not client_id:
        return None

    response = (
        supabase
        .table(CLIENT_MASTER_TABLE)
        .select("*")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )

    data = response.data or []


master_data_bp = Blueprint("master_data", __name__)

@master_data_bp.route("/api/employee/<employee_id>")
def api_employee(employee_id):
    try:
        employee = get_employee_by_id(employee_id)

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee ID not found."
            }), 404

        return jsonify({
            "success": True,
            "employee": {
                "employee_id": employee.get("employee_id", ""),
                "employee_name": employee.get("employee_name", employee.get("name", "")),
                "email": employee.get("email", ""),
                "role": employee.get("role", ""),
                "department": employee.get("department", ""),
                "experience_level": employee.get("experience_level", ""),
                "years_experience": employee.get("years_experience", 0),
                "skills": employee.get("skills", "")
            }
        })

    except Exception as error:
        print("Employee lookup error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to look up employee."
        }), 500


@master_data_bp.route("/api/client/<client_id>")
def api_client(client_id):
    try:
        client = get_client_by_id(client_id)

        if not client:
            return jsonify({
                "success": False,
                "message": "Client ID not found."
            }), 404

        return jsonify({
            "success": True,
            "client": {
                "client_id": client.get("client_id", ""),
                "client_name": client.get("client_name", client.get("name", "")),
                "organization": client.get("organization", ""),
                "role": client.get("role", ""),
                "email": client.get("email", "")
            }
        })

    except Exception as error:
        print("Client lookup error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to look up client."
        }), 500
