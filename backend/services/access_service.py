import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from backend.supabase_client import supabase

ACCESS_TABLE = "project_access"


def _make_credentials(project_id, role, subject_id=None):
    project_id = str(project_id)
    if role == "manager":
        username = f"manager_{project_id}"
        prefix = "Manager"
    elif role == "employee":
        username = str(subject_id)
        prefix = "Employee"
    elif role == "client":
        username = str(subject_id)
        prefix = "Client"
    else:
        raise ValueError("Invalid project access role.")

    password = f"{prefix}@{secrets.token_urlsafe(8)}"
    return username, password


def ensure_project_access(project_id, role, subject_id=None):
    project_id = str(project_id)
    subject_id = str(subject_id) if subject_id is not None else None

    query = (
        supabase.table(ACCESS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("role", role)
    )
    if subject_id is None:
        query = query.is_("subject_id", "null")
    else:
        query = query.eq("subject_id", subject_id)

    existing = query.limit(1).execute().data or []
    if existing:
        return {"username": existing[0]["username"], "password": None, "created": False}

    username, password = _make_credentials(project_id, role, subject_id)
    record = {
        "project_id": project_id,
        "role": role,
        "subject_id": subject_id,
        "username": username,
        "password_hash": generate_password_hash(password),
    }
    response = supabase.table(ACCESS_TABLE).insert(record).execute()
    if not response.data:
        raise RuntimeError("Project access credentials could not be created.")
    return {"username": username, "password": password, "created": True}


def authenticate_project_access(project_id, username, password):
    rows = (
        supabase.table(ACCESS_TABLE)
        .select("*")
        .eq("project_id", str(project_id))
        .eq("username", str(username).strip())
        .limit(1)
        .execute().data or []
    )
    if not rows:
        return None
    row = rows[0]
    if not check_password_hash(row.get("password_hash", ""), password or ""):
        return None
    return {
        "role": row.get("role"),
        "subject_id": row.get("subject_id"),
        "username": row.get("username"),
    }
