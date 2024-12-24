import json

def simple_handle_search_and_save(bot, handle, maxDepth=10, descriptive=False):
    # Go to user page
    bot.navigate(f"https://twitter.com/{handle}")
    
    # Extract user data
    user_profile_data = bot.get_user_profile_data(descriptive=False)
    
    # Extract posts from timeline (maybe limit to first 10 for example)
    user_posts = []
    for i in range(maxDepth):
        post_data = bot.fetch_post()
        if post_data:
            user_posts.append(post_data)
        success = bot.scroll()
        if not success:
            break
    
    # Save to JSON
    result_data = {
        "profile": user_profile_data,
        "posts": user_posts,
    }
    with open(f"{handle}.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"Data for {handle} saved to {handle}.json.")