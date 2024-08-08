from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import random
import re
import time
from secrets import username,password
from util import extract_engagement_stats


class weBot:
    def __init__(self, username, password, domain):
        self.username = username
        self.password = password
        self.driver = None
        self.domain = domain
        self.current_post_index = 0

    def random_delay(self, min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        #options.add_argument("--headless")  # Uncomment for headless mode, only works without this
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def login(self):
        print("Navigating to login page...")
        self.driver.get(self.domain)
        time.sleep(2)

        try:
            print("Finding username input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input = self.driver.find_element(By.NAME, "text")

            #username_input.send_keys(self.username)
            for char in self.username:
                username_input.send_keys(char)
                self.random_delay(0.05, 0.2)
            self.random_delay(0.05,0.2)

            username_input.send_keys(Keys.RETURN)
            time.sleep(3)  # Wait for the password screen to load

            print("Finding password input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            for char in self.password:
                password_input.send_keys(char)
                self.random_delay(0.05,0.2)
            self.random_delay(0.05,0.2)

            password_input.send_keys(Keys.RETURN)
            time.sleep(5)
            print("Logged in successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Current URL:", self.driver.current_url)
            print("Page Source:\n", self.driver.page_source)

    def navigate(self, page_url):
        print(f"Navigating to {page_url}...")
        self.driver.get(page_url)
        time.sleep(3)

    def scroll(self):
        print("Scrolling to the next post...")
        try:
            posts = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
            )
            if posts and self.current_post_index < len(posts):
                target_post = posts[self.current_post_index]
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", target_post)
                time.sleep(1)  # Allow time for scrolling and loading
                self.random_delay()
                self.current_post_index += 1
                #print(f"Scrolled to post {self.current_post_index}")
            else:
                print("No more posts to scroll to. Attempting to load more...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(10)  # Wait for potential new posts to load
                new_posts = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                if len(new_posts) > len(posts):
                    print("New posts loaded. Resetting scroll index.")
                    self.current_post_index = len(posts)
                else:
                    print("No new posts loaded. End of feed reached.")
                    self.current_post_index = 0  # Reset to top if no new posts
        except TimeoutException:
            print("Timeout waiting for posts to load.")
        except Exception as e:
            print(f"Error during scrolling: {e}")

    def random_delay(self, min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

    def _find_and_click_button(self, data_testid, aria_label_pattern=None):
            try:
                if aria_label_pattern:
                    button = self.driver.find_element(By.CSS_SELECTOR, f"button[data-testid='{data_testid}'][aria-label*='{aria_label_pattern}']")
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, f"button[data-testid='{data_testid}']")
                button.click()
                self.random_delay()  # Random delay after clicking
                return True
            except NoSuchElementException:
                print(f"Couldn't find the button with data-testid '{data_testid}'.")
                return False
            except Exception as e:
                print(f"Error interacting with button (data-testid: '{data_testid}'): {e}")
                return False

    def save_post(self):
        self.random_delay()
        return self._find_and_click_button("bookmark")

    def like(self):
        self.random_delay()
        return self._find_and_click_button("like", "Likes. Like")

    def retweet(self):
        self.random_delay()
        if self._find_and_click_button("retweet", "reposts. Repost"):
            try:
                retweet_confirm = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='retweetConfirm']"))
                )
                self.random_delay(0.5, 2)  # Shorter delay before confirming
                retweet_confirm.click()
                self.random_delay()
                return True
            except TimeoutException:
                print("Couldn't find the retweet confirmation button.")
                return False
        return False

    def send_reply(self, text):
        self.random_delay()
        try:
            if not self._find_and_click_button("reply", "Replies. Reply"):
                return False

            reply_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            for char in text:
                reply_input.send_keys(char)
                self.random_delay(0.05, 0.2)  # Simulate human typing speed

            self.random_delay(0.5, 2)  # Short pause before sending
            reply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton']"))
            )
            reply_button.click()
            self.random_delay(1, 3)  # Wait for the reply to be sent

            return True
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False

    def fetch_post_data(self, post):
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

    def fetch_post(self):
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
                )
                posts = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                if posts and self.current_post_index > 0 and self.current_post_index <= len(posts):
                    post = posts[self.current_post_index - 1]  # -1 because we've already incremented in scroll()
                    post_data = self.fetch_post_data(post)
                    #print(post_data)
                    return post_data
                else:
                    print("No posts found at the current index.")
                    return None
            except TimeoutException:
                print("Timeout waiting for posts to load in fetch_post.")
                return None
            except Exception as e:
                print(f"Error fetching data from center post: {e}")
                return None

    def click(self):
        #Click on the post currently in the center of the viewport to view its details and replies
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
            if posts:
                post = posts[0]
                self.scroll()
                post.click()
                time.sleep(3)  # Wait for the post details to load
                print("Clicked on center post")
            else:
                print("No posts found in the center to click.")
        except Exception as e:
            print(f"Error clicking on center post: {e}")

    def interact(self, action):
        #Interact with the post currently in the center of the viewport
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
            if posts:
                post = posts[0]
                self.scroll()
                if action == "like":
                    like_button = post.find_element(By.CSS_SELECTOR, "div[data-testid='like']")
                    like_button.click()
                    time.sleep(1)
                    print("Liked center post")
                elif action == "retweet":
                    retweet_button = post.find_element(By.CSS_SELECTOR, "div[data-testid='retweet']")
                    retweet_button.click()
                    time.sleep(1)
                    print("Retweeted center post")
                # Add more actions and make each a method
            else:
                print("No posts found in the center to interact with.")
        except Exception as e:
            print(f"Error interacting with center post: {e}")

    def quit(self):
        if self.driver:
            self.driver.quit()
