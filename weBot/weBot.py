from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from weBot.util import extract_engagement_stats, fetch_post_data
import pickle
import random
import time

class weBot:
    def __init__(self, username, password, email, loginDomain, homeDomain):
        self.username = username
        self.password = password
        self.email = email
        self.driver = None
        self.login_domain = loginDomain 
        self.home_domain = homeDomain
        self.current_post_index = 0
        self.posts = []

    def setup_driver(self):
        options = webdriver.ChromeOptions()
    
        # Set the window size
        options.add_argument("--window-size=400,1080")  # Example resolution: 1280x800
        
        # Set the window position on the screen
        options.add_argument("--window-position=0,100")  # Example position: x=100, y=100

        # Other options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def save_cookies(self, file_path="cookies.pkl"):
        with open(file_path, "wb") as file:
            pickle.dump(self.driver.get_cookies(), file)
        print("Cookies saved.")

    def load_cookies(self, file_path="cookies.pkl"):
        try:
            with open(file_path, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            print("Cookies loaded.")
        except FileNotFoundError:
            print("No cookies. Proceeding without loading cookies.")

    def sim_type(self,input,content): # simulate human typing
        for char in content:
            input.send_keys(char)
            self.random_delay(0.05,0.2)
        self.random_delay(0.05,0.2)

    def login(self,method="creds"):
        print("Navigating to login page...")
        self.driver.get(self.login_domain)
        self.load_cookies()

        self.driver.get(self.login_domain)  # Refresh the page with cookies loaded
        self.random_delay(0.1, 0.9)

        if "login" not in self.driver.current_url:  # If already logged in
            print("Logged in using saved cookies.")
            return
        
        if method =="creds":
            self.login_df()
        # if method =="ggl":
        #     self.login_ggl() # login through google, unimplemented for now

    def login_df(self): # Log in by username and password
        try:
            # Step 1: Enter Username
            print("Finding username input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input = self.driver.find_element(By.NAME, "text")
            self.sim_type(username_input, self.username)
            username_input.send_keys(Keys.RETURN)
            self.random_delay(2, 5)

            # Step 2: Detect Unusual Activity Prompt
            try:
                print("Checking for unusual activity prompt...")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//label[contains(., 'Phone or email')]")
                    )
                )
                print("Unusual activity detected. Entering email...")
                challenge_input = self.driver.find_element(By.NAME, "text")
                self.sim_type(challenge_input, self.email)
                challenge_input.send_keys(Keys.RETURN)
                self.random_delay(3, 5)

            except TimeoutException:
                print("No unusual activity prompt detected. Continuing login process...")

            # Step 3: Enter Password
            print("Finding password input field...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            self.sim_type(password_input, self.password)
            password_input.send_keys(Keys.RETURN)
            self.random_delay(3, 5)

            print("Logged in successfully.")
            self.save_cookies()  # Save cookies after successful login

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

    def repost(self, quote=None):
        if self._find_and_click_button("retweet", "reposts. Repost"):
            try:
                if quote:
                    # Click the "Quote" button
                    quote_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[@href='/compose/post']"))
                    )
                    self.random_delay(0.2, 0.4)  # Short delay before clicking
                    self.driver.execute_script("arguments[0].click();", quote_button)
                    self.random_delay(2, 4)  # Wait for the quote input to load

                    # Enter the quote text
                    quote_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
                    )
                    self.sim_type(quote_input, quote)

                    # Click the "Post" button to post the quote tweet
                    tweet_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton']"))
                    )
                    self.driver.execute_script("arguments[0].click();", tweet_button)
                    print("Quote tweet posted successfully.")
                    return True

                else:
                    # Confirm normal repost
                    retweet_confirm = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='retweetConfirm']"))
                    )
                    self.random_delay(0.2, 0.4)  # Shorter delay before confirming
                    self.driver.execute_script("arguments[0].click();", retweet_confirm)
                    print("Repost confirmed successfully.")
                    return True

            except (TimeoutException, ElementClickInterceptedException) as e:
                print(f"Couldn't complete the repost action: {e}")
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

            # Look for the follow button using a more general selector
            follow_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid][contains(@aria-label, 'Follow')]"))
            )
            
            # Scroll the button into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", follow_button)
            
            self.random_delay(0.5, 1)  # Short delay after scrolling
            
            # Click the follow button using JavaScript
            self.driver.execute_script("arguments[0].click();", follow_button)
            
            self.random_delay(1, 2)  # Short delay after clicking
            
            print(f"Followed the user.")
            return True

        except TimeoutException:
            print("Follow button not found or not clickable.")
            return False
        except Exception as e:
            print(f"Error following user: {e}")
            return False

    def unfollow(self):
        try:
            # Wait for the profile page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
            )

            # Check if the account is subscribable by looking for the "Subscribe to" button
            try:
                subscribe_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Subscribe to')]")
                is_subscribable = True
                print("Account is subscribable.")
            except NoSuchElementException:
                is_subscribable = False
                print("Account is not subscribable.")

            if is_subscribable:
                # Unfollow logic for subscribable accounts
                try:
                    unfollow_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Unfollow')]"))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unfollow_button)
                    self.random_delay(0.5, 1)
                    self.driver.execute_script("arguments[0].click();", unfollow_button)
                    self.random_delay(1, 2)

                    # Confirm unfollow in the dropdown menu
                    confirm_unfollow_dropdown = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem']//span[contains(text(), 'Unfollow')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", confirm_unfollow_dropdown)
                    self.random_delay(1, 2)
                    print("Unfollowed the subscribable account.")
                    return True
                except Exception as e:
                    print(f"Error unfollowing subscribable account: {e}")
                    return False
            else:
                # Unfollow logic for regular accounts
                try:
                    unfollow_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Following')]"))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unfollow_button)
                    self.random_delay(0.5, 1)
                    self.driver.execute_script("arguments[0].click();", unfollow_button)
                    self.random_delay(1, 2)

                    # Confirm unfollow in the full-screen confirmation dialog
                    confirm_unfollow = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='confirmationSheetConfirm']"))
                    )
                    self.driver.execute_script("arguments[0].click();", confirm_unfollow)
                    self.random_delay(1, 2)
                    print("Unfollowed the regular account.")
                    return True
                except Exception as e:
                    print(f"Error unfollowing regular account: {e}")
                    return False

        except TimeoutException:
            print("Unfollow button not found or not clickable.")
            return False
        except Exception as e:
            print(f"Error in unfollowing logic: {e}")
            return False

    def search(self, query):
        try:
            # Step 1: Click the "Search and explore" button
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Search and explore']"))
            )
            self.driver.execute_script("arguments[0].click();", search_button)
            self.random_delay(2, 4)

            # Step 2: Wait for the search bar to appear
            search_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='SearchBox_Search_Input']"))
            )

            # Step 3: Type the search query
            self.sim_type(search_input, query)
            self.random_delay(0.5, 1)

            # Step 4: Press "Enter" to execute the search
            search_input.send_keys(Keys.RETURN)
            print(f"Search executed for query: {query}")
            self.random_delay(2, 4)

        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"Couldn't complete the search action: {e}")
            return False

        return True

    def type_search(self, query, search_type="People"):
        # Perform the search
        if not self.search(query):
            return False

        # Determine the appropriate tab to click based on search_type
        type_mapping = {
            "Top": "//a[@href='/search?q={}&src=typed_query']",
            "Latest": "//a[contains(@href,'&f=live')]",
            "People": "//a[contains(@href,'&f=user')]",
            "Media": "//a[contains(@href,'&f=media')]",
            "Lists": "//a[contains(@href,'&f=lists')]"
        }

        # Format the XPath with the query if needed
        type_xpath = type_mapping.get(search_type, type_mapping["Top"]).format(query)

        try:
            # Click the appropriate search type tab
            search_type_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, type_xpath))
            )
            self.driver.execute_script("arguments[0].click();", search_type_tab)
            print(f"Selected search type: {search_type}")
            self.random_delay(2, 4)

        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"Couldn't select search type {search_type}: {e}")
            return False

        return True

    def type_search_click(self, query, numresult=1, search_type="People"):
        # Perform the search and select the type
        if not self.type_search(query, search_type):
            return False

        try:
            # Initialize counters and state
            current_result = 0
            result_found = False
            item_xpath = ""

            # Determine the XPath based on the search type
            if search_type == "People":
                item_xpath = "//button[@data-testid='UserCell']"
            elif search_type == "Latest":
                item_xpath = "//article[@role='article']"

            while not result_found:
                try:
                    # Identify all visible items (UserCell or Article)
                    items = self.driver.find_elements(By.XPATH, item_xpath)
                    
                    if len(items) == 0:
                        print("No items found. Retrying...")
                    
                        self.driver.execute_script("window.scrollBy(0, 100);")  # Scroll slightly to load more
                        self.random_delay(1, 2)
                        continue

                    # Loop through the visible items
                    for item in items:
                        current_result += 1
                        if current_result == numresult:
                            # Scroll the specific item into view and click it
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            self.random_delay(0.5, 1)
                            self.driver.execute_script("arguments[0].click();", item)
                            print(f"Clicked on result number {numresult} for search '{query}' in '{search_type}'")
                            result_found = True
                            self.random_delay(2, 4)
                            break

                    if not result_found:
                        # Scroll down to load more results
                        self.driver.execute_script("window.scrollBy(0, 300);")  # Scroll slightly to load more
                        self.random_delay(1, 2)

                except Exception as e:
                    print(f"Couldn't select search result number {numresult} for {search_type}: {e}")
                    return False

        except Exception as e:
            print(f"An error occurred: {e}")
            return False

        return True

    def fetch_post(self):
        try:
            centered_post = self.get_centered_post()
            if centered_post:
                post_data = fetch_post_data(centered_post)
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

    def get_user_profile_data(self, descriptive=False):
        try:
            # Wait until the page loads and a relevant element is present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='UserName']"))
            )
            
            # Extract the display name (username)
            try:
                display_name_el = self.driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserName']")
                display_name = display_name_el.text.split("\n")[0]
            except NoSuchElementException:
                display_name = ""

            # Extract handle from the URL of the current page
            handle = self.driver.current_url.split("/")[-1]
            
            # Extract bio
            try:
                bio_el = self.driver.find_element(By.CSS_SELECTOR, "div[data-testid='UserDescription']")
                bio = bio_el.text
            except NoSuchElementException:
                bio = ""
            
            # Extract followers and following counts
            try:    
                followers_el = self.driver.find_element(By.CSS_SELECTOR, "a[href$='/verified_followers'] > span > span")
                followers_count = followers_el.text
            except NoSuchElementException:
                followers_count = "0"

            try:
                following_el = self.driver.find_element(By.CSS_SELECTOR, "a[href$='/following'] > span > span")
                following_count = following_el.text
            except NoSuchElementException:
                following_count = "0"
            
            if not descipritve:
                return {
                "display_name": display_name,
                "handle": handle,
                "bio": bio,
                "followers_count": followers_count,
                "following_count": following_count
            }
            else:
                follower_list = []
                following_list = []
                try:
                    link_selector = "a[href$='/verified_followers']"
                    modal_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, link_selector))
                    )
                    self.driver.execute_script("arguments[0].click();", modal_link)
                    
                    self.random_delay(1, 3)  # Wait for modal to open
                    follower_list = self.get_user_list_from_modal()
                    # call script to iterate through followers and get handles
                    # append
                except NoSuchElementException:
                    follower_list.append("err")
                    print("error in discpritive follower list")
                try:
                    # call script to iterate through following and get handles
                    link_selector = "a[href$='/following']"
                    modal_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, link_selector))
                    )
                    self.driver.execute_script("arguments[0].click();", modal_link)
                    
                    self.random_delay(2, 4)  # Wait for modal to open

                except NoSuchElementException:
                    #following_list = "err"
                    print("error in discpritive following list")

                
                return {
                "display_name": display_name,
                "handle": handle,
                "bio": bio,
                "followers_count": followers_count,
                "following_count": following_count,
                "followers_list": followers_list,
                "following_list": following_list,

            }
            #print(f"display_name: {display_name}, handle: {handle}, bio: {bio}, followers_count: {followers_count}, following_count: {following_count}")
            
        except Exception as e:
            print(f"Error getting user profile data: {e}")
            return None

    def get_user_list_from_modal(self, list_type="followers", max_count=None):
        """
        Scrape all user handles from the 'followers' or 'following' modal.
        Scrolls incrementally to ensure all followers are captured.
        """
        try:
            # Define the selectors
            modal_selector = "div[aria-label*='Timeline:']"  # Matches 'Timeline: Followers' or 'Timeline: Following'
            user_cell_selector = "div[data-testid='cellInnerDiv']"
            handle_link_selector = "a[href^='/']"
            
            # Wait for the modal to appear
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
            )
            
            # Get the scrollable modal container
            modal_container = self.driver.find_element(By.CSS_SELECTOR, modal_selector)
            
            # Initialize storage for unique handles
            seen_handles = set()
            last_seen_count = 0

            while True:
                # Find all user cells in the modal
                user_cells = modal_container.find_elements(By.CSS_SELECTOR, user_cell_selector)
                
                for cell in user_cells:
                    try:
                        # Ensure this cell represents a real follower with a button
                        if cell.find_element(By.CSS_SELECTOR, "button[data-testid='UserCell']"):
                            # Extract the handle
                            link = cell.find_element(By.CSS_SELECTOR, handle_link_selector)
                            href = link.get_attribute("href")
                            if href:
                                handle = href.split("/")[-1]
                                if handle and handle not in seen_handles:
                                    seen_handles.add(handle)
                                    print(f"Found follower handle: {handle}")
                                    if max_count and len(seen_handles) >= max_count:
                                        print(f"Reached max_count of {max_count} {list_type}.")
                                        return list(seen_handles)
                    except NoSuchElementException:
                        # Skip if required elements are missing
                        continue
                
                # Scroll the modal container slightly
                print("poop")
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", modal_container)
                self.random_delay(1, 2)
                print("test")
                
                # Check if new elements are loaded
                current_seen_count = len(user_cells)
                if current_seen_count == last_seen_count:
                    # No new elements detected, end scrolling
                    print(f"No new {list_type} found. Ending scroll.")
                    break
                last_seen_count = current_seen_count
            return list(seen_handles)
        
        except Exception as e:
            print(f"Error retrieving user list ({list_type}): {e}")
            return []



    def quit(self):
        if self.driver:
            self.driver.quit()
