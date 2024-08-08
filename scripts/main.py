from weBot import weBot
from secrets import username,password
from brains import process_posts
def main():
    page_url = "https://twitter.com/home"  # Example URL

    positive_keywords = ['great', 'awesome', 'excellent', 'amazing', 'good', 'nice', 'love', 'best']
    negative_keywords = ['bad', 'worst', 'terrible', 'awful', 'hate', 'dislike', 'poor']

    bot = weBot(username, password, domain="https://twitter.com/login",positive_keywords=positive_keywords,negative_keywords=negative_keywords)
    bot.setup_driver()
    bot.login()
    # #bot.navigate(page_url) Automaitcally goes home after login
    # bot.scroll(1)
    # print(bot.fetch_post())
    # bot.scroll(3)
    for i in range(200):
        process_posts(bot,6)
        bot.to_home()
        bot.to_home()
        bot.random_delay(4,5)

    bot.quit()



if __name__ == "__main__":
    main()
