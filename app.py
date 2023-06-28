# Description: This is the main file for the Slack app. It handles communication with Slack and the OpenAI API.

# importing standard libraries
import os
import random
import requests

# importing third-party libraries for LLMs
import pinecone 
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings

# importing Slack libraries
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# importing config variables 
from config import Config

# import DB models
from models.message import Message
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

#import Salesforce libraries
from salesforce import Salesforce

# import functions
from jira_functions import functions

# Initializes your app with your bot token and socket mode handler
app = App(token=Config.SLACK_BOT_TOKEN)

@app.event("app_mention")
def message_hello(event, say):

    # confirm you received their message
    thread_ts = event["ts"] or event["event_ts"]
    confirmation = random.choice(Config.CONFIRMATIONS)
    #say(text=burtify(confirmation), thread_ts=thread_ts)
    
    # create a new message object
    query = event["text"].replace("<@"+Config.SLACK_USER_ID+">","")
    #engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    #Session = sessionmaker(bind=engine)
    #session = Session()
    #new_message = Message(text=query, user_id=event["user"])

    # Classify the message
    llm = OpenAI(temperature=0.0)
    resp = classify(query)
    classification = "o"
    if "choices" in resp and len(resp["choices"]) > 0 and "text" in resp["choices"][0]:
        classification = resp["choices"][0]["text"].strip()
    #new_message.classification = classification

    print("\nclassification:\n"+classification)

    # Route accordingly
    if classification == "e":

        vector_store_prompt_template = """Use the following pieces of context to answer the question at the end in the voice and style of Burt Reynolds. If you don't know the answer, only say "{UNIQUE_PHRASE}", don't try to make up an answer.
        
        Context: {added_context}

        Question: {question}"""

        vector_store_prompt = PromptTemplate(
            template=vector_store_prompt_template, input_variables=["added_context","UNIQUE_PHRASE", "question"]
        )
        llm_chain = LLMChain(llm=llm, prompt=vector_store_prompt)

        pinecone.init(api_key=Config.PINECONE_API_KEY,environment=Config.PINECONE_API_ENV)
        embeddings = OpenAIEmbeddings()
        docsearch = Pinecone.from_existing_index("cloud-connex-burt", embeddings)
        #try:
        docs = docsearch.similarity_search(query,k=2)

        print("\ndocs:\n")
        for doc in docs:
            print(doc)

        response = llm_chain(inputs={"added_context":docs,"UNIQUE_PHRASE":Config.UNIQUE_STRING,"question": query})["text"]
        print("\n\nresponse:\n"+response)

    elif classification == "j":
        print("\Config.JIRA_TOKEN:\n"+Config.JIRA_USERNAME)
        print("\Config.JIRA_TOKEN:\n"+Config.JIRA_TOKEN)
        f = functions.Functions(Config.JIRA_INSTANCE_URL, Config.JIRA_USERNAME, Config.JIRA_TOKEN, Config.OPENAI_API_KEY)
        response = f.answer_prompt(query)
        print(response)
        response = response["choices"][0]["message"]["content"]
    elif classification == "s":
        response = "I don't currently know how to answer Salesforce questions. But I am working on it."
    elif classification == "g":
        response = "I don't currently know how to answer calendar questions. But I am working on it."
    else:
        print("\nNo Match:\n")
        response = Config.UNIQUE_STRING

    burt_response = response.strip()

    # respond
    if Config.UNIQUE_STRING in response:
        chatgpt_response = llm(query)
        burt_response = burtify("I don't know the answer to that question. But here is what ChatGPT says:\n\n")+chatgpt_response
    
    say(text=burt_response, thread_ts=thread_ts)
    
    #new_message.response = burt_response
    #session.add(new_message)
    #session.commit()

def classify(query):

    url = "https://api.openai.com/v1/completions"
    headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer "+Config.OPENAI_API_KEY
    }
    data = {
    "prompt": query+"\n\n###\n\n",
    "max_tokens": 1,
    "model": Config.CLASSIFICATION_MODEL
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def burtify(response):
    llm = OpenAI(temperature=0.0)
    burt_voice_template = """I'd like the below text rewritten in the voice of Burt Reynolds in the style of his character in the TV show Archer:
    
    Text: {response}
    """

    burt_voice_prompt = PromptTemplate(
        template=burt_voice_template, input_variables=["response"]
    )
    llm_chain = LLMChain(llm=llm, prompt=burt_voice_prompt)
    
    return llm_chain(inputs={"response":response})["text"]

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app,Config.SLACK_APP_TOKEN).start()
