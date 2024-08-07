from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from secrets import username,password

class weBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")  # Uncomment for headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def login(self):
        print("Navigating to Twitter login page...")
        self.driver.get("https://twitter.com/login")
        time.sleep(2)

        try:
            print("Finding username input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input = self.driver.find_element(By.NAME, "text")

            print("Username input field found.")
            username_input.send_keys(self.username)
            username_input.send_keys(Keys.RETURN)
            time.sleep(3)  # Wait for the password screen to load

            print("Finding password input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            print("Password input field found.")
            password_input.send_keys(self.password)
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
        """Scroll to the next post and center it in the viewport"""
        posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
        if posts:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", posts[0])
            time.sleep(2)  # Allow time for scrolling and loading
        else:
            print("No posts found to scroll to.")

    def fetch_post(self):
        """Fetch data from the post currently in the center of the viewport"""
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
            if posts:
                post = posts[0]
                self.scroll()
                post_data = self.fetch_post(post)
                print(post_data)
                return post_data
            else:
                print("No posts found in the center.")
                return None
        except Exception as e:
            print(f"Error fetching data from center post: {e}")
            return None

    def click(self):
        """Click on the post currently in the center of the viewport to view its details and replies"""
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
        """Interact with the post currently in the center of the viewport (like, retweet, etc.)"""
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
                # Add more actions as needed
            else:
                print("No posts found in the center to interact with.")
        except Exception as e:
            print(f"Error interacting with center post: {e}")

    def quit(self):
        self.driver.quit()
    # Example usage in the main script
if __name__ == "__main__":
    page_url = "https://twitter.com/home"  # Example URL

    bot = weBot(username, password)
    bot.setup_driver()
    bot.login()
    #bot.navigate(page_url) Automaitcally goes home after login


    bot.scroll()
    bot.fetch_post()
    bot.click()
    bot.fetch_post()  # View the top post in the thread
    bot.interact(action="like")  # Like the top post or a reply

    bot.quit()
