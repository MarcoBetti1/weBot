from weBot.weBot import weBot
from scripts.secrets import username,password,email
from scripts.brains import process_posts
import os
def main():
    page_url = "https://twitter.com"  # Example URL
    login_url = "https://twitter.com/login" 
    # positive_keywords = ['great', 'awesome', 'excellent', 'amazing', 'good', 'nice', 'love', 'best']
    # negative_keywords = ['bad', 'worst', 'terrible', 'awful', 'hate', 'dislike', 'poor']

    bot = weBot(username, password, email=email, loginDomain=login_url,homeDomain=page_url)
    bot.setup_driver()


    bot.login()

    # Actions
    print(bot.fetch_post())
    #process_posts(bot,10)
    bot.type_search_click(query="hello!",numresult=3,search_type="People")
    bot.type_search_click(query="no",numresult=3,search_type="Latest") # only works for people and latest
    bot.scroll()
    bot.repost("Hi")
    bot.scroll()
    bot.repost()
    # #bot.navigate_to_profile("InternetH0F")
    # bot.follow()
    # # bot.like()
    # # bot.retweet()
    # # bot.save_post()
    # bot.scroll()
    # bot.like()
    # bot.retweet()
    # bot.save_post()
    # bot.follow()
    # post = bot.fetch_post()
    # print(post)

    
    # #bot.click()
    # bot.random_delay(3,4)
    # bot.follow()
    # bot.go_back()
    # # Quit
    # bot.quit()



if __name__ == "__main__":
    main()
