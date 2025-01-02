from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery
from functools import lru_cache


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SERVICE_ACCOUNT_KEY_FILE = "service_account_key.json"
SPREADSHEET_ID = "1U7uKsuO2l1SxT3qZSRmdRdX1apjm81pRsnYtFcxMGQQ"

STARTING_DATA_ENTRY_ROW = 3
DATA_ENTRY_TAB_NAME = "Internal"
NAMES_TAB_NAME = "'All Divisions Players'"
NAMES_RANGES = ["B4:C", "F4:G"]
DIV_COLS = {"1": "B", "2": "I"}


def get_creds():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_KEY_FILE, SCOPE
    )

    if not creds or creds.invalid:
        raise Exception("Unable to authenticate using service account key.")
    return creds


def get_service(creds):
    return discovery.build("sheets", "v4", credentials=creds)


@lru_cache(maxsize=1)
def fetch_member_names(creds):
    service = get_service(creds)
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


def translate_name(creds, name):
    discord_to_colonist = fetch_member_names(creds)

    if name in discord_to_colonist:
        return discord_to_colonist[name]


def update(creds, div: str, data: list[list[str]]):
    service = get_service(creds)

    sheet = service.spreadsheets()

    div_col = DIV_COLS[div]
    range_to_read = (
        f"{DATA_ENTRY_TAB_NAME}!{div_col}{STARTING_DATA_ENTRY_ROW}:{div_col}"
    )
    res = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_to_read).execute()
    )
    vals = res.get("values", [])

    first_empty_row = STARTING_DATA_ENTRY_ROW + len(vals)
    last_col = chr((ord(div_col) - ord("A") + len(data[0])) % 26 + ord("A"))
    range_to_write = f"{DATA_ENTRY_TAB_NAME}!{div_col}{first_empty_row}:{last_col}{first_empty_row + len(data)}"

    (
        sheet.values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_write,
            valueInputOption="RAW",
            body={"values": data},
        )
        .execute()
    )
