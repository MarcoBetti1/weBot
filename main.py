from weBot.weBot import weBot
from scripts.secrets import username,password,email
from scripts.brains import process_posts
from scripts.search_scripts import simple_handle_search,build_follower_graph,visualize_graph,export_graph_to_csv
from weBot.util import save
import os
def main():
    page_url = "https://twitter.com"  # Example URL
    login_url = "https://twitter.com/login" 
    bot = weBot(username, password, email=email, loginDomain=login_url,homeDomain=page_url)
    bot.setup_driver()

    bot.login()
    test_handle = "MHHwqQzc0sns09N"
    data = build_follower_graph(bot,test_handle,max_layers=3)
    export_graph_to_csv(data, filename="follower_graph3.csv")

    bot.quit()

    # TABLE Users {
    # Handle (Primary Key)
    # Public T/F
    # Follows List
    # }
    # Make sure not to add a User who is Public and Has not been explored. (because a user can have 0 followers)



    # Graph formation
    # Nodes:
    # Handle
    #           Add a node for each handle, (primary key of each row)

    # Edges:
    # Target, Source
    #           And for each handle in the Follows list (which should also corrsepond to a node)
    #           record an edge target to source

if __name__ == "__main__":
    main()
