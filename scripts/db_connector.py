import json
import logging
import os
from pathlib import Path

import pandas as pd
import gspread

from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

SPREADSHEET_NAME = "Educational_Supplies_Logs"

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

TRANSACTIONS_WORKSHEET = "Transactions"
TRANSACTION_DETAILS_WORKSHEET = "Transaction_Details"
ITEMS_WORKSHEET = "Items"
SCHOOLS_WORKSHEET = "Schools"
WAREHOUSES_WORKSHEET = "Warehouses"
REQUISITIONS_WORKSHEET = "Requisitions"
REQUISITION_DETAILS_WORKSHEET = "Requisition_Details"
USERS_WORKSHEET = "Users"
AUDIT_LOG_WORKSHEET = "Audit_Log"
PROTECTED_SEED_WORKSHEETS = {USERS_WORKSHEET, AUDIT_LOG_WORKSHEET}
BACKUP_WORKSHEETS = (
    ITEMS_WORKSHEET,
    SCHOOLS_WORKSHEET,
    WAREHOUSES_WORKSHEET,
    TRANSACTIONS_WORKSHEET,
    TRANSACTION_DETAILS_WORKSHEET,
    REQUISITIONS_WORKSHEET,
    REQUISITION_DETAILS_WORKSHEET,
    USERS_WORKSHEET,
    AUDIT_LOG_WORKSHEET,
)
CREDENTIALS_FILE = Path(__file__).resolve().parents[1] / "credentials" / "service_account.json"

USER_COLUMNS = [
    "User_ID", "Full_Name", "Email", "Role", "School_ID", "Password_Hash",
    "Active", "Created_At",
]

AUDIT_LOG_COLUMNS = [
    "Audit_ID", "Timestamp", "User_ID", "User_Email", "Role", "Action",
    "Entity_Type", "Entity_ID", "Before_State", "After_State", "IPAddress",
    "Status", "Remarks",
]

ALLOWED_REQUISITION_STATUSES = {
    "Pending",
    "Approved",
    "Partially Fulfilled",
    "Fulfilled",
    "Rejected",
}

REQUISITION_COLUMNS = [
    "Requisition_ID",
    "School_ID",
    "Request_Date",
    "Status",
    "Approved_By",
    "Approval_Date",
    "Remarks",
]

REQUISITION_DETAIL_COLUMNS = [
    "Req_Detail_ID",
    "Requisition_ID",
    "Item_ID",
    "Quantity_Requested",
    "Quantity_Approved",
    "Quantity_Fulfilled",
]


def normalize_column_name(column_name):
    return str(column_name).strip().lower().replace(" ", "_")


def find_column(dataframe, candidates, required=True):
    normalized_columns = {
        normalize_column_name(column): column for column in dataframe.columns
    }

    for candidate in candidates:
        normalized_candidate = normalize_column_name(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    if required:
        raise ValueError(f"Missing required column. Expected one of: {', '.join(candidates)}")

    return None


def require_columns(dataframe, required_columns, worksheet_name):
    missing_columns = [
        column for column in required_columns
        if find_column(dataframe, [column], required=False) is None
    ]

    if missing_columns:
        raise ValueError(
            f"{worksheet_name} worksheet is missing required columns: "
            + ", ".join(missing_columns)
        )


def clean_id_values(dataframe, column):
    if dataframe.empty:
        return set()

    return {
        str(value).strip()
        for value in dataframe[column].fillna("")
        if str(value).strip()
    }


def blank_values_exist(dataframe, column):
    if dataframe.empty:
        return False

    return dataframe[column].fillna("").astype(str).str.strip().eq("").any()


def validate_requisitions(requisitions, schools):
    require_columns(requisitions, REQUISITION_COLUMNS, REQUISITIONS_WORKSHEET)

    if schools.empty:
        valid_school_ids = set()
    else:
        school_id_column = find_column(schools, ["School_ID", "School ID"])
        valid_school_ids = clean_id_values(schools, school_id_column)

    requisition_id_column = find_column(requisitions, ["Requisition_ID", "Requisition ID"])
    school_id_column = find_column(requisitions, ["School_ID", "School ID"])
    status_column = find_column(requisitions, ["Status"])

    if blank_values_exist(requisitions, requisition_id_column):
        raise ValueError("Requisitions worksheet contains blank Requisition_ID values.")

    if blank_values_exist(requisitions, school_id_column):
        raise ValueError("Requisitions worksheet contains blank School_ID values.")

    if blank_values_exist(requisitions, status_column):
        raise ValueError("Requisitions worksheet contains blank Status values.")

    invalid_school_ids = sorted(
        school_id for school_id in clean_id_values(requisitions, school_id_column)
        if school_id not in valid_school_ids
    )
    if invalid_school_ids:
        raise ValueError(
            "Requisitions worksheet contains unknown School_ID values: "
            + ", ".join(invalid_school_ids)
        )

    invalid_statuses = sorted(
        status for status in clean_id_values(requisitions, status_column)
        if status not in ALLOWED_REQUISITION_STATUSES
    )
    if invalid_statuses:
        raise ValueError(
            "Requisitions worksheet contains invalid Status values: "
            + ", ".join(invalid_statuses)
        )


def validate_requisition_details(requisitions, requisition_details, items):
    require_columns(requisition_details, REQUISITION_DETAIL_COLUMNS, REQUISITION_DETAILS_WORKSHEET)
    require_columns(requisitions, ["Requisition_ID"], REQUISITIONS_WORKSHEET)

    if items.empty:
        valid_item_ids = set()
    else:
        item_id_column = find_column(items, ["Item_ID", "Item ID"])
        valid_item_ids = clean_id_values(items, item_id_column)

    requisition_id_column = find_column(requisitions, ["Requisition_ID", "Requisition ID"])
    detail_requisition_id_column = find_column(
        requisition_details, ["Requisition_ID", "Requisition ID"]
    )
    detail_item_id_column = find_column(requisition_details, ["Item_ID", "Item ID"])

    if blank_values_exist(requisition_details, detail_requisition_id_column):
        raise ValueError(
            "Requisition_Details worksheet contains blank Requisition_ID values."
        )

    if blank_values_exist(requisition_details, detail_item_id_column):
        raise ValueError("Requisition_Details worksheet contains blank Item_ID values.")

    valid_requisition_ids = clean_id_values(requisitions, requisition_id_column)
    detail_requisition_ids = clean_id_values(
        requisition_details, detail_requisition_id_column
    )

    missing_requisition_ids = sorted(
        requisition_id for requisition_id in detail_requisition_ids
        if requisition_id not in valid_requisition_ids
    )
    if missing_requisition_ids:
        raise ValueError(
            "Requisition_Details worksheet contains unknown Requisition_ID values: "
            + ", ".join(missing_requisition_ids)
        )

    invalid_item_ids = sorted(
        item_id for item_id in clean_id_values(requisition_details, detail_item_id_column)
        if item_id not in valid_item_ids
    )
    if invalid_item_ids:
        raise ValueError(
            "Requisition_Details worksheet contains unknown Item_ID values: "
            + ", ".join(invalid_item_ids)
        )


def validate_requisition_data(requisitions, requisition_details, items, schools):
    validate_requisitions(requisitions, schools)
    validate_requisition_details(requisitions, requisition_details, items)


def connect_to_sheet(sheet_name):
    try:
        credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
        if credentials_json:
            try:
                credentials_data = json.loads(credentials_json)
            except json.JSONDecodeError as exc:
                raise ValueError("GOOGLE_CREDENTIALS must contain valid JSON.") from exc
            if not isinstance(credentials_data, dict):
                raise ValueError("GOOGLE_CREDENTIALS must contain a JSON object.")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_data,
                SCOPE,
            )
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                str(CREDENTIALS_FILE),
                SCOPE,
            )

        client = gspread.authorize(creds)

        return client.open(sheet_name)

    except FileNotFoundError:
        logging.error("Google credential file not found at %s", CREDENTIALS_FILE)
        raise

    except Exception:
        logging.error("Failed to connect to Google Sheets.")
        raise


def read_worksheet(sheet_name, worksheet_name):

    sheet = connect_to_sheet(sheet_name)

    worksheet = sheet.worksheet(worksheet_name)

    records = worksheet.get_all_records()

    return pd.DataFrame(records)


def read_requisition_worksheets(sheet_name, validate=True):
    requisitions = read_worksheet(sheet_name, REQUISITIONS_WORKSHEET)

    data = {
        "requisitions": requisitions,
    }

    if validate:
        schools = read_worksheet(sheet_name, SCHOOLS_WORKSHEET)
        validate_requisitions(requisitions, schools)
        data["schools"] = schools

    requisition_details = read_worksheet(sheet_name, REQUISITION_DETAILS_WORKSHEET)
    data["requisition_details"] = requisition_details

    if validate:
        items = read_worksheet(sheet_name, ITEMS_WORKSHEET)
        validate_requisition_details(requisitions, requisition_details, items)
        data["items"] = items

    return data


def append_row(sheet_name, worksheet_name, row_data):

    sheet = connect_to_sheet(sheet_name)

    worksheet = sheet.worksheet(worksheet_name)

    worksheet.append_row(row_data)


def append_records(sheet_name, worksheet_name, records):
    """Append dictionaries using the worksheet's existing column order."""
    if worksheet_name in PROTECTED_SEED_WORKSHEETS:
        raise ValueError(f"Refusing to modify protected worksheet: {worksheet_name}")
    if not records:
        return 0

    sheet = connect_to_sheet(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)
    headers = [str(value).strip() for value in worksheet.row_values(1)]
    if not headers:
        raise ValueError(f"{worksheet_name} worksheet has no header row.")

    rows = []
    for record in records:
        normalized = {normalize_column_name(key): value for key, value in record.items()}
        rows.append([normalized.get(normalize_column_name(header), "") for header in headers])
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)
