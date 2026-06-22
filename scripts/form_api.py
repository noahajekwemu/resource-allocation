import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_cors import CORS

try:
    from scripts.audit_utils import write_audit_log
    from scripts.security_utils import (
        authenticate_user,
        configure_app_security,
        create_user_record,
        current_user,
        hash_password,
        public_user_record,
        require_role,
        VALID_ROLES,
    )
except (ImportError, ModuleNotFoundError):
    from audit_utils import write_audit_log
    from security_utils import (
        authenticate_user,
        configure_app_security,
        create_user_record,
        current_user,
        hash_password,
        public_user_record,
        require_role,
        VALID_ROLES,
    )

try:
    from scripts.inventory_utils import calculate_available_stock
except (ImportError, ModuleNotFoundError):
    from inventory_utils import calculate_available_stock

try:
    from scripts.report_utils import (
        get_audit_report,
        get_executive_summary,
        get_fulfillment_report,
        get_requisition_report,
        get_stock_report,
        records_to_csv_response,
    )
except (ImportError, ModuleNotFoundError):
    from report_utils import (
        get_audit_report,
        get_executive_summary,
        get_fulfillment_report,
        get_requisition_report,
        get_stock_report,
        records_to_csv_response,
    )


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "forms"))
APP_ENV = configure_app_security(app)
CORS(
    app,
    resources={
        r"/health": {
            "origins": [
                "https://noahajekwemu.github.io",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            ],
            "methods": ["GET"],
        }
    },
)

SPREADSHEET_NAME = "Educational_Supplies_Logs"
ITEMS_WORKSHEET = "Items"
SCHOOLS_WORKSHEET = "Schools"
WAREHOUSES_WORKSHEET = "Warehouses"
REQUISITIONS_WORKSHEET = "Requisitions"
REQUISITION_DETAILS_WORKSHEET = "Requisition_Details"
TRANSACTIONS_WORKSHEET = "Transactions"
TRANSACTION_DETAILS_WORKSHEET = "Transaction_Details"
USERS_WORKSHEET = "Users"
BASE_DIR = Path(__file__).resolve().parent.parent
FORMS_DIR = BASE_DIR / "forms"
FORM_PAGE_ROLES = {
    "approve_requisition.html": {"Admin", "Approver"},
    "receive_stock.html": {"Admin", "Store_Officer"},
    "issue_stock.html": {"Admin", "Store_Officer"},
    "requisition_form.html": {"Admin", "School_User"},
    "user_management.html": {"Admin"},
    "reports.html": {"Admin", "Viewer", "Approver", "Store_Officer", "School_User"},
    "print_executive_summary.html": {"Admin", "Viewer", "Approver", "Store_Officer"},
}
ROLE_DEFAULT_REDIRECTS = {
    "Admin": "/forms/approve_requisition.html",
    "Approver": "/forms/approve_requisition.html",
    "Store_Officer": "/forms/issue_stock.html",
    "School_User": "/forms/requisition_form.html",
    "Viewer": "/forms/reports.html",
}
SAFE_API_REDIRECTS = {"/api/items", "/api/schools", "/api/warehouses"}


@app.get("/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/me")
def current_user_route():
    user = current_user()
    if user is None:
        return jsonify({"authenticated": False})
    return jsonify({
        "authenticated": True,
        "user_id": user.get("User_ID", ""),
        "email": user.get("Email", ""),
        "full_name": user.get("Full_Name", ""),
        "role": user.get("Role", ""),
        "school_id": user.get("School_ID", ""),
    })


@app.after_request
def add_no_cache_headers(response):
    is_protected_form = request.path.startswith("/forms/")
    is_authenticated_response = (
        current_user() is not None and request.path.startswith("/api/")
    )
    if is_protected_form or is_authenticated_response:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(403)
def forbidden_error(_error):
    return jsonify({"success": False, "error": "Access forbidden."}), 403


@app.errorhandler(404)
def not_found_error(_error):
    return jsonify({"success": False, "error": "Resource not found."}), 404


@app.errorhandler(500)
def internal_server_error(_error):
    logging.error("Unhandled server error")
    return jsonify(
        {"success": False, "error": "An unexpected server error occurred."}
    ), 500


def _safe_next_path(value: Any, user: dict[str, Any] | None = None) -> str:
    path = str(value or "").strip()
    if not path.startswith("/") or path.startswith("//") or "?" in path or "#" in path:
        return ""
    if path in SAFE_API_REDIRECTS:
        return path
    prefix = "/forms/"
    if not path.startswith(prefix):
        return ""
    filename = path.removeprefix(prefix)
    if "/" in filename or "\\" in filename:
        return ""
    allowed_roles = FORM_PAGE_ROLES.get(filename)
    if allowed_roles is None:
        return ""
    if user is not None and user.get("Role") not in allowed_roles:
        return ""
    return path


def _default_redirect_for(user: dict[str, Any]) -> str:
    return ROLE_DEFAULT_REDIRECTS.get(str(user.get("Role", "")), "/api/items")


def _request_payload() -> dict[str, Any]:
    if not request.is_json:
        raise ValueError("Request body must be JSON.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def _audit(action: str, entity_type: str, entity_id: str = "", before_state=None, after_state=None, status: str = "Success", remarks: str = "", user=None) -> None:
    try:
        write_audit_log(action, entity_type, entity_id, before_state, after_state, status, remarks, user=user)
    except Exception as exc:
        logging.exception("Failed to write audit log for %s: %s", action, exc)


def _load_db_connector() -> Any:
    """Load db_connector when an operation needs Google Sheets access."""
    try:
        from scripts import db_connector
    except (ImportError, ModuleNotFoundError):
        import importlib.util

        connector_path = Path(__file__).resolve().with_name("db_connector.py")
        spec = importlib.util.spec_from_file_location("db_connector", connector_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load db_connector from {connector_path}")

        db_connector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db_connector)

    return db_connector


def _read_worksheet(worksheet_name: str) -> pd.DataFrame:
    """Read a worksheet through db_connector."""
    db_connector = _load_db_connector()
    return db_connector.read_worksheet(SPREADSHEET_NAME, worksheet_name)


def _append_row(worksheet_name: str, row: list[Any]) -> None:
    """Append a row to a worksheet through db_connector."""
    db_connector = _load_db_connector()
    db_connector.append_row(SPREADSHEET_NAME, worksheet_name, row)


def _worksheet_headers(worksheet_name: str) -> list[str]:
    """Return first-row worksheet headers through db_connector."""
    db_connector = _load_db_connector()
    worksheet = db_connector.connect_to_sheet(SPREADSHEET_NAME).worksheet(worksheet_name)
    return worksheet.row_values(1)


def _append_dict_row(worksheet_name: str, values: dict[str, Any]) -> None:
    """Append a dictionary row using the worksheet header order."""
    headers = _worksheet_headers(worksheet_name)
    if not headers:
        raise ValueError(f"{worksheet_name} worksheet must have a header row.")

    row = [values.get(header, "") for header in headers]
    _append_row(worksheet_name, row)


def _worksheet(worksheet_name: str):
    """Return a worksheet object through db_connector."""
    db_connector = _load_db_connector()
    return db_connector.connect_to_sheet(SPREADSHEET_NAME).worksheet(worksheet_name)


def _update_row_by_id(
    worksheet_name: str,
    id_column_candidates: list[str],
    row_id: str,
    values: dict[str, Any],
) -> None:
    """Update selected columns on the first worksheet row matching an ID."""
    dataframe = _read_worksheet(worksheet_name)
    if dataframe.empty:
        raise ValueError(f"{worksheet_name} worksheet is empty.")

    id_column = _find_column(dataframe, id_column_candidates)
    row_matches = dataframe[
        dataframe[id_column].fillna("").astype(str).str.strip() == str(row_id).strip()
    ]
    if row_matches.empty:
        raise ValueError(f"{worksheet_name} row not found for ID {row_id}.")

    headers = _worksheet_headers(worksheet_name)
    normalized_headers = {
        _normalize_column_name(header): index + 1 for index, header in enumerate(headers)
    }
    sheet_row = int(row_matches.index[0]) + 2
    worksheet = _worksheet(worksheet_name)

    for column_name, value in values.items():
        normalized_column = _normalize_column_name(column_name)
        if normalized_column not in normalized_headers:
            continue
        worksheet.update_cell(sheet_row, normalized_headers[normalized_column], value)


def _normalize_column_name(column_name: str) -> str:
    """Normalize a column name for flexible matching."""
    return str(column_name).strip().lower().replace(" ", "_")


def _find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = True,
) -> str | None:
    """Find a dataframe column using one or more possible names."""
    normalized_columns = {
        _normalize_column_name(column): column for column in dataframe.columns
    }

    for candidate in candidates:
        normalized_candidate = _normalize_column_name(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    if required:
        raise ValueError(f"Missing required column. Expected one of: {', '.join(candidates)}")

    return None


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any, field_name: str = "quantity") -> int:
    """Convert worksheet or payload quantity values to an integer."""
    if pd.isna(value) or str(value).strip() == "":
        return 0

    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def _current_year() -> str:
    """Return the current year used in generated IDs."""
    return datetime.now(timezone.utc).strftime("%Y")


def _next_id(worksheet_name: str, id_column_candidates: list[str], prefix: str) -> str:
    """Generate the next sequential ID for the current year."""
    year = _current_year()
    dataframe = _read_worksheet(worksheet_name)

    if dataframe.empty:
        return f"{prefix}-{year}-000001"

    id_column = _find_column(dataframe, id_column_candidates, required=False)
    if not id_column:
        return f"{prefix}-{year}-000001"

    pattern = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$")
    highest_number = 0

    for value in dataframe[id_column].fillna("").astype(str):
        match = pattern.match(value.strip())
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return f"{prefix}-{year}-{highest_number + 1:06d}"


def _next_compact_id(worksheet_name: str, id_column_candidates: list[str], prefix: str) -> str:
    """Generate compact sequential IDs like REQ001 and RD001."""
    dataframe = _read_worksheet(worksheet_name)

    if dataframe.empty:
        return f"{prefix}001"

    id_column = _find_column(dataframe, id_column_candidates, required=False)
    if not id_column:
        return f"{prefix}001"

    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    highest_number = 0

    for value in dataframe[id_column].fillna("").astype(str):
        match = pattern.match(value.strip())
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return f"{prefix}{highest_number + 1:03d}"


def _next_detail_ids(count: int) -> list[str]:
    """Generate the next detail IDs for a multi-item transaction."""
    first_id = _next_id(TRANSACTION_DETAILS_WORKSHEET, ["Detail_ID", "Detail ID"], "TD")
    prefix, year, number = first_id.split("-")
    start_number = int(number)
    return [f"{prefix}-{year}-{start_number + index:06d}" for index in range(count)]


def _next_requisition_detail_ids(count: int) -> list[str]:
    """Generate the next requisition detail IDs for requested line items."""
    first_id = _next_compact_id(
        REQUISITION_DETAILS_WORKSHEET,
        ["Req_Detail_ID", "Requisition_Detail_ID", "Detail_ID", "Req Detail ID"],
        "RD",
    )
    start_number = int(first_id.removeprefix("RD"))
    return [f"RD{start_number + index:03d}" for index in range(count)]


def _clean_line_items(line_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize transaction detail rows."""
    cleaned_items = []

    for index, line_item in enumerate(line_items, start=1):
        item_id = str(line_item.get("Item_ID") or line_item.get("item_id") or "").strip()
        condition = str(line_item.get("Condition") or line_item.get("condition") or "Good").strip()

        try:
            quantity = int(line_item.get("Quantity") or line_item.get("quantity") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Line {index}: quantity must be a number.") from exc

        if not item_id:
            raise ValueError(f"Line {index}: Item_ID is required.")
        if quantity <= 0:
            raise ValueError(f"Line {index}: quantity must be greater than zero.")

        cleaned_items.append(
            {
                "Item_ID": item_id,
                "Quantity": quantity,
                "Condition": condition or "Good",
            }
        )

    if not cleaned_items:
        raise ValueError("At least one item row is required.")

    return cleaned_items


def _clean_requisition_items(line_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize requisition detail rows."""
    cleaned_items = []

    for index, line_item in enumerate(line_items, start=1):
        item_id = str(line_item.get("Item_ID") or line_item.get("item_id") or "").strip()

        try:
            quantity = int(
                line_item.get("Quantity_Requested")
                or line_item.get("quantity_requested")
                or line_item.get("Quantity")
                or line_item.get("quantity")
                or 0
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Line {index}: quantity must be a number.") from exc

        if not item_id:
            raise ValueError(f"Line {index}: Item_ID is required.")
        if quantity <= 0:
            raise ValueError(f"Line {index}: quantity must be greater than zero.")

        cleaned_items.append(
            {
                "Item_ID": item_id,
                "Quantity_Requested": quantity,
            }
        )

    if not cleaned_items:
        raise ValueError("At least one item row is required.")

    return cleaned_items


def _id_values_exist(
    worksheet_name: str,
    id_column_candidates: list[str],
    requested_ids: set[str],
    label: str,
) -> None:
    """Validate that requested IDs exist in a lookup worksheet."""
    dataframe = _read_worksheet(worksheet_name)
    id_column = _find_column(dataframe, id_column_candidates)
    valid_ids = set(dataframe[id_column].fillna("").astype(str).str.strip())
    missing_ids = sorted(requested_id for requested_id in requested_ids if requested_id not in valid_ids)

    if missing_ids:
        raise ValueError(f"Unknown {label}: {', '.join(missing_ids)}")


def get_items() -> list[dict[str, Any]]:
    """Return item records for form dropdowns."""
    return _read_worksheet(ITEMS_WORKSHEET).to_dict(orient="records")


def get_schools() -> list[dict[str, Any]]:
    """Return school records for form dropdowns."""
    return _read_worksheet(SCHOOLS_WORKSHEET).to_dict(orient="records")


def get_warehouses() -> list[dict[str, Any]]:
    """Return warehouse records for form dropdowns."""
    return _read_worksheet(WAREHOUSES_WORKSHEET).to_dict(orient="records")


def get_users() -> list[dict[str, Any]]:
    """Return user records with an explicit public-field allowlist."""
    users = _read_worksheet(USERS_WORKSHEET)
    if users.empty:
        return []
    return [public_user_record(row) for row in users.fillna("").to_dict(orient="records")]


def _user_record(user_id: str) -> dict[str, Any]:
    users = _read_worksheet(USERS_WORKSHEET)
    if users.empty:
        raise ValueError(f"User not found: {user_id}")
    id_column = _find_column(users, ["User_ID", "User ID"])
    matches = users[
        users[id_column].fillna("").astype(str).str.strip() == str(user_id).strip()
    ]
    if matches.empty:
        raise ValueError(f"User not found: {user_id}")
    return matches.iloc[0].fillna("").to_dict()


def _next_user_id(users: pd.DataFrame) -> str:
    if users.empty:
        return "USR001"
    id_column = _find_column(users, ["User_ID", "User ID"], required=False)
    highest = 0
    if id_column:
        for value in users[id_column].fillna("").astype(str):
            match = re.fullmatch(r"USR(\d+)", value.strip(), re.IGNORECASE)
            if match:
                highest = max(highest, int(match.group(1)))
    return f"USR{highest + 1:03d}"


def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    users = _read_worksheet(USERS_WORKSHEET)
    email = str(payload.get("Email", "")).strip().lower()
    if not users.empty:
        email_column = _find_column(users, ["Email"])
        existing = users[email_column].fillna("").astype(str).str.strip().str.lower()
        if email and existing.eq(email).any():
            raise ValueError("Email already exists.")
    record = create_user_record(
        _next_user_id(users),
        payload.get("Full_Name", ""),
        email,
        str(payload.get("Role", "")).strip(),
        payload.get("Password", ""),
        payload.get("School_ID", ""),
        payload.get("Active", True),
    )
    _append_dict_row(USERS_WORKSHEET, record)
    return public_user_record(record)


def update_user(user_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    allowed_fields = {"Full_Name", "Role", "School_ID", "Active"}
    invalid_fields = set(payload) - allowed_fields
    if invalid_fields:
        raise ValueError(f"Fields cannot be updated: {', '.join(sorted(invalid_fields))}.")
    if not payload:
        raise ValueError("At least one user field is required.")

    before_record = _user_record(user_id)
    updates = dict(payload)
    if "Full_Name" in updates:
        updates["Full_Name"] = str(updates["Full_Name"] or "").strip()
        if not updates["Full_Name"]:
            raise ValueError("Full_Name is required.")
    if "Role" in updates:
        updates["Role"] = str(updates["Role"] or "").strip()
        if updates["Role"] not in VALID_ROLES:
            raise ValueError(f"Invalid role: {updates['Role']}")
    if "School_ID" in updates:
        updates["School_ID"] = str(updates["School_ID"] or "").strip()
    if "Active" in updates and not isinstance(updates["Active"], bool):
        raise ValueError("Active must be true or false.")

    after_record = {**before_record, **updates}
    if after_record.get("Role") == "School_User" and not str(
        after_record.get("School_ID", "")
    ).strip():
        raise ValueError("School_ID is required for School_User.")
    _update_row_by_id(USERS_WORKSHEET, ["User_ID", "User ID"], user_id, updates)
    return public_user_record(before_record), public_user_record(after_record)


def get_available_stock(item_id: str) -> int:
    """Calculate available stock for an item from normalized transactions."""
    return calculate_available_stock(item_id)


def _decorate_requisition_details(details: pd.DataFrame) -> list[dict[str, Any]]:
    """Return requisition detail rows with available stock values."""
    if details.empty:
        return []

    item_column = _find_column(details, ["Item_ID", "Item ID"])
    requested_column = _find_column(details, ["Quantity_Requested", "Requested Quantity"])
    approved_column = _find_column(
        details, ["Quantity_Approved", "Approved Quantity"], required=False
    )
    detail_id_column = _find_column(
        details, ["Req_Detail_ID", "Requisition_Detail_ID", "Detail_ID", "Req Detail ID"]
    )

    decorated = []
    for _, row in details.iterrows():
        item_id = str(row[item_column]).strip()
        requested_quantity = _to_int(row[requested_column], "Quantity_Requested")
        approved_quantity = (
            _to_int(row[approved_column], "Quantity_Approved") if approved_column else 0
        )
        record = row.to_dict()
        record["Req_Detail_ID"] = str(row[detail_id_column]).strip()
        record["Item_ID"] = item_id
        record["Quantity_Requested"] = requested_quantity
        record["Quantity_Approved"] = approved_quantity
        record["Available_Stock"] = calculate_available_stock(item_id)
        decorated.append(record)

    return decorated


def _decorate_open_requisition_details(details: pd.DataFrame) -> list[dict[str, Any]]:
    """Return approved requisition details that still have quantities to fulfill."""
    if details.empty:
        return []

    approved_column = _find_column(
        details, ["Quantity_Approved", "Approved Quantity"], required=False
    )
    fulfilled_column = _find_column(
        details, ["Quantity_Fulfilled", "Fulfilled Quantity"], required=False
    )

    decorated = []
    for record in details.fillna("").to_dict("records"):
        approved_quantity = (
            _to_int(record.get(approved_column), "Quantity_Approved")
            if approved_column
            else 0
        )
        fulfilled_quantity = (
            _to_int(record.get(fulfilled_column), "Quantity_Fulfilled")
            if fulfilled_column
            else 0
        )
        remaining_quantity = approved_quantity - fulfilled_quantity
        if remaining_quantity <= 0:
            continue

        record["Quantity_Approved"] = approved_quantity
        record["Quantity_Fulfilled"] = fulfilled_quantity
        record["Quantity_Remaining"] = remaining_quantity
        decorated.append(record)

    return decorated


def get_pending_requisitions() -> list[dict[str, Any]]:
    """Return requisitions that are still pending approval."""
    requisitions = _read_worksheet(REQUISITIONS_WORKSHEET)
    if requisitions.empty:
        return []

    status_column = _find_column(requisitions, ["Status"])
    pending = requisitions[
        requisitions[status_column].fillna("").astype(str).str.strip().str.lower()
        == "pending"
    ]
    return pending.to_dict(orient="records")


def get_open_requisitions() -> list[dict[str, Any]]:
    """Return approved requisitions with remaining quantities to fulfill."""
    requisitions = _read_worksheet(REQUISITIONS_WORKSHEET)
    if requisitions.empty:
        return []

    details = _read_worksheet(REQUISITION_DETAILS_WORKSHEET)
    schools = _read_worksheet(SCHOOLS_WORKSHEET)

    requisition_id_column = _find_column(requisitions, ["Requisition_ID", "Requisition ID"])
    status_column = _find_column(requisitions, ["Status"])
    school_id_column = _find_column(
        requisitions, ["School_ID", "School ID"], required=False
    )
    detail_requisition_id_column = _find_column(
        details, ["Requisition_ID", "Requisition ID"], required=False
    )

    school_name_by_id: dict[str, str] = {}
    if not schools.empty:
        schools_id_column = _find_column(schools, ["School_ID", "School ID"], required=False)
        school_name_column = _find_column(
            schools, ["School_Name", "School Name", "School"], required=False
        )
        if schools_id_column and school_name_column:
            for _, school in schools.iterrows():
                school_id = str(school.get(schools_id_column, "")).strip()
                if school_id:
                    school_name_by_id[school_id] = str(
                        school.get(school_name_column, "")
                    ).strip()

    open_statuses = {"approved", "partially fulfilled"}
    open_rows = requisitions[
        requisitions[status_column].fillna("").astype(str).str.strip().str.lower().isin(
            open_statuses
        )
    ]

    open_requisitions = []
    for _, row in open_rows.iterrows():
        requisition_id = str(row[requisition_id_column]).strip()
        detail_rows = pd.DataFrame()
        if not details.empty and detail_requisition_id_column:
            detail_rows = details[
                details[detail_requisition_id_column].fillna("").astype(str).str.strip()
                == requisition_id
            ]
        open_details = _decorate_open_requisition_details(detail_rows)
        if not open_details:
            continue

        record = row.fillna("").to_dict()
        if school_id_column:
            school_id = str(record.get(school_id_column, "")).strip()
            record["School_Name"] = school_name_by_id.get(school_id, "")
        record["details"] = open_details
        open_requisitions.append(record)

    return open_requisitions


def get_requisition(requisition_id: str) -> dict[str, Any]:
    """Return a requisition header and its detail rows."""
    requisition_id = str(requisition_id).strip()
    requisitions = _read_worksheet(REQUISITIONS_WORKSHEET)
    details = _read_worksheet(REQUISITION_DETAILS_WORKSHEET)

    if requisitions.empty:
        raise ValueError("Requisitions worksheet is empty.")

    requisition_id_column = _find_column(requisitions, ["Requisition_ID", "Requisition ID"])
    matches = requisitions[
        requisitions[requisition_id_column].fillna("").astype(str).str.strip()
        == requisition_id
    ]
    if matches.empty:
        raise ValueError(f"Requisition not found: {requisition_id}")

    detail_rows = details.iloc[0:0]
    if not details.empty:
        detail_requisition_id_column = _find_column(
            details, ["Requisition_ID", "Requisition ID"]
        )
        detail_rows = details[
            details[detail_requisition_id_column].fillna("").astype(str).str.strip()
            == requisition_id
        ]

    return {
        "header": matches.iloc[0].to_dict(),
        "details": _decorate_requisition_details(detail_rows),
    }


def _status_for_requisition(requisition_id: str) -> str:
    requisitions = _read_worksheet(REQUISITIONS_WORKSHEET)
    requisition_id_column = _find_column(requisitions, ["Requisition_ID", "Requisition ID"])
    status_column = _find_column(requisitions, ["Status"])
    matches = requisitions[
        requisitions[requisition_id_column].fillna("").astype(str).str.strip()
        == str(requisition_id).strip()
    ]
    if matches.empty:
        raise ValueError(f"Requisition not found: {requisition_id}")
    return str(matches.iloc[0][status_column]).strip()


def _require_pending_requisition(requisition_id: str) -> None:
    status = _status_for_requisition(requisition_id)
    if status.lower() != "pending":
        raise ValueError(f"Only Pending requisitions can be changed. Current status is {status}.")


def _clean_approval_items(
    payload_items: list[dict[str, Any]],
    stored_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate approved quantities against request and inventory limits."""
    stored_by_detail_id = {
        str(detail["Req_Detail_ID"]).strip(): detail for detail in stored_details
    }
    cleaned = []

    for index, item in enumerate(payload_items, start=1):
        detail_id = str(
            item.get("Req_Detail_ID")
            or item.get("req_detail_id")
            or item.get("Detail_ID")
            or ""
        ).strip()
        if not detail_id:
            raise ValueError(f"Line {index}: Req_Detail_ID is required.")
        if detail_id not in stored_by_detail_id:
            raise ValueError(f"Line {index}: Req_Detail_ID is not part of this requisition.")

        approved_quantity = _to_int(
            item.get("Quantity_Approved")
            if "Quantity_Approved" in item
            else item.get("quantity_approved"),
            "Quantity_Approved",
        )
        if approved_quantity < 0:
            raise ValueError(f"Line {index}: approved quantity cannot be negative.")

        stored_detail = stored_by_detail_id[detail_id]
        requested_quantity = stored_detail["Quantity_Requested"]
        if approved_quantity > requested_quantity:
            raise ValueError(
                f"Line {index}: approved quantity cannot exceed requested quantity."
            )

        cleaned.append(
            {
                "Req_Detail_ID": detail_id,
                "Item_ID": stored_detail["Item_ID"],
                "Quantity_Requested": requested_quantity,
                "Quantity_Approved": approved_quantity,
                "Available_Stock": stored_detail["Available_Stock"],
            }
        )

    if not cleaned:
        raise ValueError("At least one requisition detail row is required.")

    requested_detail_ids = {item["Req_Detail_ID"] for item in cleaned}
    missing_detail_ids = [
        detail["Req_Detail_ID"]
        for detail in stored_details
        if detail["Req_Detail_ID"] not in requested_detail_ids
    ]
    if missing_detail_ids:
        raise ValueError(
            "Approval is missing requisition detail rows: " + ", ".join(missing_detail_ids)
        )

    approved_by_item: dict[str, int] = {}
    available_by_item: dict[str, int] = {}
    for item in cleaned:
        item_id = item["Item_ID"]
        approved_by_item[item_id] = approved_by_item.get(item_id, 0) + item["Quantity_Approved"]
        available_by_item[item_id] = item["Available_Stock"]

    insufficient_items = [
        f"{item_id}: approved {approved_quantity}, available {available_by_item[item_id]}"
        for item_id, approved_quantity in approved_by_item.items()
        if approved_quantity > available_by_item[item_id]
    ]
    if insufficient_items:
        raise ValueError("Insufficient stock for approval: " + "; ".join(insufficient_items))

    return cleaned


def approve_requisition(payload: dict[str, Any]) -> dict[str, Any]:
    """Approve a pending requisition and store approved quantities."""
    requisition_id = str(
        payload.get("Requisition_ID") or payload.get("requisition_id") or ""
    ).strip()
    approved_by = str(payload.get("Approved_By") or payload.get("approved_by") or "").strip()
    remarks = str(payload.get("Remarks") or payload.get("remarks") or "").strip()

    if not requisition_id:
        raise ValueError("Requisition_ID is required.")
    if not approved_by:
        raise ValueError("Approved_By is required.")

    _require_pending_requisition(requisition_id)
    requisition = get_requisition(requisition_id)
    cleaned_items = _clean_approval_items(payload.get("items", []), requisition["details"])

    for item in cleaned_items:
        _update_row_by_id(
            REQUISITION_DETAILS_WORKSHEET,
            ["Req_Detail_ID", "Requisition_Detail_ID", "Detail_ID", "Req Detail ID"],
            item["Req_Detail_ID"],
            {"Quantity_Approved": item["Quantity_Approved"]},
        )

    _update_row_by_id(
        REQUISITIONS_WORKSHEET,
        ["Requisition_ID", "Requisition ID"],
        requisition_id,
        {
            "Status": "Approved",
            "Approved_By": approved_by,
            "Approval_Date": _now_iso(),
            "Remarks": remarks,
        },
    )

    return {"success": True, "requisition_id": requisition_id, "status": "Approved"}


def reject_requisition(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject a pending requisition."""
    requisition_id = str(
        payload.get("Requisition_ID") or payload.get("requisition_id") or ""
    ).strip()
    remarks = str(payload.get("Remarks") or payload.get("remarks") or "").strip()

    if not requisition_id:
        raise ValueError("Requisition_ID is required.")

    _require_pending_requisition(requisition_id)
    _update_row_by_id(
        REQUISITIONS_WORKSHEET,
        ["Requisition_ID", "Requisition ID"],
        requisition_id,
        {
            "Status": "Rejected",
            "Remarks": remarks,
        },
    )

    return {"success": True, "requisition_id": requisition_id, "status": "Rejected"}


def _require_fulfillable_requisition(requisition_id: str) -> str:
    status = _status_for_requisition(requisition_id)
    normalized_status = status.strip().lower()
    if normalized_status not in {"approved", "partially fulfilled"}:
        raise ValueError(
            "Only Approved or Partially Fulfilled requisitions can be fulfilled. "
            f"Current status is {status}."
        )
    return status


def _requisition_details_for_fulfillment(requisition_id: str) -> list[dict[str, Any]]:
    details = _read_worksheet(REQUISITION_DETAILS_WORKSHEET)
    if details.empty:
        raise ValueError("Requisition_Details worksheet is empty.")

    requisition_id_column = _find_column(details, ["Requisition_ID", "Requisition ID"])
    detail_id_column = _find_column(
        details, ["Req_Detail_ID", "Requisition_Detail_ID", "Detail_ID", "Req Detail ID"]
    )
    item_id_column = _find_column(details, ["Item_ID", "Item ID"])
    approved_column = _find_column(details, ["Quantity_Approved", "Approved Quantity"])
    fulfilled_column = _find_column(
        details, ["Quantity_Fulfilled", "Fulfilled Quantity"], required=False
    )

    detail_rows = details[
        details[requisition_id_column].fillna("").astype(str).str.strip()
        == str(requisition_id).strip()
    ]
    if detail_rows.empty:
        raise ValueError(f"Requisition has no detail rows: {requisition_id}")

    normalized_details = []
    for _, row in detail_rows.iterrows():
        approved_quantity = _to_int(row[approved_column], "Quantity_Approved")
        fulfilled_quantity = (
            _to_int(row[fulfilled_column], "Quantity_Fulfilled")
            if fulfilled_column
            else 0
        )
        normalized_details.append(
            {
                "Req_Detail_ID": str(row[detail_id_column]).strip(),
                "Item_ID": str(row[item_id_column]).strip(),
                "Quantity_Approved": approved_quantity,
                "Quantity_Fulfilled": fulfilled_quantity,
                "Quantity_Remaining": approved_quantity - fulfilled_quantity,
            }
        )

    return normalized_details


def _validate_fulfillment_items(
    requisition_id: str,
    line_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _require_fulfillable_requisition(requisition_id)
    requisition_details = _requisition_details_for_fulfillment(requisition_id)

    requested_by_item: dict[str, int] = {}
    remaining_by_item: dict[str, int] = {}
    for line_item in line_items:
        item_id = line_item["Item_ID"]
        requested_by_item[item_id] = requested_by_item.get(item_id, 0) + line_item["Quantity"]
    for detail in requisition_details:
        item_id = detail["Item_ID"]
        remaining_by_item[item_id] = remaining_by_item.get(item_id, 0) + max(
            detail["Quantity_Remaining"], 0
        )

    errors = []
    for item_id, requested_quantity in requested_by_item.items():
        remaining_quantity = remaining_by_item.get(item_id, 0)
        if requested_quantity > remaining_quantity:
            errors.append(
                f"{item_id}: requested {requested_quantity}, remaining {remaining_quantity}"
            )

    if errors:
        raise ValueError("Fulfillment exceeds approved quantity for: " + "; ".join(errors))

    return requisition_details


def _fulfillment_status(details: list[dict[str, Any]]) -> str:
    approved_total = sum(detail["Quantity_Approved"] for detail in details)
    fulfilled_total = sum(detail["Quantity_Fulfilled"] for detail in details)

    if approved_total > 0 and fulfilled_total >= approved_total:
        return "Fulfilled"
    if fulfilled_total > 0:
        return "Partially Fulfilled"
    return "Approved"


def update_fulfillment(transaction_id: str) -> dict[str, Any]:
    """Apply an OUT transaction's quantities to its linked requisition."""
    transaction_id = str(transaction_id).strip()
    if not transaction_id:
        raise ValueError("Transaction_ID is required.")

    transactions = _read_worksheet(TRANSACTIONS_WORKSHEET)
    transaction_details = _read_worksheet(TRANSACTION_DETAILS_WORKSHEET)
    if transactions.empty:
        raise ValueError("Transactions worksheet is empty.")
    if transaction_details.empty:
        raise ValueError("Transaction_Details worksheet is empty.")

    transaction_id_column = _find_column(transactions, ["Transaction_ID", "Transaction ID"])
    transaction_type_column = _find_column(
        transactions, ["Transaction_Type", "Transaction Type", "Type"]
    )
    requisition_id_column = _find_column(transactions, ["Requisition_ID", "Requisition ID"])
    matches = transactions[
        transactions[transaction_id_column].fillna("").astype(str).str.strip()
        == transaction_id
    ]
    if matches.empty:
        raise ValueError(f"Transaction not found: {transaction_id}")

    transaction = matches.iloc[0]
    transaction_type = str(transaction[transaction_type_column]).strip().upper()
    if transaction_type != "OUT":
        raise ValueError("Only OUT transactions can update requisition fulfillment.")

    requisition_id = str(transaction[requisition_id_column]).strip()
    if not requisition_id:
        raise ValueError("Transaction is not linked to a Requisition_ID.")

    detail_transaction_id_column = _find_column(
        transaction_details, ["Transaction_ID", "Transaction ID"]
    )
    item_id_column = _find_column(transaction_details, ["Item_ID", "Item ID"])
    quantity_column = _find_column(transaction_details, ["Quantity", "Qty"])
    transaction_detail_rows = transaction_details[
        transaction_details[detail_transaction_id_column].fillna("").astype(str).str.strip()
        == transaction_id
    ]
    if transaction_detail_rows.empty:
        raise ValueError(f"Transaction has no detail rows: {transaction_id}")

    line_items = []
    for _, row in transaction_detail_rows.iterrows():
        line_items.append(
            {
                "Item_ID": str(row[item_id_column]).strip(),
                "Quantity": _to_int(row[quantity_column], "Quantity"),
            }
        )

    requisition_details = _validate_fulfillment_items(requisition_id, line_items)
    quantities_by_item: dict[str, int] = {}
    for line_item in line_items:
        item_id = line_item["Item_ID"]
        quantities_by_item[item_id] = quantities_by_item.get(item_id, 0) + line_item["Quantity"]

    updated_details = []
    for detail in requisition_details:
        remaining_issue_quantity = quantities_by_item.get(detail["Item_ID"], 0)
        if remaining_issue_quantity <= 0:
            updated_details.append(detail)
            continue

        applied_quantity = min(max(detail["Quantity_Remaining"], 0), remaining_issue_quantity)
        quantities_by_item[detail["Item_ID"]] = remaining_issue_quantity - applied_quantity
        updated_detail = dict(detail)
        updated_detail["Quantity_Fulfilled"] = (
            detail["Quantity_Fulfilled"] + applied_quantity
        )
        _update_row_by_id(
            REQUISITION_DETAILS_WORKSHEET,
            ["Req_Detail_ID", "Requisition_Detail_ID", "Detail_ID", "Req Detail ID"],
            detail["Req_Detail_ID"],
            {"Quantity_Fulfilled": updated_detail["Quantity_Fulfilled"]},
        )
        updated_details.append(updated_detail)

    status = _fulfillment_status(updated_details)
    _update_row_by_id(
        REQUISITIONS_WORKSHEET,
        ["Requisition_ID", "Requisition ID"],
        requisition_id,
        {"Status": status},
    )

    return {
        "success": True,
        "transaction_id": transaction_id,
        "requisition_id": requisition_id,
        "status": status,
    }


def _validate_out_stock(line_items: list[dict[str, Any]]) -> None:
    """Reject OUT transactions when requested quantities exceed available stock."""
    errors = []
    requested_by_item: dict[str, int] = {}

    for line_item in line_items:
        item_id = line_item["Item_ID"]
        requested_by_item[item_id] = requested_by_item.get(item_id, 0) + line_item["Quantity"]

    for item_id, requested_quantity in requested_by_item.items():
        available_quantity = get_available_stock(item_id)

        if available_quantity < requested_quantity:
            errors.append(
                f"{item_id}: requested {requested_quantity}, available {available_quantity}"
            )

    if errors:
        raise ValueError("Insufficient stock for: " + "; ".join(errors))


def _submit_transaction(
    transaction_type: str,
    payload: dict[str, Any],
    validate_stock: bool = False,
) -> dict[str, Any]:
    """Save a transaction header and its line items."""
    line_items = _clean_line_items(payload.get("items", []))

    if validate_stock:
        _validate_out_stock(line_items)

    transaction_id = _next_id(TRANSACTIONS_WORKSHEET, ["Transaction_ID", "Transaction ID"], "TXN")
    transaction_date = payload.get("Transaction_Date") or payload.get("transaction_date") or _now_iso()
    warehouse_id = payload.get("Warehouse_ID") or payload.get("warehouse_id") or ""
    school_id = (
        payload.get("Destination_School_ID")
        or payload.get("destination_school_id")
        or payload.get("School_ID")
        or payload.get("school_id")
        or ""
    )

    header = {
        "Transaction_ID": transaction_id,
        "Transaction_Date": transaction_date,
        "Transaction_Type": transaction_type,
        "Warehouse_ID": warehouse_id,
        "Destination_School_ID": school_id,
        "Requisition_ID": payload.get("Requisition_ID") or payload.get("requisition_id") or "",
        "Source": payload.get("Source") or payload.get("source") or "",
        "Status": payload.get("Status") or payload.get("status") or "Completed",
        "Remarks": payload.get("Remarks") or payload.get("remarks") or "",
    }

    logging.info("Submitting %s transaction %s", transaction_type, transaction_id)
    _append_dict_row(TRANSACTIONS_WORKSHEET, header)

    detail_ids = _next_detail_ids(len(line_items))
    for detail_id, line_item in zip(detail_ids, line_items):
        _append_dict_row(
            TRANSACTION_DETAILS_WORKSHEET,
            {
                "Detail_ID": detail_id,
                "Transaction_ID": transaction_id,
                "Item_ID": line_item["Item_ID"],
                "Quantity": line_item["Quantity"],
                "Condition": line_item["Condition"],
            },
        )

    return {
        "transaction_id": transaction_id,
        "detail_ids": detail_ids,
        "line_items": len(line_items),
        "status": "success",
    }


def submit_receive_stock(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit an IN transaction with one or more item rows."""
    try:
        return _submit_transaction("IN", payload)
    except Exception as exc:
        logging.exception("Failed to submit receive stock transaction: %s", exc)
        raise


def submit_issue_stock(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit an OUT transaction after stock validation."""
    try:
        requisition_id = str(
            payload.get("Requisition_ID") or payload.get("requisition_id") or ""
        ).strip()
        if requisition_id:
            line_items = _clean_line_items(payload.get("items", []))
            _validate_fulfillment_items(requisition_id, line_items)

        result = _submit_transaction("OUT", payload, validate_stock=True)
        if requisition_id:
            fulfillment = update_fulfillment(result["transaction_id"])
            result["requisition_id"] = fulfillment["requisition_id"]
            result["fulfillment_status"] = fulfillment["status"]
        return result
    except Exception as exc:
        logging.exception("Failed to submit issue stock transaction: %s", exc)
        raise


def submit_requisition(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit a requisition and store requested line items."""
    try:
        line_items = _clean_requisition_items(payload.get("items", []))
        school_id = str(payload.get("School_ID") or payload.get("school_id") or "").strip()
        requested_by = str(payload.get("Requested_By") or payload.get("requested_by") or "").strip()
        reason = str(payload.get("Reason") or payload.get("reason") or "").strip()

        if not school_id:
            raise ValueError("School_ID is required.")

        _id_values_exist(SCHOOLS_WORKSHEET, ["School_ID", "School ID"], {school_id}, "School_ID")
        _id_values_exist(
            ITEMS_WORKSHEET,
            ["Item_ID", "Item ID"],
            {line_item["Item_ID"] for line_item in line_items},
            "Item_ID",
        )

        requisition_id = _next_compact_id(
            REQUISITIONS_WORKSHEET,
            ["Requisition_ID", "Requisition ID"],
            "REQ",
        )
        detail_ids = _next_requisition_detail_ids(len(line_items))

        header = {
            "Requisition_ID": requisition_id,
            "Request_Date": payload.get("Request_Date")
            or payload.get("request_date")
            or payload.get("Requisition_Date")
            or payload.get("requisition_date")
            or _now_iso(),
            "School_ID": payload.get("School_ID") or payload.get("school_id") or "",
            "Status": "Pending",
            "Requested_By": requested_by,
            "Reason": reason,
        }

        logging.info("Submitting requisition %s", requisition_id)
        _append_dict_row(REQUISITIONS_WORKSHEET, header)

        for detail_id, line_item in zip(detail_ids, line_items):
            _append_dict_row(
                REQUISITION_DETAILS_WORKSHEET,
                {
                    "Req_Detail_ID": detail_id,
                    "Requisition_ID": requisition_id,
                    "Item_ID": line_item["Item_ID"],
                    "Quantity_Requested": line_item["Quantity_Requested"],
                    "Quantity_Approved": "",
                    "Quantity_Fulfilled": "",
                },
            )

        return {
            "success": True,
            "requisition_id": requisition_id,
        }
    except Exception as exc:
        logging.exception("Failed to submit requisition: %s", exc)
        raise


def _json_error(exc: Exception, status_code: int = 400):
    message = str(exc)
    if status_code >= 500 and APP_ENV == "production":
        message = "An unexpected server error occurred."
    return jsonify({"success": False, "error": message}), status_code


@app.route("/login", methods=["GET", "POST"])
def login_route():
    error = ""
    next_path = _safe_next_path(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            email = str(payload.get("email", "")).strip().lower()
            password = str(payload.get("password", ""))
        else:
            email = str(request.form.get("email", "")).strip().lower()
            password = str(request.form.get("password", ""))
        try:
            user = authenticate_user(email, password)
        except Exception:
            logging.exception("Authentication lookup failed for %s", email)
            user = None
        if user:
            session.clear()
            session.permanent = True
            session["user"] = user
            logging.info("Login succeeded for %s", email)
            _audit(
                "login", "User", str(user.get("User_ID", "")),
                None, {"Email": email}, status="Success", user=user,
            )
            if request.is_json:
                public_user = {
                    key: value for key, value in user.items()
                    if key.lower() not in {"password", "password_hash"}
                }
                return jsonify({"success": True, "user": public_user})
            return redirect(
                _safe_next_path(next_path, user) or _default_redirect_for(user)
            )
        logging.warning("Login failed for %s", email)
        _audit(
            "login", "User", email, None, {"Email": email},
            status="Failed", remarks="Invalid credentials", user={"Email": email},
        )
        error = "Invalid email or password, or the account is inactive."
        if request.is_json:
            return _json_error(ValueError(error), 401)
    return render_template("login.html", error=error, next_path=next_path)


@app.route("/logout", methods=["GET", "POST"])
def logout_route():
    user = current_user()
    if user:
        _audit("logout", "User", str(user.get("User_ID", "")), user, None, user=user)
    session.clear()
    if request.is_json:
        return jsonify({"success": True})
    return redirect(url_for("login_route"))


@app.route("/forms/<path:filename>")
def serve_form(filename):
    if filename == "login.html":
        return redirect(url_for("login_route"))

    user = current_user()
    if not user:
        return redirect(url_for("login_route", next=f"/forms/{filename}"))

    allowed_roles = FORM_PAGE_ROLES.get(filename)
    if allowed_roles is None:
        return jsonify({"success": False, "error": "Form not found."}), 404

    if user.get("Role") not in allowed_roles:
        return jsonify(
            {
                "success": False,
                "error": "You do not have permission to access this page.",
            }
        ), 403

    return send_from_directory(FORMS_DIR, filename)


@app.get("/items")
@app.get("/api/items")
def items_route():
    try:
        return jsonify(get_items())
    except Exception as exc:
        logging.exception("Failed to load items: %s", exc)
        return _json_error(exc, 500)


@app.get("/schools")
@app.get("/api/schools")
def schools_route():
    try:
        return jsonify(get_schools())
    except Exception as exc:
        logging.exception("Failed to load schools: %s", exc)
        return _json_error(exc, 500)


@app.get("/warehouses")
@app.get("/api/warehouses")
def warehouses_route():
    try:
        return jsonify(get_warehouses())
    except Exception as exc:
        logging.exception("Failed to load warehouses: %s", exc)
        return _json_error(exc, 500)


@app.get("/api/users")
@require_role("Admin")
def users_route():
    try:
        return jsonify({"success": True, "users": get_users()})
    except Exception as exc:
        logging.exception("Failed to load users: %s", exc)
        return _json_error(exc, 500)


@app.post("/api/users")
@require_role("Admin")
def create_user_route():
    payload = {}
    try:
        payload = _request_payload()
        user = create_user(payload)
        _audit("CREATE_USER", "User", user["User_ID"], None, user)
        return jsonify({"success": True, "user": user}), 201
    except ValueError as exc:
        _audit(
            "CREATE_USER", "User", "", None,
            {"Email": str(payload.get("Email", "")).strip().lower()},
            "Failed", str(exc),
        )
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to create user: %s", exc)
        _audit("CREATE_USER", "User", "", None, None, "Failed", str(exc))
        return _json_error(exc, 500)


@app.patch("/api/users/<user_id>")
@require_role("Admin")
def update_user_route(user_id):
    payload = {}
    try:
        payload = _request_payload()
        before, after = update_user(user_id, payload)
        action = "UPDATE_USER"
        if "Active" in payload and before["Active"] != after["Active"]:
            action = "ACTIVATE_USER" if after["Active"] else "DEACTIVATE_USER"
        _audit(action, "User", user_id, before, after)
        return jsonify({"success": True, "user": after})
    except ValueError as exc:
        _audit("UPDATE_USER", "User", user_id, None, None, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to update user %s: %s", user_id, exc)
        _audit("UPDATE_USER", "User", user_id, None, None, "Failed", str(exc))
        return _json_error(exc, 500)


@app.post("/api/users/<user_id>/reset-password")
@require_role("Admin")
def reset_user_password_route(user_id):
    try:
        payload = _request_payload()
        password_hash = hash_password(payload.get("Password", ""))
        before = public_user_record(_user_record(user_id))
        _update_row_by_id(
            USERS_WORKSHEET, ["User_ID", "User ID"], user_id,
            {"Password_Hash": password_hash},
        )
        after = dict(before)
        _audit("RESET_USER_PASSWORD", "User", user_id, before, after)
        return jsonify({"success": True, "message": "Password reset successfully."})
    except ValueError as exc:
        _audit(
            "RESET_USER_PASSWORD", "User", user_id, None, None,
            "Failed", str(exc),
        )
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to reset password for %s: %s", user_id, exc)
        _audit(
            "RESET_USER_PASSWORD", "User", user_id, None, None,
            "Failed", str(exc),
        )
        return _json_error(exc, 500)


def _report_format() -> str:
    report_format = request.args.get("format", "json").strip().lower()
    if report_format not in {"json", "csv"}:
        raise ValueError("format must be json or csv.")
    return report_format


def _report_response(report_name: str, payload: Any, report_format: str):
    _audit(
        "EXPORT_REPORT", "Report", report_name, None,
        {"Report_Name": report_name, "Format": report_format},
    )
    if report_format == "csv":
        records = payload if isinstance(payload, list) else [payload]
        return records_to_csv_response(records, f"{report_name}_report.csv")
    return jsonify(payload)


@app.get("/api/reports/executive-summary")
@require_role("Admin", "Viewer", "Approver", "Store_Officer")
def executive_summary_report_route():
    try:
        report_format = _report_format()
        return _report_response(
            "executive_summary", get_executive_summary(), report_format
        )
    except ValueError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to generate executive summary report: %s", exc)
        return _json_error(exc, 500)


@app.get("/api/reports/stock")
@require_role("Admin", "Viewer", "Store_Officer")
def stock_report_route():
    try:
        report_format = _report_format()
        return _report_response("stock", get_stock_report(), report_format)
    except ValueError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to generate stock report: %s", exc)
        return _json_error(exc, 500)


@app.get("/api/reports/requisitions")
@require_role("Admin", "Viewer", "Approver", "School_User")
def requisition_report_route():
    try:
        report_format = _report_format()
        user = current_user() or {}
        school_id = str(user.get("School_ID", "")).strip() if user.get("Role") == "School_User" else None
        records = [] if school_id == "" else get_requisition_report(school_id=school_id)
        return _report_response("requisitions", records, report_format)
    except ValueError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to generate requisition report: %s", exc)
        return _json_error(exc, 500)


@app.get("/api/reports/fulfillment")
@require_role("Admin", "Viewer", "Approver", "Store_Officer", "School_User")
def fulfillment_report_route():
    try:
        report_format = _report_format()
        user = current_user() or {}
        school_id = str(user.get("School_ID", "")).strip() if user.get("Role") == "School_User" else None
        records = [] if school_id == "" else get_fulfillment_report(school_id=school_id)
        return _report_response("fulfillment", records, report_format)
    except ValueError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to generate fulfillment report: %s", exc)
        return _json_error(exc, 500)


@app.get("/api/reports/audit")
@require_role("Admin")
def audit_report_route():
    try:
        report_format = _report_format()
        records = get_audit_report(
            action=request.args.get("action"), user_id=request.args.get("user_id")
        )
        return _report_response("audit", records, report_format)
    except ValueError as exc:
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to generate audit report: %s", exc)
        return _json_error(exc, 500)


@app.get("/pending_requisitions")
@app.get("/api/pending-requisitions")
@require_role("Admin", "Approver")
def pending_requisitions_route():
    try:
        return jsonify({"success": True, "requisitions": get_pending_requisitions()})
    except Exception as exc:
        logging.exception("Failed to load pending requisitions: %s", exc)
        return _json_error(exc, 500)


@app.get("/open_requisitions")
@app.get("/api/open-requisitions")
@require_role("Admin", "Store_Officer", "Approver")
def open_requisitions_route():
    try:
        return jsonify({"success": True, "requisitions": get_open_requisitions()})
    except Exception as exc:
        logging.exception("Failed to load open requisitions: %s", exc)
        return _json_error(exc, 500)


@app.get("/requisition/<requisition_id>")
@app.get("/api/requisition/<requisition_id>")
def requisition_route(requisition_id):
    try:
        return jsonify({"success": True, **get_requisition(requisition_id)})
    except ValueError as exc:
        return _json_error(exc, 404)
    except Exception as exc:
        logging.exception("Failed to load requisition %s: %s", requisition_id, exc)
        return _json_error(exc, 500)


@app.post("/approve_requisition")
@app.post("/api/approve-requisition")
@require_role("Admin", "Approver")
def approve_requisition_route():
    payload = {}
    try:
        payload = _request_payload()
        user = current_user() or {}
        payload["Approved_By"] = user.get("Full_Name") or user.get("Email") or user.get("User_ID")
        entity_id = str(payload.get("Requisition_ID") or payload.get("requisition_id") or "")
        before = get_requisition(entity_id) if entity_id else None
        result = approve_requisition(payload)
        _audit("approve requisition", "Requisition", entity_id, before, result)
        return jsonify(result)
    except ValueError as exc:
        _audit("approve requisition", "Requisition", str(payload.get("Requisition_ID", "")), None, payload, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to approve requisition request: %s", exc)
        return _json_error(exc, 500)


@app.post("/reject_requisition")
@app.post("/api/reject-requisition")
@require_role("Admin", "Approver")
def reject_requisition_route():
    payload = {}
    try:
        payload = _request_payload()
        entity_id = str(payload.get("Requisition_ID") or payload.get("requisition_id") or "")
        before = get_requisition(entity_id) if entity_id else None
        result = reject_requisition(payload)
        _audit("reject requisition", "Requisition", entity_id, before, result)
        return jsonify(result)
    except ValueError as exc:
        _audit("reject requisition", "Requisition", str(payload.get("Requisition_ID", "")), None, payload, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to reject requisition request: %s", exc)
        return _json_error(exc, 500)


@app.post("/submit_requisition")
@app.post("/api/requisition")
@require_role("Admin", "School_User")
def submit_requisition_route():
    payload = {}
    try:
        payload = _request_payload()
        user = current_user() or {}
        requested_school = str(payload.get("School_ID") or payload.get("school_id") or "").strip()
        assigned_school = str(user.get("School_ID", "")).strip()
        if user.get("Role") == "School_User" and (not assigned_school or requested_school != assigned_school):
            return _json_error(PermissionError("School users may submit requisitions only for their assigned school."), 403)
        payload["Requested_By"] = user.get("Full_Name") or user.get("Email") or user.get("User_ID")
        result = submit_requisition(payload)
        _audit("submit requisition", "Requisition", result["requisition_id"], None, result)
        return jsonify(result)
    except ValueError as exc:
        _audit("submit requisition", "Requisition", "", None, payload, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to submit requisition request: %s", exc)
        return _json_error(exc, 500)


@app.post("/submit_receive_stock")
@app.post("/api/receive-stock")
@require_role("Admin", "Store_Officer")
def submit_receive_stock_route():
    payload = {}
    try:
        payload = _request_payload()
        result = submit_receive_stock(payload)
        _audit("receive stock", "Transaction", result["transaction_id"], None, result)
        return jsonify(result)
    except ValueError as exc:
        _audit("receive stock", "Transaction", "", None, payload, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to submit receive stock request: %s", exc)
        return _json_error(exc, 500)


@app.post("/submit_issue_stock")
@app.post("/api/issue-stock")
@require_role("Admin", "Store_Officer")
def submit_issue_stock_route():
    payload = {}
    try:
        payload = _request_payload()
        result = submit_issue_stock(payload)
        _audit("issue stock", "Transaction", result["transaction_id"], None, result)
        if result.get("requisition_id"):
            _audit("fulfillment update", "Requisition", result["requisition_id"], None, {"Status": result.get("fulfillment_status"), "Transaction_ID": result["transaction_id"]})
        return jsonify(result)
    except ValueError as exc:
        _audit("issue stock", "Transaction", "", None, payload, "Failed", str(exc))
        return _json_error(exc, 400)
    except Exception as exc:
        logging.exception("Failed to submit issue stock request: %s", exc)
        return _json_error(exc, 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=APP_ENV == "development")
