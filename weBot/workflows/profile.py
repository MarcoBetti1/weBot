"""Profile data extraction routines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..bot import BotController
from ..core.actions import navigation, social
from ..core.actions.utils import random_delay
from ..core.state import PageState


@dataclass
class ProfileData:
    display_name: str
    handle: str
    bio: str
    followers_count: str
    following_count: str
    followers_list: Optional[List[str]] = None
    following_list: Optional[List[str]] = None


def _ensure_profile(bot: BotController, handle: str) -> None:
    navigation.navigate_to(bot.driver, bot.context, f"https://twitter.com/{handle}")
    WebDriverWait(bot.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='UserName']")))
    bot.context.update_state(PageState.PROFILE, handle=handle)


def fetch_profile(bot: BotController, handle: str, *, descriptive: bool = False) -> ProfileData:
    _ensure_profile(bot, handle)
    driver = bot.driver

    try:
        display_name = driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserName']").text.split("\n")[0]
    except NoSuchElementException:
        display_name = ""

    handle_value = driver.current_url.rstrip("/").split("/")[-1]

    try:
        bio = driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserDescription']").text
    except NoSuchElementException:
        bio = ""

    try:
        followers_count = driver.find_element(By.CSS_SELECTOR, "a[href$='/verified_followers'] > span > span").text
    except NoSuchElementException:
        followers_count = "0"

    try:
        following_count = driver.find_element(By.CSS_SELECTOR, "a[href$='/following'] > span > span").text
    except NoSuchElementException:
        following_count = "0"

    followers_list: Optional[List[str]] = None
    following_list: Optional[List[str]] = None

    if descriptive:
        bot.driver.get(f"https://twitter.com/{handle_value}/followers")
        random_delay(0.8, 1.4, label="profile_fetch")
        followers_list, _ = social.collect_handles_from_modal(driver)

        bot.driver.get(f"https://twitter.com/{handle_value}/following")
        random_delay(0.8, 1.4, label="profile_fetch")
        following_list, _ = social.collect_handles_from_modal(driver)

    return ProfileData(
        display_name=display_name,
        handle=handle_value,
        bio=bio,
        followers_count=followers_count,
        following_count=following_count,
        followers_list=followers_list,
        following_list=following_list,
    )
