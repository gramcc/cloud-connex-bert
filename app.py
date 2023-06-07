# Description: This is the main file for the Slack app. It handles communication with Slack and the OpenAI API.

# importing standard libraries
import os
import random

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



# Initializes your app with your bot token and socket mode handler
app = App(token=Config.SLACK_BOT_TOKEN)

@app.event("app_mention")
def message_hello(event, say):
    # say() sends a message to the channel where the event was triggered
    llm = OpenAI(temperature=0.0)
    query = event["text"].replace("<@"+Config.SLACK_USER_ID+">","")
    print("\nquery:\n"+query)
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    new_message = Message(text=query, user_id=event["user"])

    classification_prompt_template = """
    Given the following inquiry, which of the following do you think this pertains to: JIRA,Salesforce, or the Employee Handbook? Please only choose one option and return a single answer.
    If none of them is a good match you can also return "no match"

    Inquiry: {inquiry}
    """

    classification_prompt = PromptTemplate(
        template=classification_prompt_template, input_variables=["inquiry"]
    )
    llm_chain = LLMChain(llm=llm, prompt=classification_prompt)
    classification = llm_chain(inputs={"inquiry":query})["text"].strip()
    new_message.classification = classification

    print("\nclassification:\n"+classification)

    if classification == "JIRA" or classification == "Employee Handbook" or classification == "No Match":

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
        if classification == "JIRA":
            docs = docsearch.similarity_search(query,namespace="jira-current-sprint",k=3)
        elif classification == "Employee Handbook":
            docs = docsearch.similarity_search(query,k=2)

        print("\ndocs:\n")
        for doc in docs:
            print(doc)

        response = llm_chain(inputs={"added_context":docs,"UNIQUE_PHRASE":Config.UNIQUE_STRING,"question": query})["text"]
        print("\n\nresponse:\n"+response)
    else:
        print("\nNo Match:\n")
        response = Config.UNIQUE_STRING

    burt_response = response.strip()

    if Config.UNIQUE_STRING in response:
        chatgpt_response = llm(query)
        burt_response = burtify("I don't know the answer to that question. But here is what ChatGPT says:\n\n")+chatgpt_response
    
    say("<@"+event["user"]+"> "+burt_response)

    
    new_message.response = burt_response
    session.add(new_message)
    session.commit()



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
