#!/usr/bin/env python3
"""EV Lindau Young Islanders Sharepic Generator."""

import pandas as pd

import xml.etree.ElementTree as ET

import argparse
import typing
from teams import OPPONENTS
from deb_scraper import deb_scraper

DATE_FMT = "%d.%m.%Y"

TREE = ET.parse("template.svg")
ROOT = TREE.getroot()
CSV_SEARCH_STR = ".//{{*}}text[@id='{field}{age}']"
YOUTH_TEAMS = ("U17", "U15", "U13", "U11", "U9")
DEB_IDS = {"U17": (39231, 18560), "U15": (14783, 18748), "U13": (39458, 18778)}
DATE_COL = "Datum"
TIME_COL = "Zeit"
VS_COL = "Gegner"
GOALS_COL = "Spielstand"


def get_max_week_of_year(year: int) -> int:
    """Determine the maximum ISO week number (52 or 53) for a given year.

    The ISO standard dictates that a year has 53 weeks if December 28th falls in week
    53.

    Args:
        year (int): Year to find the maximum ISO week number.

    Returns:
        int: Max ISO week number.

    """
    # Use December 28th, which is always in the last week of the year to reliably find
    # the maximum week number.
    return pd.Timestamp(year=year, month=12, day=28).week


CURRENT: pd.Timestamp = pd.Timestamp.now()
MAX_WEEK = get_max_week_of_year(CURRENT.year)


class ValidWeekNumber(argparse.Action):
    """Validate the provided week number.

    Rules:
        1. Must be an integer.
        2. Must be >= 1.
        3. Must be <= the max week count of the current year.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        value: typing.Any,
        option_string: str | None = None,
    ):
        """Do the validation, baby.

        Args:
            parser (argparse.ArgumentParser): The ArgumentParser object which contains
                this action.
            namespace (argparse.Namespace): The Namespace object that will be returned
                by parse_args().
            value (int): The associated command-line argument.
            option_string (str | None, optional): The option string that was used to
                invoke this action. Defaults to None.

        Raises:
            argparse.ArgumentTypeError: Value provided cannot be parsed as integer.
            argparse.ArgumentTypeError: Value is not a valid week number.

        """
        try:
            week_num = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"'{value}' is not a valid integer for a week number."
            )

        if not (1 <= week_num <= MAX_WEEK):
            msg = (
                f"Invalid week number: {week_num}. "
                f"The week number must be between 1 and {MAX_WEEK} "
                f"(the maximum number of weeks in the current year, {CURRENT.year})."
            )
            raise argparse.ArgumentTypeError(msg)

        # If validation passes, set the attribute in the namespace
        setattr(namespace, self.dest, week_num)


def parse_args() -> int:
    """Set up and run the argument parser.

    Returns:
        int: Week to generate the sharepic for.
    """
    parser = argparse.ArgumentParser(description="Generate Young Islanders Sharepic.")

    parser.add_argument(
        "week_num",
        action=ValidWeekNumber,
        default=CURRENT.week,
        nargs="?",
        help=(
            f"The week number (depending on the current year). For {CURRENT.year}, the "
            f"valid range is 1 to {MAX_WEEK}. Defaults to {CURRENT.week}."
        ),
    )

    args = parser.parse_args()

    return args.week_num


def main() -> None:
    """Generate the sharepics."""
    current_week = parse_args()
    with deb_scraper() as get_game_data:
        preview(current_week, get_game_data)
        scorecard(current_week - 1, get_game_data)


def preview(
    week: int, get_game_data: typing.Callable[[int, int], pd.DataFrame]
) -> None:
    """Generate the game preview.

    Args:
        week (int): Week to generate the sharepic for.
        get_game_data (Callable[[int, int], pd.DataFrame]): Function to get the game
            data.

    Raises:
        ValueError: If more than one game per week and team is found.
    """
    for team in YOUTH_TEAMS:
        data = (
            pd.read_csv(team.lower() + ".csv")
            if team in ("U9", "U11")
            else get_game_data(*DEB_IDS[team])
        )

        data[DATE_COL] = pd.to_datetime(data[DATE_COL], format=DATE_FMT)
        weeks = data[DATE_COL].dt.isocalendar().week
        idx: pd.Series = weeks == week

        team_age = team.lstrip("U")
        if not idx.any():
            _empty_date(team_age)
            _empty_opponent(team_age)
            _empty_time(team_age)
            continue

        try:
            date_str: str = data[idx][DATE_COL].item().strftime(DATE_FMT)
            time_str: str = data[idx][TIME_COL].item()
            versus: str = data[idx][VS_COL].item()
        except ValueError as err:
            raise ValueError(idx) from err

        if versus.startswith("@ "):
            where = "A"
            versus = versus[2:]
        else:
            where = "H"

        if team in ("U9", "U11"):
            # for U9 and U11, the "versus" actually is the location where the team plays
            where = ""
        else:
            # for the other teams, the opponent is abbreviated, replace with full team
            # name
            versus = OPPONENTS[versus]

        _set_calendar_week(week)
        _set_date(date_str, team_age)
        _set_opponent(versus, where, team_age)
        _set_time(time_str, team_age)

    TREE.write("preview.svg")


def scorecard(
    week: int, get_game_data: typing.Callable[[int, int], pd.DataFrame]
) -> None:
    """Generate the game preview.

    Args:
        week (int): Week to generate the sharepic for.
        get_game_data (Callable[[int, int], pd.DataFrame]): Function to get the game
            data.

    Raises:
        ValueError: If more than one game per week and team is found.
    """
    for team in YOUTH_TEAMS:
        data = (
            pd.read_csv(team.lower() + ".csv")
            if team in ("U9", "U11")
            else get_game_data(*DEB_IDS[team])
        )

        team_age = team.lstrip("U")

        data[DATE_COL] = pd.to_datetime(data[DATE_COL], format=DATE_FMT)

        weeks = data[DATE_COL].dt.isocalendar().week
        idx: pd.Series = weeks == week

        if not idx.any() or team in ("U9", "U11"):
            # for U9 and U11, the is no result
            _empty_date(team_age)
            _empty_opponent(team_age)
            _empty_time(team_age)
            continue

        try:
            date_str: str = data[idx][DATE_COL].item().strftime(DATE_FMT)
            goals_str: str = data[idx][GOALS_COL].item()
            versus: str = data[idx][VS_COL].item()
        except ValueError as err:
            raise ValueError(idx) from err

        if versus.startswith("@ "):
            where = "A"
            versus = versus[2:]
            goals_str = ":".join(reversed(goals_str.split(":")))
        else:
            where = "H"

        # the opponent is abbreviated, replace with full team name
        versus = OPPONENTS[versus]

        _set_calendar_week(week)
        _set_date(date_str, team_age)
        _set_opponent(versus, where, team_age)
        _set_time(goals_str, team_age)

    TREE.write("scores.svg")


def _set_opponent(versus: str, where: str, age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="TEAM", age=age))
    (s,) = list(t)
    s.text = f"{versus}" + (f" [{where}]" if where else "")


def _set_date(date: str, age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="DATE", age=age))
    (s,) = list(t)
    s.text = date


def _set_time(time: str, age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="TIME", age=age))
    (s,) = list(t)
    s.text = time


def _set_calendar_week(week: int) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="CALENDAR_WEEK", age=""))
    (s,) = list(t)
    s.text = f"SPIELVORSCHAU KW {week}"


def _empty_opponent(age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="TEAM", age=age))
    (s,) = list(t)
    s.text = ""


def _empty_date(age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="DATE", age=age))
    (s,) = list(t)
    s.text = ""


def _empty_time(age: str) -> None:
    (t,) = ROOT.findall(CSV_SEARCH_STR.format(field="TIME", age=age))
    (s,) = list(t)
    s.text = ""


if __name__ == "__main__":
    main()
