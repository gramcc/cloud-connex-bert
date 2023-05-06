import os
import random
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain.llms import OpenAI

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


@app.event("app_mention")
def message_hello(event, say):
    # say() sends a message to the channel where the event was triggered
    print(event)
    llm = OpenAI(temperature=0.9)
    response = llm(event['text'])
    print(response)
    # add a list of things to say back to the user
    IDontKnowSyaings = [
        "Hey there",
        "Well, I'll be darned if I know the answer to that one. I'm just here for the mustache and the jokes." ,
        "You know, I'm not quite sure about that one. But when you're as cool as me you don't really need to know the answer to everything.",
        "Well, hot damn, I'm stumped. But you know what they say, ignorance is bliss.",
        "Can't say I have the foggiest, buddy. But that's the beauty of life, isn't it?",
        "Well, I'll be dipped in molasses, I'm at a loss. But that's okay, I always say it's better to keep your mouth shut and let people think you're dumb than to open it and prove 'em right.",
    ]
    HeresChatGPTSayings = [
        "Well, I gotta tell you, partner, this here response was generated by some fancy computer program called ChatGPT. I don't rightly understand how it works, but it sure beats having to use that noggin of mine.",
        "Well, dog my cats, I'm not actually the one coming up with these answers. Some genius computer brain cooked 'em up for me. But don't worry, I'm still the one delivering 'em with that good ol' Burt Reynolds charm.",
        "Now, let me level with you, friend. I'm not actually a human. I'm a highly advanced robot programmed to mimic the one and only Burt Reynolds. And this chatbot thingy is helping me pass for a real person.",
        "Well, I'll be a monkey's uncle. This here response wasn't actually written by me. It's the work of some high-tech AI gizmo. But I reckon I could have come up with something similar if I put my mind to it.",
        "I gotta admit, partner, I'm not the sharpest tool in the shed. That's why I'm relying on this computer contraption to help me out. And let me tell you, it's doing a mighty fine job if I do say so myself.",
        "Now, don't go thinking that just because I'm a big-shot actor, I know everything about everything. I'm just a regular Joe like you, except I got this nifty computer program to make me sound smarter than I am.",
        "Well, knock me over with a feather. This response was actually generated by some fancy AI technology. But don't worry, I'm still the same old Burt Reynolds you know and love. And I still look darn good in a cowboy hat.",
        "I'll be darned, partner, I don't think I could have come up with that answer on my own. But lucky for me, I got this highfalutin' computer thingamabob to do the heavy lifting for me.",
        "Now, don't go getting the wrong idea, partner. I may be a Hollywood legend, but I ain't no expert in every dang thing. That's why I got this fancy computer contraption to help me out.",
        "Well, butter my biscuits, I can't take credit for this response. It's the work of some brilliant computer whiz kid. But I reckon it sounds pretty dang good coming out of my mouth, don't you think?"
    ]

    say(random.choice(HeresChatGPTSayings))
    say(response)
    #say(sayings[randNum])


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
