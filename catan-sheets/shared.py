import discord
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import NamedTuple, Sequence
import pytz


# enum
class Division(Enum):
    DIV1 = "1"
    DIV2 = "2"
    CK = "CK"


@dataclass
class GameMetadata:
    division: Division
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
            f"{'⚠️' if self.is_duplicate else ""}{'🕒' if self.is_old_game else ''}",
        )


class PlayerScore(NamedTuple):
    display_name: str
    scoreboard_name: str
    score: int

    @staticmethod
    def from_names(
        discord_user: discord.Member | None,
        discord_name: str | None,
        name: str,
        score: int,
    ):
        fallback_name = discord_name if discord_name else name
        display_name = (
            f"{name} ({discord_user.mention if discord_user else '@' + fallback_name})"
        )
        scoreboard_name = (
            discord_name if discord_name else fallback_name + " (FALLBACK)"
        )

        return PlayerScore(
            display_name=display_name, scoreboard_name=scoreboard_name, score=score
        )


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
            [md_row] + [score.scoreboard_name, score.score]
            for md_row, score in zip(self.metadata.serialize(), self.scores)
        ]

    def message(self, author: discord.User | discord.Member) -> str:
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for message generation")

        msg = []

        played_at_epoch = int(self.metadata.timestamp.timestamp())
        msg.append(
            f"**Division {self.metadata.division.value}** [game]({self.metadata.replay_link}) posted by {author.mention} (played <t:{played_at_epoch}>)"
        )

        if self.metadata.is_old_game:
            msg.append("*⚠️ Warning: this game was played more than 4 hours ago.*")

        if self.metadata.is_duplicate:
            msg.append("*⚠️ Warning: this game has already been submitted.*")

        msg.append("")

        for player in self.scores:
            msg.append(f"{player.display_name}: {player.score} VPs")

        return "\n".join(msg)


def get_discord_user(members: Sequence[discord.Member], discord_name: str):
    discord_user = None
    if discord_name is not None:
        discord_user = discord.utils.get(members, name=discord_name)  # type: ignore
        if discord_user is None:
            discord_user = discord.utils.get(members, global_name=discord_name)  # type: ignore
        if discord_user is None:
            discord_user = discord.utils.get(members, nick=discord_name)  # type: ignore

    return discord_user
