import re

def extract_engagement_stats(label):
    stats = {}
    pattern = r'(\d+(?:,\d+)*)\s+(\w+)'
    matches = re.findall(pattern, label)
    for value, key in matches:
        stats[key] = int(value.replace(',', ''))
    return stats
