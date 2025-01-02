def simple_handle_search(bot, handle, maxDepth=10, descriptive=False):
    
    # Extract user data
    user_profile_data = bot.get_user_profile_data(handle,descriptive)
    
    bot.navigate(f"https://twitter.com/{handle}")
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
    return result_data

import collections

def build_follower_graph(bot, start_handle, max_layers=3, max_per_user=40):
    """
    Build a graph (adjacency dict) of followers up to `max_layers` away
    from `start_handle`.
    
    :param bot: an instance of your weBot (with the method get_user_list_from_modal or similar)
    :param start_handle: the initial user handle from which to begin scraping
    :param max_layers: maximum BFS depth (e.g., 3)
    :param max_per_user: optional limit for how many followers to retrieve per user
    :return: a dictionary representing follower edges, e.g. {follower_handle: {user_handle, ...}, ...}
    """
    # We'll store edges as follower -> user
    graph = {}
    
    # Visited set to avoid re-fetching the same user multiple times
    visited = set()
    
    # Queue for BFS: each entry is (handle, depth)
    queue = collections.deque()
    queue.append((start_handle, 0))
    
    while queue:
        current_handle, depth = queue.popleft()
        
        # If we've already processed this user, skip
        if current_handle in visited:
            continue
        
        if depth < max_layers:

            # Mark as visited
            visited.add(current_handle)

            # Go to the user's page
            bot.navigate(f"https://twitter.com/{current_handle}/followers")

            # Add error check to move on and save for later, if no more then wait

            # Get this user's followers
            # (Your code might be get_user_list_from_modal("followers") or a simpler approach.)
            try:
                followers_list, fullyexplored = bot.get_user_list_from_modal(
                    list_type="followers", 
                    max_count=max_per_user
                )

            except Exception as e:
                print(f"Error retrieving followers for {current_handle}: {e}")
                followers_list = []
            
            # Store edges: for each follower f in followers_list, f -> current_handle
            for f in followers_list:
                # Add f to the graph if not present
                if f not in graph:
                    graph[f] = set()
                graph[f].add(current_handle)
                
            # Enqueue all the newly found followers if they are not visited
            for f in followers_list:
                if f not in visited:
                    queue.append((f, depth + 1))
                    
            bot.random_delay(3.5,10)
    
    return graph

import networkx as nx
import matplotlib.pyplot as plt

def visualize_graph(graph):
    G = nx.DiGraph()  # Directed graph
    
    # Add edges
    for follower, followed_users in graph.items():
        for user in followed_users:
            G.add_edge(follower, user)
    
    plt.figure(figsize=(12, 12))
    
    # A simple layout, e.g., spring layout
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Draw the nodes and edges
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color="lightblue")
    nx.draw_networkx_edges(G, pos, arrowstyle="->", arrowsize=10, edge_color="gray")
    nx.draw_networkx_labels(G, pos, font_size=8)
    
    plt.title("Follower Graph")
    plt.axis("off")
    plt.show()

import csv
def export_graph_to_csv(graph, filename="follower_graph.csv"):
    """
    Given an adjacency dict {follower: {usersTheyFollow, ...}}, 
    write edges to CSV: follower, userTheyFollow
    """
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])  # typical column names for Gephi
        for follower, followed_users in graph.items():
            for user in followed_users:
                writer.writerow([follower, user])

    print(f"Graph exported to {filename}")
