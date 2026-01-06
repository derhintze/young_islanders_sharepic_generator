"""Get game data from DEB Online."""

from contextlib import contextmanager
from io import StringIO
from typing import Callable

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

URL = "https://deb-online.live/team/?teamId={}&divisionId={}"
XPATH_EXPRESSION = (
    "//div[contains(@class, '-hd-los-team-full-page-games')]"
    "//div[text()='Spiele']/following-sibling::div//table"
)


@contextmanager
def deb_scraper() -> Callable[[str], pd.DataFrame]:
    """DEB Online scraper context."""
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install()), options=firefox_options
    )

    def get_game_data(team_id: int, division_id: int) -> pd.DataFrame:
        driver.get(URL.format(team_id, division_id))

        table_element = WebDriverWait(driver, 60).until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, XPATH_EXPRESSION)
            )
        )
        table_html = table_element.get_attribute("outerHTML")

        dataframes = pd.read_html(StringIO(table_html), header=0)

        if not dataframes:
            raise RuntimeError("Did not find any tables to parse.")

        if not len(dataframes) == 1:
            raise RuntimeError("Found more than 1 table to parse.")

        (data,) = dataframes
        data["Datum"] = pd.to_datetime(data["Datum"], format="%d.%m.%Y")

        return data

    try:
        yield get_game_data
    finally:
        driver.quit()
