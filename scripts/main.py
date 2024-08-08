from weBot import weBot
from secrets import username,password
from brains import process_posts
def main():
    page_url = "https://twitter.com/home"  # Example URL

    # positive_keywords = ['great', 'awesome', 'excellent', 'amazing', 'good', 'nice', 'love', 'best']
    # negative_keywords = ['bad', 'worst', 'terrible', 'awful', 'hate', 'dislike', 'poor']

    bot = weBot(username, password, loginDomain="https://twitter.com/login",homeDomain=page_url)
    bot.setup_driver()
    bot.login()
    # #bot.navigate(page_url) Automaitcally goes home after login
    # bot.scroll(1)
    # print(bot.fetch_post())
    # bot.scroll(3)

    for i in range(200):
        process_posts(bot,5)
        bot.to_home()
        bot.random_delay(3,4)
        process_posts(bot,5)
        bot.to_home()

    bot.quit()



if __name__ == "__main__":
    main()
