from dataclasses import dataclass
from datetime import datetime, timedelta
import discord
from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery
from functools import lru_cache
from typing import NamedTuple
import pytz


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SERVICE_ACCOUNT_KEY_FILE = "service_account_key.json"
SPREADSHEET_ID = "1U7uKsuO2l1SxT3qZSRmdRdX1apjm81pRsnYtFcxMGQQ"

STARTING_DATA_ENTRY_ROW = 4
DATA_ENTRY_TAB_NAME = "Internal"
NAMES_TAB_NAME = "'All Divisions Players'"
NAMES_RANGES = ["B4:C", "F4:G"]
DIV_COLS = {"1": "A", "2": "H"}


@dataclass
class GameMetadata:
    division: str
    replay_link: str
    timestamp: datetime
    is_duplicate: bool

    @property
    def is_old_game(self):
        return self.timestamp < datetime.now(tz=pytz.UTC) - timedelta(hours=4)

    @property
    def has_warning(self):
        return self.is_old_game or self.is_duplicate

    def serialize(self) -> tuple[str, str, str, str]:
        return (
            self.replay_link,
            self.timestamp.isoformat(),
            "",
            "⚠️" if self.has_warning else "",
        )


class PlayerScore(NamedTuple):
    display_name: str
    scoreboard_name: str
    score: int


@dataclass
class GameData:
    metadata: GameMetadata | None
    scores: list[PlayerScore]

    def serialize(self):
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for serialization")

        if len(self.scores) != 4:
            raise Exception(f"score data invalid {self.scores}")

        # zip one metadata element per scores row to the start
        return [
            [md_row] + list(score)
            for md_row, score in zip(self.metadata.serialize(), self.scores)
        ]

    def message(self, author: discord.User | discord.Member) -> str:
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for message generation")

        msg = []

        played_at_epoch = int(self.metadata.timestamp.timestamp())
        msg.append(
            f"**Division {self.metadata.division} colonist.io game** posted by {author.mention} (played <t:{played_at_epoch}>)"
        )

        if self.metadata.is_old_game:
            msg.append("*⚠️ Warning: this game was played more than 4 hours ago.*")

        if self.metadata.is_duplicate:
            msg.append("*⚠️ Warning: this game has already been submitted.*")
        
        msg.append("")

        for player in self.scores:
            msg.append(f"{player.display_name}: {player.score} VPs")

        return "\n".join(msg)


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

    is_duplicate = game_data.metadata.replay_link in [row[0] for row in existing_rows]
    game_data.metadata.is_duplicate = is_duplicate

    first_empty_row = STARTING_DATA_ENTRY_ROW + len(existing_rows)
    last_col = add_char(metadata_col, 3)
    last_row = first_empty_row + 3  # ?
    range_to_write = (
        f"{DATA_ENTRY_TAB_NAME}!{metadata_col}{first_empty_row}:{last_col}{last_row}"
    )

    print(game_data.serialize())

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

    return is_duplicate


def add_char(char: str, add: int):
    return chr((ord(char) - ord("A") + add) % 26 + ord("A"))
