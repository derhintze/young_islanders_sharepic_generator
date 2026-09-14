"""The abbreviations used for other teams."""

import pandas as pd

from deb_scraper import deb_scraper

DEB_IDS = {"U20": (28219, 21932), "U15": (39264, 21725), "U13": (39458, 21846)}

OPPONENTS = {
    "AIB": "EHC Bad Aibling",
    "BUC": "ESV Buchloe",
    "BWH": "Bad Wörishofen",
    "EAS": "TSV Schongau",
    "ECP": "EC Peiting",
    "ERCL": "ERC Lechbruck",
    "EVF": "EV Füssen",
    "EVK": "EV Königsbrunn",
    "FFB": "EV Fürstenfeldbruck",
    "HCL2": "HC Landsberg II",
    "KEM": "ESC Kempten",
    "MEM": "ECDC Memmingen",
    "PEMI": "Peißenberg Miners",
    "PFR": "EV Pfronten",
    "RAV": "EV Ravensburg",
    "RBM2": "RB München II",
    "RRG": "River Rats Geretsried",
    "SEC": "Stuttgarter EC",
    "SGGZ": "SG Götzens / Zirl",
    "SGLP2": "SG Lechbr. / Peiting II",
    "SGTBW": "SG Türkh. / Wörish.",
    "SGUB": "SG Ulm / Burgau",
    "SON": "ERC Sonthofen",
    "TEVM": "TEV Miesbach",
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
