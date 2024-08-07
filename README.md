## weBot
Trying to make a bot to speed up the process of achieving dead internet. Thats half a joke, but the goal is to make a bot that is able to interact with social media like a human. **Eventually** We will aim to make the bot have a mind of its own for its interactions. For now lets aim to give it arms and legs by making it able to read and interact, even though all interactions may be meaningless for now.

Alot of information is lacking from here. ***I HIGHLY recommend*** viewing the project diagram [Here][project-flow] (in progress)

[project-flow]: https://whimsical.com/twit-HuoT4XtuHXGRRmjCkhyQyz



### To run:
- copy the repository or the contents of it. Easiest to make a new branch and initialize it locally
- Make VENV. This is not necessary, but important to control libraries to avoid conflicts. In your directory, type `python -m venv path/to/venv` I typically store it in venv and use python 3 so for me it would be `python3 -m venv venv`. (you may need to isntall virtualenv with pip before)
    - Start Venv on mac: `source venv/bin/activate` or the correct path to "activate"
    - Start Venv on windows: idek how to do it on windows, it should be pretty easy. Just typing the path to the activate script should work
- Install required dependancies. Requirements.txt will indicate all required dependancies, and they can all be installed at once with `pip install -r requirements.txt` (assuming your in this folder)
- run the web bot, currently we have a main in weBot.py so we can just run that `python3 scripts/weBot.py`

### Current State:
- Just learning selenium and other stuff so we currently have a bot with just username and password and it can navigate to the login screen and enter the fields.
- Secrets.py can store the login info seperate from the code for the bot. Also we will remove the main class from that eventually.
