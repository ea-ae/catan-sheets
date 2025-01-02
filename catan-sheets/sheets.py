from shared import GameData
from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery
from functools import lru_cache


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SERVICE_ACCOUNT_KEY_FILE = "service_account_key.json"
SPREADSHEET_ID = "1U7uKsuO2l1SxT3qZSRmdRdX1apjm81pRsnYtFcxMGQQ"

STARTING_DATA_ENTRY_ROW = 4
DATA_ENTRY_TAB_NAME = "Internal"
NAMES_TAB_NAME = "'All Divisions Players'"
NAMES_RANGES = ["B4:C", "F4:G"]
DIV_COLS = {"1": "A", "2": "H"}


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


def update(creds, div: str, game_data: GameData):
    if game_data.metadata is None:
        raise Exception("cannot update without metadata")

    service = get_service(creds)

    sheet = service.spreadsheets()

    metadata_col = DIV_COLS[div]
    # first row is metadata, so when checking for empty rows, skip it
    name_col = add_char(metadata_col, 1)
    range_to_read = (
        f"{DATA_ENTRY_TAB_NAME}!{metadata_col}{STARTING_DATA_ENTRY_ROW}:{name_col}"
    )
    res = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_to_read).execute()
    )
    existing_rows = res.get("values", [])

    if len(existing_rows) > 0 and len(existing_rows[0]) > 0:
        is_duplicate = game_data.metadata.replay_link in [row[0] for row in existing_rows]
        game_data.metadata.is_duplicate = is_duplicate

    first_empty_row = STARTING_DATA_ENTRY_ROW + len(existing_rows)
    last_col = add_char(metadata_col, 3)
    last_row = first_empty_row + 3  # ?
    range_to_write = (
        f"{DATA_ENTRY_TAB_NAME}!{metadata_col}{first_empty_row}:{last_col}{last_row}"
    )

    (
        sheet.values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_write,
            valueInputOption="RAW",
            body={"values": game_data.serialize()},
        )
        .execute()
    )


def add_char(char: str, add: int):
    return chr((ord(char) - ord("A") + add) % 26 + ord("A"))
