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
        # options.add_argument("--headless") # This runs it quietly without showing up as an application
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

    def fetch_posts_data(self, page_url, scrolls=5): # none if this is tested yet
        print(f"Navigating to {page_url}...")
        self.driver.get(page_url)
        time.sleep(3)
        posts_data = []

        for _ in range(scrolls):
            print(f"Scrolling... {_ + 1}")
            posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
            for post in posts:
                try:
                    username = post.find_element(By.CSS_SELECTOR, "div.r-1f6r7vd > div > div > div > span").text
                    link = post.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    stats = post.find_elements(By.CSS_SELECTOR, "div[role='group'] span")

                    comments = int(stats[0].text) if stats[0].text.isdigit() else 0
                    retweets = int(stats[1].text) if stats[1].text.isdigit() else 0
                    likes = int(stats[2].text) if stats[2].text.isdigit() else 0
                    views = 0  # Views may need additional handling

                    posts_data.append({
                        "username": username,
                        "link": link,
                        "comments": comments,
                        "retweets": retweets,
                        "likes": likes,
                        "views": views
                    })
                except Exception as e:
                    print(f"Error extracting data from post: {e}")

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        return posts_data

    def quit(self):
        self.driver.quit()

if __name__ == "__main__":
    # username = "your_username"
    # password = "your_password"
    page_url = "https://twitter.com/explore/tabs/for-you"  # FYP Url

    scraper = weBot(username, password)
    scraper.setup_driver()
    scraper.login()
    data = scraper.fetch_posts_data(page_url)
    scraper.quit()

    for post in data:
        print(post)
