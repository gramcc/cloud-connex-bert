# Description: This is the main file for the Slack app. It handles communication with Slack and the OpenAI API.

# Importing standard libraries
import os
import random
import requests
import json

# Importing third-party libraries for vector search
import pinecone
import openai

# Importing Slack libraries
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Importing config variables
from config import Config
openai.api_key = Config.OPENAI_API_KEY

# Import DB models
from models.message import Message
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Initializes your app with your bot token and socket mode handler
app = App(token=Config.SLACK_BOT_TOKEN)

@app.event("message")
def im_created(event, say):
    say(text=handle_message(event["text"]))

@app.event("app_mention")
def message_hello(event, say):

    # Confirm you received their message
    thread_ts = event["ts"] or event["event_ts"]

    # Create a new message object
    query = event["text"].replace("<@"+Config.SLACK_USER_ID+">","")

    # Extract user_id and channel_id from the event
    user_id = event.get("user")
    channel_id = event.get("channel")

    # Print the user_id and channel_id
    print(f"User ID: {user_id}")
    print(f"Channel ID: {channel_id}")

    say(text=handle_message(query), thread_ts=thread_ts)


def handle_message(query):

    # Classify the message
    resp = classify(query)
    classification = "o"
    if "Classification" in resp:
        classification = resp["Classification"]

    print("\nclassification:\n" + classification)

    # Route accordingly
    if classification == "e":
        vector_store_prompt_template = """Use the following pieces of context to answer the question at the end in the voice and style of Burt Reynolds. If you don't know the answer, only say "{UNIQUE_PHRASE}", don't try to make up an answer.
        Context: {added_context}
        Question: {question}"""

        MODEL = "text-embedding-ada-002"
        pinecone.init(api_key=Config.PINECONE_API_KEY, environment=Config.PINECONE_API_ENV)
        index = pinecone.Index("cloud-connex-burt")
        xq = openai.Embedding.create(input=query, engine=MODEL)['data'][0]['embedding']
        docs = index.query([xq], top_k=5, include_metadata=True)['matches'][0]
        print(docs)
        # ...

        # Fill in the details of calling OpenAI API directly
        response = call_openai_api(vector_store_prompt_template, added_context=docs, UNIQUE_PHRASE=Config.UNIQUE_STRING, question=query)
        if "source" in docs['metadata']:
            response = response + "\n\n" + burtify("This is a link to the document I got the answer from:")+"\n"+docs['metadata']['source']
        else:
            response = response + "\n\n" + burtify("This is a link to the document I got the answer from:")+"\n"+docs['metadata']['url']

    elif classification == "j":
        # Import functions
        from jira_functions import functions
        f = functions.Functions(Config.JIRA_INSTANCE_URL, Config.JIRA_USERNAME, Config.JIRA_TOKEN, Config.OPENAI_API_KEY)
        response = f.answer_prompt(query)
        response = response["choices"][0]["message"]["content"]

    elif classification == "s":
        try:
            # Import Salesforce libraries
            from salesforce.functions import Salesforce
            s = Salesforce("https://bopsy.my.salesforce.com", Config.OPENAI_API_KEY, client_id=Config.SALESFORCE_CLIENT_ID, client_secret=Config.SALESFORCE_CLIENT_SECRET, username=Config.SALESFORCE_USERNAME, password=Config.SALESFORCE_PASSWORD, security_token=Config.SALESFORCE_SECURITY_TOKEN)
            print("answer_prompt_start")
            response = s.answer_prompt(query)
            print(response)
            response = response["choices"][0]["message"]["content"]
        
        except Exception as e:
            print(str(e))
            response = burtify("I'm sorry, I'm having trouble with Salesforce right now. Please try again later.")

    elif classification == "g":
        response = burtify("I don't currently know how to answer calendar questions. But I am working on it.")
    else:
        print("\nNo Match:\n")
        response = Config.UNIQUE_STRING

    burt_response = response.strip()

    # respond
    if Config.UNIQUE_STRING in response:
        chatgpt_response = call_openai_api(query)
        burt_response = burtify("I don't know the answer to that question. But here is what ChatGPT says:")+"\n\n"+chatgpt_response

    # Respond
    return burt_response

def classify(query):
    chat_messages = [
        {"role":"system","content":"Bert is a research chat bot that tries to define the types of questions from a user correctly"},
        {"role":"user","content":query}
    ]
    completion = openai.ChatCompletion.create(model=Config.CLASSIFICATION_MODEL,messages=chat_messages)
    return json.loads(completion["choices"][0]["message"]["content"])


def burtify(response):
    burt_voice_template = """I'd like the below text rewritten in the voice of Burt Reynolds:
    
    Text: {}
    """.format(response)
    
    return call_openai_api(burt_voice_template)

def call_openai_api(prompt_template, **kwargs):
    prompt = prompt_template.format(**kwargs)
    print(prompt)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":prompt}],
    ) 
    print(response)
    return response["choices"][0]["message"]["content"].strip()

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, Config.SLACK_APP_TOKEN).start()
