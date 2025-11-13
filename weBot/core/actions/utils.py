"""Utility helpers shared across action modules."""
from __future__ import annotations

import random
import time
from typing import Iterable, Tuple

from ...config.behaviour import get_behaviour_settings

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_for(driver, condition, timeout: float = 10):
    return WebDriverWait(driver, timeout).until(condition)


def human_delay_range(delay_range: Iterable[float]) -> Tuple[float, float]:
    values = list(delay_range)
    if len(values) == 2:
        return values[0], values[1]
    if len(values) == 1:
        return values[0], values[0]
    return 0.05, 0.2


def human_type(element: WebElement, content: str, delay_range: Iterable[float] | None = None) -> None:
    settings = get_behaviour_settings()
    default_range = settings.typing_delay.as_tuple()
    min_delay, max_delay = human_delay_range(delay_range or default_range)
    for char in content:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
    time.sleep(random.uniform(min_delay, max_delay))


def element_exists(driver, locator: tuple[By, str], timeout: float = 5) -> bool:
    try:
        wait_for(driver, EC.presence_of_element_located(locator), timeout=timeout)
        return True
    except Exception:
        return False


def random_delay(
    min_seconds: float | None = None,
    max_seconds: float | None = None,
    *,
    label: str | None = None,
) -> None:
    settings = get_behaviour_settings()
    configured_min, configured_max = settings.random_delay.as_tuple()

    explicit_min = float(min_seconds) if min_seconds is not None else None
    explicit_max = float(max_seconds) if max_seconds is not None else None

    if label:
        override = settings.named_ranges.get(label)
        if override:
            configured_min, configured_max = override.as_tuple()
            explicit_min = None
            explicit_max = None

    low = explicit_min if explicit_min is not None else configured_min
    high = explicit_max if explicit_max is not None else configured_max
    if high < low:
        high = low
    time.sleep(random.uniform(low, high))


def micro_wait() -> None:
    settings = get_behaviour_settings()
    low, high = settings.micro_wait.as_tuple()
    random_delay(low, high, label="micro_wait")
