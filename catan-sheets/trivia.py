from dataclasses import dataclass
from typing import Any, Callable, TypeVar, Generic
import math


T = TypeVar("T")


@dataclass
class Trivia(Generic[T]):
    f: Callable[[str, dict[str, Any]], T]
    description: Callable[[str, T], str]
    fun_factor: Callable[[T], float]


TRIVIAS = [
    Trivia[float](
        f=lambda p, json: to_stats(json)["resourceStats"][p]["robbingLoss"],
        description=lambda name, x: f"{name} got robbed {x} times",
        fun_factor=lambda x: x * 0.7,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["resourceStats"][p]["robbingIncome"],
        description=lambda name, x: f"{name} robbed others {x} times",
        fun_factor=lambda x: x * 0.5,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["resourceStats"][p]["rollingLoss"],
        description=lambda name, x: f"{name} lost {x} resources by getting 7'd out",
        fun_factor=lambda x: x * 0.35,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["resourceStats"][p]["tradeIncome"]
        - to_stats(json)["resourceStats"][p]["tradeLoss"],
        description=lambda name, x: f"{name} traded a net profit of {x} cards",
        fun_factor=lambda x: x * 2,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["activityStats"][p]["resourceIncomeBlocked"],
        description=lambda name, x: f"{name} lost {x} resources to blocked tiles",
        fun_factor=lambda x: x * 0.2,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["diceStats"][0],
        description=lambda name, x: f"Two was rolled {x} times this game",
        fun_factor=lambda x: x * 1.5,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["diceStats"][1],
        description=lambda name, x: f"Three was rolled {x} times this game",
        fun_factor=lambda x: x * 1,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["diceStats"][9],
        description=lambda name, x: f"Eleven was rolled {x} times this game",
        fun_factor=lambda x: x * 1,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["diceStats"][10],
        description=lambda name, x: f"Twelve was rolled {x} times this game",
        fun_factor=lambda x: x * 1.5,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["gameDurationInMS"] // 60_000,
        description=lambda name, x: f"This game lasted only {x} minutes",
        fun_factor=lambda x: 23 - x,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["totalTurnCount"],
        description=lambda name, x: f"This game lasted only {x} turns",
        fun_factor=lambda x: 55 - x,
    ),
    Trivia[float](
        f=lambda p, json: to_stats(json)["players"][p]["victoryPoints"].get("2", 0),
        description=lambda name, x: f"{name} bought {x} VP devs",
        fun_factor=lambda x: x * 10 if x >= 4 else 0,
    ),
]


def generate_trivia(json: dict[str, Any]):
    color_to_name: dict[int, str] = {
        player["selectedColor"]: player["username"]
        for player in json["playerUserStates"]
    }

    best_trivia = None
    best_fun_factor = -math.inf

    for trivia in TRIVIAS:
        for player_color in color_to_name.keys():
            score = trivia.f(str(player_color), json)
            fun_factor = trivia.fun_factor(score)
            if fun_factor > best_fun_factor:
                player_name = color_to_name[player_color]
                best_trivia = trivia.description(player_name, score)
                best_fun_factor = fun_factor

    return best_trivia


def to_stats(json: dict[str, Any]) -> dict[str, Any]:
    return json["eventHistory"]["endGameState"]
