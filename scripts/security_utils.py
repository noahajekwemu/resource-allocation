import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from flask import jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


USERS_WORKSHEET = "Users"
SPREADSHEET_NAME = "Educational_Supplies_Logs"
VALID_ROLES = {"Admin", "Approver", "Store_Officer", "School_User", "Viewer"}
ROLE_PERMISSIONS = {
    "Admin": {"*"},
    "Approver": {"view_pending_requisitions", "view_open_requisitions", "approve_requisition", "reject_requisition"},
    "Store_Officer": {"view_open_requisitions", "receive_stock", "issue_stock", "fulfill_requisition"},
    "School_User": {"submit_requisition"},
    "Viewer": {"view_public"},
}


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password is required.")
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        return False


def _read_users():
    try:
        from scripts import db_connector
    except (ImportError, ModuleNotFoundError):
        import db_connector
    return db_connector.read_worksheet(SPREADSHEET_NAME, USERS_WORKSHEET)


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in user.items() if str(key).lower() != "password_hash"}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        return None
    users = _read_users()
    if users.empty:
        return None
    email_column = next((column for column in users.columns if str(column).strip().lower() == "email"), None)
    if not email_column:
        raise ValueError("Users worksheet is missing Email column.")
    matches = users[users[email_column].fillna("").astype(str).str.strip().str.lower() == normalized_email]
    return None if matches.empty else matches.iloc[0].fillna("").to_dict()


def _is_active(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "yes", "1", "active"}


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = get_user_by_email(email)
    if not user or not _is_active(user.get("Active")):
        return None
    role = str(user.get("Role", "")).strip()
    if role not in VALID_ROLES:
        logging.warning("Rejected login for user with invalid role: %s", email)
        return None
    if not verify_password(password, str(user.get("Password_Hash", ""))):
        return None
    return _public_user(user)


def current_user() -> dict[str, Any] | None:
    user = session.get("user")
    return dict(user) if isinstance(user, dict) else None


def user_can(action: str, user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    permissions = ROLE_PERMISSIONS.get(str(user.get("Role", "")).strip(), set())
    return "*" in permissions or action in permissions


def require_login(view: Callable | None = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if current_user() is None:
                return jsonify({"success": False, "error": "Please log in."}), 401
            return func(*args, **kwargs)
        return wrapped
    return decorator(view) if view is not None else decorator


def require_role(*roles: str):
    invalid_roles = set(roles) - VALID_ROLES
    if invalid_roles:
        raise ValueError(f"Invalid role(s): {', '.join(sorted(invalid_roles))}")

    def decorator(func: Callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify({"success": False, "error": "Please log in."}), 401
            if user.get("Role") not in roles:
                return jsonify({"success": False, "error": "You do not have permission to perform this action."}), 403
            return func(*args, **kwargs)
        return wrapped
    return decorator


def create_user_record(user_id: str, full_name: str, email: str, role: str, password: str, school_id: str = "") -> dict[str, Any]:
    """Build a worksheet-ready initial user record with a hashed password."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return {
        "User_ID": user_id,
        "Full_Name": full_name,
        "Email": str(email).strip().lower(),
        "Role": role,
        "School_ID": school_id,
        "Password_Hash": hash_password(password),
        "Active": True,
        "Created_At": datetime.now(timezone.utc).isoformat(),
    }
