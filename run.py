#!/usr/bin/env python3

import pandas as pd

import xml.etree.ElementTree as ET

from teams import OPPONENTS

DATE_FMT = "%d.%m.%Y"

TREE = ET.parse("template.svg")
ROOT = TREE.getroot()
YOUTH_TEAMS = ("U17", "U15", "U13", "U11", "U9")
SEARCH_STR = ".//{{*}}text[@id='{field}{age}']"


def set_opponent(versus: str, where: str, age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="TEAM", age=age))
    (s,) = list(t)
    s.text = f"{versus}" + (f" [{where}]" if where else "")


def set_date(date: str, age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="DATE", age=age))
    (s,) = list(t)
    s.text = date


def set_time(time: str, age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="TIME", age=age))
    (s,) = list(t)
    s.text = time


def set_calendar_week(week: int) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="CALENDAR_WEEK", age=""))
    (s,) = list(t)
    s.text = f"SPIELVORSCHAU KW {week}"


def empty_opponent(age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="TEAM", age=age))
    (s,) = list(t)
    s.text = ""


def empty_date(age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="DATE", age=age))
    (s,) = list(t)
    s.text = ""


def empty_time(age: str) -> None:
    (t,) = ROOT.findall(SEARCH_STR.format(field="TIME", age=age))
    (s,) = list(t)
    s.text = ""


for team in YOUTH_TEAMS:
    team_age = team.lstrip("U")

    data = pd.read_csv(
        team.lower() + ".csv",
    )
    data["DATE"] = pd.to_datetime(data["DATE"], format=DATE_FMT)

    # current week could be pd.Timestamp.now().week
    current_week = 48
    weeks = data["DATE"].dt.isocalendar().week
    idx: pd.Series = weeks == current_week

    if not idx.any():
        empty_date(team_age)
        empty_opponent(team_age)
        empty_time(team_age)
        continue

    try:
        date_str: str = data[idx]["DATE"].item().strftime(DATE_FMT)
        time_str: str = data[idx]["TIME"].item()
        versus: str = data[idx]["VS"].item()
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
        # for the other teams, the oppenent is abbreviated, replace with full team nam
        versus = OPPONENTS[versus]

    set_calendar_week(current_week)
    set_date(date_str, team_age)
    set_opponent(versus, where, team_age)
    set_time(time_str, team_age)

TREE.write("modified.svg")
