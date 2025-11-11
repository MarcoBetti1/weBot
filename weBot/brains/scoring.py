"""Content scoring helpers powered by Vader sentiment."""
from __future__ import annotations

from typing import Dict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def calculate_post_score(post: Dict[str, str], inverse: bool = False) -> float:
    text = (post.get("tweet_text") or "").lower()
    sentiment_score = _analyzer.polarity_scores(text)["compound"]
    text_multiplier = len(text) / 6
    score = sentiment_score * 120 + text_multiplier
    if inverse:
        score *= -1
    return score
