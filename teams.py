"""The abbreviations used for other teams."""

from deb_scraper import deb_scraper
import pandas as pd

DEB_IDS = {"U17": (39231, 18560), "U15": (14783, 18748), "U13": (39458, 18778)}

OPPONENTS = {
    "AIB": "EHC Bad Aibling",
    "BUC": "ESV Buchloe",
    "BWH": "Bad Wörishofen",
    "EAS": "TSV Schongau",
    "ERCL": "ERC Lechbruck",
    "EVK": "EV Königsbrunn",
    "FFB": "EV Fürstenfeldbruck",
    "HCL2": "HC Landsberg II",
    "KEM": "ESC Kempten",
    "MEM": "ECDC Memmingen",
    "PEMI": "Peißenberg Miners",
    "PFR": "EV Pfronten",
    "RBM2": "Rookie Bulls München II",
    "SGGZ": "SG Götzens / Zirl",
    "SGLP2": "SG Lechbr. / Peiting II",
    "SGTBW": "SG Türkh. / Wörish.",
    "SGUB": "SG Ulm / Burgau",
    "SON": "ERC Sonthofen",
    "ULM": "VfE Ulm / Neu-Ulm",
}

if __name__ == "__main__":
    teams = set()
    with deb_scraper() as get_game_data:
        for team, ids in DEB_IDS.items():
            data: pd.DataFrame = get_game_data(*ids)

            teams |= {g.lstrip("@ ") for g in data["Gegner"]}

    print("can be removed:", sorted(set(OPPONENTS) - teams))
    print("missing:", sorted(teams - set(OPPONENTS)))
