import logging
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

from flask import Flask, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


USERS_WORKSHEET = "Users"
SPREADSHEET_NAME = "Educational_Supplies_Logs"
VALID_ROLES = {"Admin", "Approver", "Store_Officer", "School_User", "Viewer"}
PUBLIC_USER_FIELDS = (
    "User_ID", "Full_Name", "Email", "Role", "School_ID", "Active", "Created_At"
)
ROLE_PERMISSIONS = {
    "Admin": {"*"},
    "Approver": {"view_pending_requisitions", "view_open_requisitions", "approve_requisition", "reject_requisition"},
    "Store_Officer": {"view_open_requisitions", "receive_stock", "issue_stock", "fulfill_requisition"},
    "School_User": {"submit_requisition"},
    "Viewer": {"view_public"},
}

VALID_APP_ENVIRONMENTS = {"development", "production"}
DEVELOPMENT_SECRET_KEY = "development-only-change-me"


def configure_app_security(app: Flask) -> str:
    """Apply environment-aware Flask security settings and return APP_ENV."""
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if app_env not in VALID_APP_ENVIRONMENTS:
        raise RuntimeError(
            "APP_ENV must be either 'development' or 'production'."
        )

    secret_key = os.environ.get("FORM_API_SECRET_KEY")
    if not secret_key and app_env == "production":
        raise RuntimeError("FORM_API_SECRET_KEY must be set in production.")
    if not secret_key:
        secret_key = DEVELOPMENT_SECRET_KEY
        logging.warning(
            "FORM_API_SECRET_KEY is not set; using an insecure development fallback."
        )

    app.config.update(
        APP_ENV=app_env,
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=app_env == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
    )
    return app_env


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


def public_user_record(user: dict[str, Any]) -> dict[str, Any]:
    """Return only fields that are safe to expose outside the data layer."""
    record = {field: user.get(field, "") for field in PUBLIC_USER_FIELDS}
    record["Active"] = _is_active(record["Active"])
    return record


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
    return public_user_record(user)


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


def create_user_record(
    user_id: str,
    full_name: str,
    email: str,
    role: str,
    password: str,
    school_id: str = "",
    active: bool = True,
) -> dict[str, Any]:
    """Build a worksheet-ready initial user record with a hashed password."""
    full_name = str(full_name or "").strip()
    email = str(email or "").strip().lower()
    school_id = str(school_id or "").strip()
    if not full_name:
        raise ValueError("Full_Name is required.")
    if not email:
        raise ValueError("Email is required.")
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    if role == "School_User" and not school_id:
        raise ValueError("School_ID is required for School_User.")
    if not isinstance(active, bool):
        raise ValueError("Active must be true or false.")
    return {
        "User_ID": user_id,
        "Full_Name": full_name,
        "Email": email,
        "Role": role,
        "School_ID": school_id,
        "Password_Hash": hash_password(password),
        "Active": active,
        "Created_At": datetime.now(timezone.utc).isoformat(),
    }
