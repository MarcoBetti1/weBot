from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import random

analyzer = SentimentIntensityAnalyzer()


def random_delay(min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

def interact_based_on_score(bot, score):
    actions = [
        (bot.retweet),
        (bot.like),
        (bot.save_post)
        ]
    if score >= 80:  # Very high score
        print(f"High score ({score}): Reposting, liking, and saving.")
        random.shuffle(actions)
        for action in actions:
            action()
            random_delay(0.2,0.5)
        

    elif score >= 50:
        print(f"med_high score ({score})")
        # Select a random 1 or 2 actions from the list
        num_actions = random.choice([1, 2])
        selected_actions = random.sample(actions, num_actions)
        for action in selected_actions:
            action()
            random_delay(0.2,0.5)

    elif score >= 32:  # Medium score
        print(f"Medium score ({score}): Liking.")

        bot.like()
    else:
        print(f"Low score ({score}): No action taken.")

def process_posts(bot, num_posts=10):
    for _ in range(num_posts):
        post_data = bot.fetch_post()
        print(post_data)
        if post_data:
            score = calculate_post_score(post_data)
            print(score)
            interact_based_on_score(bot, score)

        bot.scroll()
        random_delay(2.5, 4.5)

def calculate_post_score(post_data):
    text = post_data['tweet_text'].lower()
    text_Muli = len(text)/4

    sentiment_score = analyzer.polarity_scores(text)['compound']
    print("{:-<65} {}".format(text, str(sentiment_score)))
    score = 0

    # Adjust score based on sentiment
    score += sentiment_score * 40  # Scale the sentiment score
    # Consider engagement metrics
    if 'likes' in post_data:
        score += min(post_data['likes'] // 1000, 4)  # Max 5
    if 'reposts' in post_data:
        score += min(post_data['reposts'] // 500, 4) 
    if 'replies' in post_data: 
        score += min(post_data['replies'] // 100, 4)  



    return score + text_Muli
