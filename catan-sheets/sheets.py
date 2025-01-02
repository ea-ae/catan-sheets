from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery
from functools import lru_cache


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SERVICE_ACCOUNT_KEY_FILE = "service_account_key.json"
SPREADSHEET_ID = "1U7uKsuO2l1SxT3qZSRmdRdX1apjm81pRsnYtFcxMGQQ"

DATA_ENTRY_TAB_NAME = "Internal"
NAMES_TAB_NAME = "'All Divisions Players'"
NAMES_RANGES = ["B4:C", "F4:G"]


def get_credentials():
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_KEY_FILE, SCOPE
    )

    if not credential or credential.invalid:
        raise Exception("Unable to authenticate using service account key.")
    return credential


def get_service(credentials):
    return discovery.build("sheets", "v4", credentials=credentials)


@lru_cache(maxsize=1)
def fetch_member_names(credentials):
    service = get_service(credentials)
    member_names = {}

    for names_range in NAMES_RANGES:
        range_to_read = f"{NAMES_TAB_NAME}!{names_range}"
        # first column is discord name, second is colonist
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_to_read)
            .execute()
        )
        values = result.get("values", [])
        for row in values:
            member_names[row[1]] = row[0]
    
    return member_names


def translate_name(credentials, name):
    discord_to_colonist = {v: k for k, v in fetch_member_names(credentials)}

    if name in discord_to_colonist:
        return discord_to_colonist[name]



def update(credentials, div: str, data: list[list[str]]):
    service = get_service(credentials)

    sheet = service.spreadsheets()

    STARTING_ROW = 3
    div_col = {
        "1": "B",
        "2": "I"
    }[div]
    range_to_read = f"{DATA_ENTRY_TAB_NAME}!{div_col}{STARTING_ROW}:{div_col}"
    res = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_to_read).execute()
    )
    vals = res.get("values", [])

    first_empty_row = STARTING_ROW + len(vals)
    last_col = chr((ord(div_col) - ord("A") + len(data[0])) % 26 + ord("A"))
    range_to_write = f"{DATA_ENTRY_TAB_NAME}!{div_col}{first_empty_row}:{last_col}{first_empty_row + len(data)}"

    rez = (
        sheet.values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_write,
            valueInputOption="RAW",
            body={"values": data},
        )
        .execute()
    )
