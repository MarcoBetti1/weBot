from weBot.weBot import weBot
from scripts.secrets import username,password
from scripts.brains import process_posts
import os
def main():
    page_url = "https://twitter.com/home"  # Example URL
    login_url = "https://twitter.com/login" 
    # positive_keywords = ['great', 'awesome', 'excellent', 'amazing', 'good', 'nice', 'love', 'best']
    # negative_keywords = ['bad', 'worst', 'terrible', 'awful', 'hate', 'dislike', 'poor']

    bot = weBot(username, password, loginDomain=login_url,homeDomain=page_url)
    bot.setup_driver()


    bot.login()

    # Actions
    print(bot.fetch_post())
    bot.scroll()
    bot.click()
    bot.follow()
    bot.go_back()
    # Quit
    bot.quit()



if __name__ == "__main__":
    main()
