"""Utility helpers shared across action modules."""
from __future__ import annotations

import random
import time
from typing import Iterable, Tuple

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


def human_type(element: WebElement, content: str, delay_range: Iterable[float] = (0.05, 0.2)) -> None:
    min_delay, max_delay = human_delay_range(delay_range)
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


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def micro_wait() -> None:
    random_delay(0.05, 0.25)
