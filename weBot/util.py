import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import json
def extract_engagement_stats(label):
    stats = {}
    pattern = r'(\d+(?:,\d+)*)\s+(\w+)'
    matches = re.findall(pattern, label)
    for value, key in matches:
        stats[key] = int(value.replace(',', ''))
    return stats

def fetch_post_data(post):
        try:
            # Extract username
            username = post.find_element(By.CSS_SELECTOR, "div[data-testid='User-Name'] span").text

            # Extract tweet text
            tweet_text = post.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']").text

            # Extract post link
            try:
                time_element = post.find_element(By.CSS_SELECTOR, "time")
                link = time_element.find_element(By.XPATH, "./..").get_attribute("href")
            except NoSuchElementException:
                link = None

            # Extract all engagement stats from the container div
            try:
                engagement_container = post.find_element(By.CSS_SELECTOR, "div[role='group'][aria-label]")
                engagement_label = engagement_container.get_attribute('aria-label')
                engagement_stats = extract_engagement_stats(engagement_label)
            except NoSuchElementException:
                engagement_stats = {}

            return {
                "username": username,
                "link": link,
                "tweet_text": tweet_text,
                **engagement_stats
            }
        except Exception as e:
            print(f"Error extracting data from post: {e}")
            return None

def save(name,data):
    with open(f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Data for {name} saved to {name}.json.")
