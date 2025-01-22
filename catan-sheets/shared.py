from trivia import generate_trivia
import db

import discord
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, NamedTuple, Sequence
from sqlalchemy.orm.session import Session
import pytz


class Division(Enum):
    DIV1 = "1"
    DIV2 = "2"
    CK = "CK"


class Site(Enum):
    COLONIST = "colonist.io",
    TWO_SHEEP = "twosheep.io"


@dataclass
class GameMetadata:
    division: Division
    site: Site
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
    username: str
    discord_user: discord.Member | None
    discord_name: str | None
    scoreboard_name: str
    score: int

    @staticmethod
    def from_names(
        discord_user: discord.Member | None,
        discord_name: str | None,
        username: str,
        score: int,
    ):
        fallback_name = discord_name if discord_name else username
        scoreboard_name = (
            discord_name if discord_name else fallback_name + " (FALLBACK)"
        )

        return PlayerScore(
            username=username,
            discord_user=discord_user,
            discord_name=discord_name,
            scoreboard_name=scoreboard_name,
            score=score,
        )


@dataclass
class GameData:
    metadata: GameMetadata | None
    scores: list[PlayerScore]
    raw_json: dict[str, Any] | None

    def persist(self, session: Session):
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for persistence")

        game = db.Game(
            div=self.metadata.division,
            site=self.metadata.site,
            replay_link=self.metadata.replay_link,
            timestamp=self.metadata.timestamp,
            is_duplicate=self.metadata.is_duplicate,
            is_old_game=self.metadata.is_old_game,
            game_json=self.raw_json,
        )
        session.add(game)
        for player_score in self.scores:
            session.add(
                db.GamePlayer(
                    name=player_score.username,
                    score=player_score.score,
                    game=game,
                    player=None  # temp / todo migrate, we don't have proper mappings yet
                )
            )

    def serialize(self):
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for serialization")

        if len(self.scores) != 4:
            raise Exception(f"score data invalid {self.scores}")

        # zip one metadata element per scores row to the start
        return [
            [md_row]
            + [
                score.scoreboard_name,
                (
                    min(score.score, 13)
                    if self.metadata.division == Division.CK
                    else min(score.score, 10)
                ),
            ]
            for md_row, score in zip(self.metadata.serialize(), self.scores)
        ]

    def message(self, author: discord.User | discord.Member) -> str:
        if self.metadata is None:
            raise Exception(f"metadata is mandatory for message generation")

        msg = []

        played_at_epoch = int(self.metadata.timestamp.timestamp())
        msg.append(
            f"**Division {self.metadata.division.value}** [game]({self.metadata.replay_link}) posted by @{author.name} (played <t:{played_at_epoch}>)"
        )

        if self.metadata.is_old_game:
            msg.append("*⚠️ Warning: this game was played more than 4 hours ago.*")

        if self.metadata.is_duplicate:
            msg.append("*⚠️ Warning: this game has already been submitted.*")

        msg.append("")

        for player in self.scores:
            if player.discord_user is not None:
                msg.append(f"{player.username} ({player.discord_user.mention}): {player.score} VPs")
            elif player.discord_name is not None:
                msg.append(f"{player.username} (@{player.discord_name}): {player.score} VPs")
            else:
                msg.append(f"{player.username}: {player.score} VPs")

        if self.raw_json is not None:
            msg.append("")
            msg.append(f"*{generate_trivia(self.raw_json)}*")

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
