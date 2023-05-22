import os

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Other configuration settings...
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")  # find at app.pinecone.io
    PINECONE_API_ENV = os.environ.get("PINECONE_API_ENV")  # next to api key in console
    SLACK_USER_ID = os.environ.get("SLACK_USER_ID") # find from the json response to a slack message
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN") # find at slack bot setup page
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") # find at slack bot setup page
    DATABASE_URL = os.environ.get("DATABASE_URL") # find at heroku postgres setup page
    # add a immutable string that is universal to the rest of the code
    UNIQUE_STRING = "Purple unicorns tacos"

    def print_variables():
        print("PINECONE_API_KEY: "+Config.PINECONE_API_KEY)
        print("PINECONE_API_ENV: "+Config.PINECONE_API_ENV)
        print("SLACK_USER_ID: "+Config.SLACK_USER_ID)
        print("SLACK_BOT_TOKEN: "+Config.SLACK_BOT_TOKEN)
        print("UNIQUE_STRING: "+Config.UNIQUE_STRING)
