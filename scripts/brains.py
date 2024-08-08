from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import random

analyzer = SentimentIntensityAnalyzer()


def random_delay(min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

def interact_based_on_score(bot, score):
    if score >= 70:  # Very high score
        print(f"High score ({score}): Reposting, liking, and saving.")
        random_delay(0.1,0.4)
        bot.retweet()
        random_delay(0.1,0.4)
        bot.like()
        random_delay(0.1,0.4)
        bot.save_post()
    elif score >= 50:  # Medium-high score
        print(f"Medium-high score ({score}): Liking and saving.")
        bot.like()
        random_delay(0.1,0.4)
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
            score = calculate_post_score(post_data)
            print(score)
            interact_based_on_score(bot, score)

        random_delay(3, 7)
        time.sleep(7)

def calculate_post_score(post_data):
    text = post_data['tweet_text'].lower()
    sentiment_score = analyzer.polarity_scores(text)['compound']

    score = 0

    # Adjust score based on sentiment
    score += sentiment_score * 50  # Scale the sentiment score

    # Consider engagement metrics
    score += min(post_data['likes'] // 1000, 20)  # Max 20 points for likes
    score += min(post_data['reposts'] // 500, 15)  # Max 15 points for retweets
    score += min(post_data['replies'] // 100, 10)  # Max 10 points for replies

    # Bonus for very high engagement
    if post_data['likes'] > 50000 or post_data['reposts'] > 10000:
        score += 20

    return score
