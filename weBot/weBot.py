from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from weBot.util import extract_engagement_stats
import random
import re
import time


class weBot:
    def __init__(self, username, password, loginDomain, homeDomain):
        self.username = username
        self.password = password
        self.driver = None
        self.login_domain = loginDomain 
        self.home_domain = homeDomain
        self.current_post_index = 0
        self.posts = []

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        #options.add_argument("--headless")  
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def sim_type(self,input,content): # simulate human typing
        for char in content:
            input.send_keys(char)
            self.random_delay(0.05,0.2)
        self.random_delay(0.05,0.2)

    def login(self):
        print("Navigating to login page...")
        self.driver.get(self.login_domain)
        self.random_delay(1,3)

        try:
            print("Finding username input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input = self.driver.find_element(By.NAME, "text")

            #username_input.send_keys(self.username)
            self.sim_type(username_input,self.username)

            username_input.send_keys(Keys.RETURN)

            self.random_delay(2,5)

            print("Finding password input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            self.sim_type(password_input,self.password)

            password_input.send_keys(Keys.RETURN)
            self.random_delay(3,5)
            print("Logged in successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Current URL:", self.driver.current_url)
            print("Page Source:\n", self.driver.page_source)

    def navigate(self, page_url):
        print(f"Navigating to {page_url}...")
        self.driver.get(page_url)
        time.sleep(3)

    def update_post_list(self):
        self.posts = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
        )

    def reset_scroll_index(self):
        self.current_post_index = 0
        self.update_post_list()

    def get_centered_post(self):
        return self.driver.execute_script("""
            var posts = document.querySelectorAll("article[data-testid='tweet']");
            var windowHeight = window.innerHeight;
            var centerY = windowHeight / 2;
            var closest = null;
            var closestDistance = Infinity;
            for (var i = 0; i < posts.length; i++) {
                var rect = posts[i].getBoundingClientRect();
                var distance = Math.abs(rect.top + rect.height / 2 - centerY);
                if (distance < closestDistance) {
                    closest = posts[i];
                    closestDistance = distance;
                }
            }
            return closest;
        """)

    def scroll(self):
        print("Scrolling to the next post...")
        try:
            self.update_post_list()
            if self.current_post_index < len(self.posts):
                target_post = self.posts[self.current_post_index]
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", target_post)
                self.random_delay(0.8, 2.3)
                
                # Update the post list after scrolling
                self.update_post_list()
                
                # Find the new position of the target post
                new_post_index = next((i for i, post in enumerate(self.posts) if post == target_post), None)
                
                if new_post_index is not None:
                    self.current_post_index = new_post_index + 1
                else:
                    # If the target post is not found (it might have been removed), just increment
                    self.current_post_index += 1
                
                print(f"Scrolled to post {self.current_post_index}")
                return True
            else:
                print("No more posts to scroll to. Attempting to load more...")
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay(3, 5)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height > last_height:
                    self.update_post_list()
                    print("New posts loaded. Continuing from current index.")
                    return self.scroll()
                else:
                    print("No new posts loaded. End of feed reached.")
                    self.current_post_index = 0  # Reset to top if no new posts
                    return False
        except TimeoutException:
            print("Timeout waiting for posts to load.")
            return False
        except Exception as e:
            print(f"Error during scrolling: {e}")
            return False

    def random_delay(self, min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

    def _find_and_click_button(self, data_testid, aria_label_pattern=None):
        try:
            # Find the centered post
            centered_post = self.get_centered_post()

            if not centered_post:
                print("No centered post found.")
                return False

            # Find the button within the centered post
            if aria_label_pattern:
                button = centered_post.find_element(By.CSS_SELECTOR, f"button[data-testid='{data_testid}'][aria-label*='{aria_label_pattern}']")
            else:
                button = centered_post.find_element(By.CSS_SELECTOR, f"button[data-testid='{data_testid}']")

            # Try to click using JavaScript
            try:
                self.driver.execute_script("arguments[0].click();", button)
            except Exception:
                # If JavaScript click fails, try regular click
                ActionChains(self.driver).move_to_element(button).click().perform()
            return True
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            print(f"Error interacting with button (data-testid: '{data_testid}'): {e}")
            return False

    def save_post(self):
        return self._find_and_click_button("bookmark")

    def like(self):
        return self._find_and_click_button("like", "Likes. Like")

    def retweet(self):
        if self._find_and_click_button("retweet", "reposts. Repost"):
            try:
                retweet_confirm = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='retweetConfirm']"))
                )
                self.random_delay(0.2, 0.4)  # Shorter delay before confirming
                self.driver.execute_script("arguments[0].click();", retweet_confirm)
                return True
            except (TimeoutException, ElementClickInterceptedException) as e:
                print(f"Couldn't confirm retweet: {e}")
                return False
        return False

    def click(self):
        # Click on the post currently in the center of the viewport to view its details and replies
        self.scroll() # So we arent focused on the post we clicked on
        try:
            centered_post = self.get_centered_post()
            if centered_post:
                # Use JavaScript to click the post, as it's more reliable than Selenium's click
                self.driver.execute_script("arguments[0].click();", centered_post)
                print("Clicked on center post")
            else:
                print("No post found in the center to click.")
        except Exception as e:
            print(f"Error clicking on center post: {e}")
    
    def click_author(self):
        try:
            # Find the centered post
            centered_post = self.get_centered_post()
            if not centered_post:
                print("No centered post found.")
                return False

            # Find the author's username element within the centered post
            username_element = WebDriverWait(centered_post, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='User-Name'] a"))
            )
            
            # Scroll the username into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", username_element)
            
            self.random_delay(0.5, 1)  # Short delay after scrolling
            
            # Click the username using JavaScript
            self.driver.execute_script("arguments[0].click();", username_element)
            
            self.random_delay(2, 3)  # Wait for the profile page to load
            
            print(f"Clicked on author's username")
            return True

        except TimeoutException:
            print("Author's username not found or not clickable")
            return False
        except Exception as e:
            print(f"Error clicking author's username: {e}")
            return False
        
    def go_back(self):
        # Click the back button with specific attributes
        try:
            # Wait for the back button to be clickable
            back_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Back'][data-testid='app-bar-back']"))
            )
            # Use JavaScript to click the button, as it's more reliable than Selenium's click
            self.driver.execute_script("arguments[0].click();", back_button)
            print("Clicked back button")
            
            # After going back, reset the scroll index and update the post list
            self.reset_scroll_index()
        except TimeoutException:
            print("Back button not found or not clickable")
            # Attempt to find the button and print more details for debugging
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']")
                print(f"Button found but not clickable. Button text: {button.text}")
                print(f"Button is displayed: {button.is_displayed()}")
                print(f"Button is enabled: {button.is_enabled()}")
            except NoSuchElementException:
                print("Back button not found in the DOM")
        except Exception as e:
            print(f"Error clicking back button: {e}")

    def create_post(self, text):
        self.to_home()
        try:
            # Find and click on the post textarea
            post_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            post_input.click()

            self.sim_type(post_input,text)

            # Find and click the post button
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButtonInline']"))
            )
            self.random_delay(1, 3)  # Wait for the post to be sent
            post_button.click()


            print("Post created successfully.")
            return True
        except Exception as e:
            print(f"Error creating post: {e}")
            return False

    def send_reply(self, text):
        try:
            if not self._find_and_click_button("reply", "Replies. Reply"):
                return False

            reply_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            self.sim_type(reply_input,text)

            reply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton']"))
            )
            self.random_delay(1, 3) 
            reply_button.click()
            

            return True
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False

    def follow(self):
        try:
            # Wait for the profile page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
            )

            # Extract the username from the profile page
            username_element = self.driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserName'] span")
            username = username_element.text.split("@")[-1]

            # Look for the follow button using a more specific selector
            follow_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[aria-label^='Follow @{username}'][data-testid$='-follow']"))
            )
            
            # Scroll the button into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", follow_button)
            
            self.random_delay(0.5, 1)  # Short delay after scrolling
            
            # Click the follow button using JavaScript
            self.driver.execute_script("arguments[0].click();", follow_button)
            
            self.random_delay(1, 2)  # Short delay after clicking
            
            print(f"Followed @{username}")
            return True

        except TimeoutException:
            print(f"Follow button not found or not clickable for @{username}")
            return False
        except Exception as e:
            print(f"Error following @{username}: {e}")
            return False

    def unfollow(self):
        try:
            # Wait for the profile page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
            )

            # Extract the username from the profile page
            username_element = self.driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserName'] span")
            username = username_element.text.split("@")[-1]

            # Look for the unfollow button using a more specific selector
            unfollow_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[aria-label^='Unfollow @{username}']"))
            )
            
            # Scroll the button into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unfollow_button)
            
            self.random_delay(0.5, 1)  # Short delay after scrolling
            
            # Click the unfollow button using JavaScript
            self.driver.execute_script("arguments[0].click();", unfollow_button)
            
            self.random_delay(1, 2)  # Short delay after clicking
            
            # Confirm unfollow in the dialog that appears
            try:
                confirm_unfollow = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem']//span[text()='Unfollow']"))
                )
                self.driver.execute_script("arguments[0].click();", confirm_unfollow)
                self.random_delay(1, 2)  # Short delay after confirming
            except TimeoutException:
                print("Unfollow confirmation dialog not found")
                return False
            
            print(f"Unfollowed @{username}")
            return True

        except TimeoutException:
            print(f"Unfollow button not found or not clickable for @{username}")
            return False
        except Exception as e:
            print(f"Error unfollowing @{username}: {e}")
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
            centered_post = self.get_centered_post()
            if centered_post:
                post_data = self.fetch_post_data(centered_post)
                return post_data
            else:
                print("No centered post found.")
                return None
        except TimeoutException:
            print("Timeout waiting for posts to load in fetch_post.")
            return None
        except Exception as e:
            print(f"Error fetching data from center post: {e}")
            return None

    def to_home(self):
        self.navigate(self.home_domain)
        self.random_delay(2,4)
        self.reset_scroll_index()
        # self.driver.execute_script("window.scrollTo(0, 0);")

    def quit(self):
        if self.driver:
            self.driver.quit()
