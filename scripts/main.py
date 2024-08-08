from weBot import weBot
from secrets import username,password
def main():
    page_url = "https://twitter.com/home"  # Example URL

    bot = weBot(username, password, domain="https://twitter.com/login")
    bot.setup_driver()
    bot.login()
    #bot.navigate(page_url) Automaitcally goes home after login


    bot.scroll()
    bot.like()
    bot.retweet()
    bot.save_post()
    bot.send_reply("fartman")
    bot.fetch_post()
    bot.scroll()
    bot.like()
    bot.fetch_post()
    bot.scroll()
    bot.fetch_post()
    # bot.scroll()
    # bot.scroll()
    # bot.scroll()
    #bot.fetch_post()
    # bot.click()
    # bot.scroll()
    # bot.scroll()
    # bot.scroll()
    # bot.scroll()
    #bot.fetch_post()  # View the top post in the thread
    #bot.interact(action="like")  # Like the top post or a reply

    bot.quit()

if __name__ == "__main__":
    main()
