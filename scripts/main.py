from weBot import weBot
from secrets import username,password
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
    process_posts(bot,20)

    bot.quit()

def interact_based_on_score(bot, score):
        if score >= 70:  # Very high score
            print(f"High score ({score}): Reposting, liking, and saving.")
            bot.retweet()
            bot.like()
            bot.save_post()
        elif score >= 50:  # Medium-high score
            print(f"Medium-high score ({score}): Liking and saving.")
            bot.like()
            bot.save_post()
        elif score >= 30:  # Medium score
            print(f"Medium score ({score}): Liking.")
            bot.like()
        else:
            print(f"Low score ({score}): No action taken.")

def process_posts(bot, num_posts=10):
        for _ in range(num_posts):
            bot.scroll(1)
            post_data = bot.fetch_post()
            if post_data:
                score = bot.calculate_post_score(post_data)
                print(score)
                interact_based_on_score(bot,score)
            bot.random_delay(3, 7)

if __name__ == "__main__":
    main()
