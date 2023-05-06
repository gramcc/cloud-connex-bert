import os
import random
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone 

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")  # find at app.pinecone.io
PINECONE_API_ENV = os.environ.get("PINECONE_API_ENV")  # next to api key in console
SLACK_USER_ID = os.environ.get("SLACK_USER_ID") # find at slack bot setup page


# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# add a immutable string that is universal to the rest of the code
UNIQUE_STRING = "Purple unicorns tacos"

@app.event("app_mention")
def message_hello(event, say):
    # say() sends a message to the channel where the event was triggered
    print(event)
    llm = OpenAI(temperature=0.0)
    query = event["text"].replace("<@"+SLACK_USER_ID+">","")
    prompt_template = """Use the following pieces of context to answer the question at the end in the voice and style of Burt Reynolds. If you don't know the answer, only say "{UNIQUE_PHRASE}", don't try to make up an answer.
    
    Context: {added_context}

    Question: {question}"""

    #CONTEXT = "Holidays\nFeb 20                President's Day\nApr 10                Spring Holiday\nMay 29        Memorial Day\nJun 19                Juneteenth\nJuly 4                Independence Day\nSep 4                Labor Day\nNov 23        Thanksgiving\nNov 24        Day after Thanksgiving\nDec 21                Holiday Break\nDec 22        Holiday Break\nDec 25        Holiday Break\nDec 26        Holiday Break\nDec 27        Holiday Break\nDec 28        Holiday Break\nDec 29        Holiday Break\nJan 1                New Years Day 2024\n\n\n\n\nUnpaid leaves of absence\nCloud Connex does not allow unpaid leaves of absence. We do encourage all employees to find the best direction for themselves and encourage everyone to follow the path best suited to their health and happiness. However, we strive to provide the best for our customers and therefore believe that any position should be fully dedicated to that goal.\n\n\nCode of Conduct\nIntroduction"

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["added_context","UNIQUE_PHRASE", "question"]
    )
    llm_chain = LLMChain(llm=llm, prompt=PROMPT)
    #chain = load_qa_chain(OpenAI(temperature=0), chain_type="stuff", prompt=PROMPT)
    #chain({"input_documents": docs, "question": query}, return_only_outputs=True)


    pinecone.init(api_key=PINECONE_API_KEY,environment=PINECONE_API_ENV)
    embeddings = OpenAIEmbeddings()
    docsearch = Pinecone.from_existing_index("cloud-connex-burt", embeddings)
    #try:
    docs = docsearch.similarity_search(query)
    #except:
    #    docs = [""]
    
    response = llm_chain(inputs={"added_context":docs[0],"UNIQUE_PHRASE":UNIQUE_STRING,"question": query})["text"]
    print("\n\nresponse:\n"+response)
    # add a list of things to say back to the user
    IDontKnowSyaings = [
        "Well, I'll be darned if I know the answer to that one. I'm just here for the mustache and the jokes." ,
        "You know, I'm not quite sure about that one. But when you're as cool as me you don't really need to know the answer to everything.",
        "Well, hot damn, I'm stumped. But you know what they say, ignorance is bliss.",
        "Can't say I have the foggiest, buddy. But that's the beauty of life, isn't it?",
        "Well, I'll be dipped in molasses, I'm at a loss. But that's okay, I always say it's better to keep your mouth shut and let people think you're dumb than to open it and prove 'em right.",
    ]
    HeresChatGPTSayings = [
        "Well, I gotta tell you, <@"+event["user"]+">"+", this here response was generated by some fancy computer program called ChatGPT. I don't rightly understand how it works, but it sure beats having to use that noggin of mine.",
        "Well, dog my cats, I'm not actually the one coming up with these answers. Some genius computer brain cooked 'em up for me. But don't worry, I'm still the one delivering 'em with that good ol' Burt charm.",
        "Now, let me level with you, <@"+event["user"]+">"+". I'm not actually all knowing ... even if I seem like it sometimes. And this chatbot thingy is helping me pass for a know it all.",
        "Well, I'll be a monkey's uncle. This here response wasn't actually written by me. It's the work of some high-tech AI gizmo. But I reckon I could have come up with something similar if I put my mind to it.",
        "I gotta admit, <@"+event["user"]+">"+", I'm not the sharpest tool in the shed. That's why I'm relying on this computer contraption to help me out. And let me tell you, it's doing a mighty fine job if I do say so myself.",
        "Now, don't go thinking that just because I'm a big-shot actor, I know everything about everything. I'm just a regular Joe like you, except I got this nifty computer program to make me sound smarter than I am.",
        "Well, knock me over with a feather. This response was actually generated by some fancy AI technology. But don't worry, I'm still the same old Burt you know and love. And I still look darn good in a cowboy hat.",
        "I'll be darned, <@"+event["user"]+">"+", I don't think I could have come up with that answer on my own. But lucky for me, I got this highfalutin' computer thingamabob to do the heavy lifting for me.",
        "Now, don't go getting the wrong idea, partner. I may be a Hollywood legend, but I ain't no expert in every dang thing. That's why I got this fancy computer contraption to help me out.",
        "Well, butter my biscuits, I can't take credit for this response. It's the work of some brilliant computer whiz kid. But I reckon it sounds pretty dang good coming out of my mouth, don't you think?"
    ]

    if UNIQUE_STRING in response:
        response = random.choice(HeresChatGPTSayings)
        if SLACK_USER_ID in response:
            say(response)
        else:
             say("<@"+event["user"]+"> "+response)
        say(llm(query))
    else:
        say("<@"+event["user"]+"> "+response)


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
