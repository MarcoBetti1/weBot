import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

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

def simple_handle_search_and_save(bot, handle):
    # 1. Go to user page
    bot.navigate(f"https://twitter.com/{handle}")
    
    # 2. Extract user data
    user_profile_data = bot.get_user_profile_data()
    
    # 3. Extract posts from timeline (maybe limit to first 10 for example)
    user_posts = []
    for i in range(10):
        post_data = bot.fetch_post()
        if post_data:
            user_posts.append(post_data)
        success = bot.scroll()
        if not success:
            break
    
    # 4. Save to JSON
    result_data = {
        "profile": user_profile_data,
        "posts": user_posts,
    }
    with open(f"{handle}.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"Data for {handle} saved to {handle}.json.")
