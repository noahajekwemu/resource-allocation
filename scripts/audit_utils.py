import json
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import has_request_context, request

from scripts.security_utils import current_user


SPREADSHEET_NAME = "Educational_Supplies_Logs"
AUDIT_LOG_WORKSHEET = "Audit_Log"
AUDIT_LOG_HEADERS = [
    "Audit_ID", "Timestamp", "User_ID", "User_Email", "Role", "Action",
    "Entity_Type", "Entity_ID", "Before_State", "After_State", "IPAddress",
    "Status", "Remarks",
]
AUDIT_LOG_COLUMNS = AUDIT_LOG_HEADERS


def _json_state(state: dict[str, Any] | None) -> str:
    return json.dumps(state, sort_keys=True, default=str, separators=(",", ":"))


def _ensure_audit_headers(worksheet: Any) -> None:
    if worksheet.row_values(1) != AUDIT_LOG_HEADERS:
        worksheet.update(range_name="A1:M1", values=[AUDIT_LOG_HEADERS])


def build_audit_row(action: str, entity_type: str, entity_id: str, before_state: dict[str, Any] | None, after_state: dict[str, Any] | None, status: str, remarks: str = "", user: dict[str, Any] | None = None, ip_address: str = "") -> dict[str, Any]:
    actor = user if user is not None else (current_user() if has_request_context() else None)
    actor = actor or {}
    if has_request_context() and not ip_address:
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",", 1)[0].strip()
    return {
        "Audit_ID": f"AUD-{uuid.uuid4().hex.upper()}",
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "User_ID": actor.get("User_ID", ""),
        "User_Email": actor.get("Email", ""),
        "Role": actor.get("Role", ""),
        "Action": action,
        "Entity_Type": entity_type,
        "Entity_ID": str(entity_id or ""),
        "Before_State": _json_state(before_state),
        "After_State": _json_state(after_state),
        "IPAddress": ip_address,
        "Status": status,
        "Remarks": remarks,
    }


def write_audit_log(action: str, entity_type: str, entity_id: str, before_state: dict[str, Any] | None, after_state: dict[str, Any] | None, status: str, remarks: str = "", user: dict[str, Any] | None = None) -> dict[str, Any]:
    row = build_audit_row(action, entity_type, entity_id, before_state, after_state, status, remarks, user=user)
    try:
        from scripts import db_connector
    except (ImportError, ModuleNotFoundError):
        import db_connector
    worksheet = db_connector.connect_to_sheet(SPREADSHEET_NAME).worksheet(AUDIT_LOG_WORKSHEET)
    _ensure_audit_headers(worksheet)
    worksheet.append_row([row[column] for column in AUDIT_LOG_HEADERS])
    return row
