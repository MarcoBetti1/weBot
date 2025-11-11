"""DOM extractors for posts and profile data."""
from __future__ import annotations

import re
from typing import Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def extract_engagement_stats(label: str) -> Dict[str, int]:
    stats = {}
    pattern = r"(\d+(?:,\d+)*)\s+(\w+)"
    for value, key in re.findall(pattern, label):
        stats[key] = int(value.replace(",", ""))
    return stats


def fetch_post_data(post: WebElement) -> Optional[Dict[str, object]]:
    try:
        username = post.find_element(By.CSS_SELECTOR, "div[data-testid='User-Name'] span").text
    except Exception:
        username = None
    try:
        tweet_text = post.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']").text
    except Exception:
        tweet_text = ""
    try:
        time_element = post.find_element(By.CSS_SELECTOR, "time")
        link = time_element.find_element(By.XPATH, "./..").get_attribute("href")
    except Exception:
        link = None
    try:
        engagement_container = post.find_element(By.CSS_SELECTOR, "div[role='group'][aria-label]")
        engagement_label = engagement_container.get_attribute("aria-label")
        engagement_stats = extract_engagement_stats(engagement_label)
    except Exception:
        engagement_stats = {}
    return {
        "username": username,
        "tweet_text": tweet_text,
        "link": link,
        **engagement_stats,
    }
