from __future__ import annotations
from shared import Division, Site
from typing import List, Optional
from sqlalchemy import TIMESTAMP, Enum, ForeignKey, create_engine, Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, relationship


engine = create_engine("sqlite:///main.db")
session_maker = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    uid = Column(Integer, primary_key=True)


class Player(Base):
    __tablename__ = "players"

    discord_id = Column(String)
    colonist_username = Column(String)
    twosheep_username = Column(String)

    games: Mapped[List[GamePlayer]] = relationship(back_populates="player")


class Game(Base):
    __tablename__ = "games"

    div = Column(Enum(Division))
    site = Column(Enum(Site))
    replay_link = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    is_duplicate = Column(Boolean, nullable=False)
    is_old_game = Column(Boolean, nullable=False)
    game_json = Column(JSON)

    players: Mapped[List[GamePlayer]] = relationship(back_populates="game")


class GamePlayer(Base):
    __tablename__ = "game_players"

    name = Column(String)  # denormalized cuz we silly like that
    score = Column(Integer)

    game_id = Column(Integer, ForeignKey("games.uid"), nullable=False)
    game: Mapped[Game] = relationship(back_populates="players")
    player_id = Column(Integer, ForeignKey("players.uid"))
    player: Mapped[Optional[Player]] = relationship(back_populates="games")


def get_engine():
    return engine


def get_session():
    return session_maker()


def start():
    Base.metadata.create_all(engine)
