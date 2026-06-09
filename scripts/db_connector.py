import logging
import pandas as pd
import gspread

from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


def connect_to_sheet(sheet_name):
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials/service_account.json",
            SCOPE
        )

        client = gspread.authorize(creds)

        return client.open(sheet_name)

    except FileNotFoundError:
        logging.error("Credential file not found")
        raise

    except Exception as exc:
        logging.error(f"Connection error: {exc}")
        raise


def read_worksheet(sheet_name, worksheet_name):

    sheet = connect_to_sheet(sheet_name)

    worksheet = sheet.worksheet(worksheet_name)

    records = worksheet.get_all_records()

    return pd.DataFrame(records)


def append_row(sheet_name, worksheet_name, row_data):

    sheet = connect_to_sheet(sheet_name)

    worksheet = sheet.worksheet(worksheet_name)

    worksheet.append_row(row_data)