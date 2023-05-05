import os
import random
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# client id: 578735992631.5215848875395

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


@app.event("app_mention")
def message_hello(event, say):
    # say() sends a message to the channel where the event was triggered
    print(event)
    # add a list of things to say back to the user
    sayings = [
        "Hey there",
        "Well, I'll be darned if I know the answer to that one. I'm just here for the mustache and the jokes." ,
        "You know, I'm not quite sure about that one. But when you're as cool as me you don't really need to know the answer to everything.",
        "Well, hot damn, I'm stumped. But you know what they say, ignorance is bliss.",
        "Can't say I have the foggiest, buddy. But that's the beauty of life, isn't it?",
        "Well, I'll be dipped in molasses, I'm at a loss. But that's okay, I always say it's better to keep your mouth shut and let people think you're dumb than to open it and prove 'em right.",
    ]
    randNum = random.randint(0, len(sayings) - 1)
    say(sayings[randNum])


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
