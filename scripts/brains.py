from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import random
from collections import deque

analyzer = SentimentIntensityAnalyzer()

class InteractionTracker:
    def __init__(self, window_size=100):
        self.interactions = deque(maxlen=window_size)
        self.target_interaction_rate = 0.4  # 40% interaction rate

    def add_interaction(self, interacted):
        self.interactions.append(1 if interacted else 0)

    def get_current_rate(self):
        if not self.interactions:
            return 0
        return sum(self.interactions) / len(self.interactions)

    def should_interact(self):
        current_rate = self.get_current_rate()
        if current_rate < self.target_interaction_rate:
            return random.random() < 0.6  # Increase chance of interaction
        elif current_rate > self.target_interaction_rate:
            return random.random() < 0.2  # Decrease chance of interaction
        return random.random() < 0.4  # Maintain current rate

interaction_tracker = InteractionTracker()

def random_delay(min_seconds=1, max_seconds=5):
            time.sleep(random.uniform(min_seconds, max_seconds))

def get_random_comment():
    comments = [
        "Interesting perspective!",
        "Thanks for sharing this.",
        "I hadn't thought about it that way before.",
        "Great point!",
        "This is really insightful.",
        "I completely agree with you.",
        "You've given me something to think about.",
        "Well said!",
        "I appreciate you sharing this.",
        "This is really important information."
    ]
    return random.choice(comments)

def interact_based_on_score(bot, score):
    actions = {
        'like': bot.like,
        'retweet': bot.retweet,
        'save': bot.save_post,
        'comment': lambda: bot.send_reply(get_random_comment())
    }
    
    def execute_action(action):
        action()
        random_delay(0.5, 1.5)  # Slightly longer delay between actions

    if not interaction_tracker.should_interact():
        print(f"Score: {score}. Skipping interaction based on history.")
        interaction_tracker.add_interaction(False)
        return

    if score < 30:
        print(f"Low score ({score}): No action taken.")
        interaction_tracker.add_interaction(False)
        return

    if score >= 30 and score <55:
        if random.random() < 0.3:  
            print(f"Score: {score}. Performing single action: Like.")
            execute_action(actions['like'])
            interaction_tracker.add_interaction(True)
        else:
            print(f"Score: {score}. No action taken.")
            interaction_tracker.add_interaction(False)
        return

    elif score >= 55 and score < 90:
        print(f"Score: {score}. Performing one or two actions.")
        num_actions = random.choice([1, 2])
        selected_actions = random.sample(list(actions.values()), num_actions)
        for action in selected_actions:
            execute_action(action)
        interaction_tracker.add_interaction(True)
        return
    elif score >= 90:
        # For high scores, perform 2-3 actions
        num_actions = random.randint(3, 4)
        print(f"High score ({score}): Performing {num_actions} actions.")
        selected_actions = random.sample(list(actions.values()), num_actions)
        for action in selected_actions:
            execute_action(action)
        interaction_tracker.add_interaction(True)

def process_posts(bot, num_posts=10):
    for _ in range(num_posts):
        post_data = bot.fetch_post()
        if post_data:
            score = calculate_post_score(post_data)
            print(f"Calculated score: {score}")
            interact_based_on_score(bot, score)

        bot.scroll()
        random_delay(2.5, 4.5)

def calculate_post_score(post_data, inverse=False):
    text = post_data['tweet_text'].lower()
    text_Muli = len(text)/6

    sentiment_score = analyzer.polarity_scores(text)['compound']
    print("{:-<65} {}".format(text, str(sentiment_score)))
    score = 0

    # Adjust score based on sentiment
    
    score += sentiment_score * 120  # Scale the sentiment score
    # Consider engagement metrics

    if inverse:
        score = score * -1

    return score + text_Muli
