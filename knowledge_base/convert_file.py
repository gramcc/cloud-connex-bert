import openai
import pinecone
import json

class Embedding:

    def __init__(self, OPENAI_API_KEY):
        openai.api_key = OPENAI_API_KEY

    # Placeholder function to represent the OpenAI API call
    def get_embeddings_from_openai(text):
        # Assume we have a function 'call_openai_api' to get embeddings from OpenAI
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response['data'][0]['embedding']
    
    
class Vectors:

    def __init__(self,PINECONE_API_KEY,PINECONE_API_ENV) -> None:
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_API_ENV)

    def append_embeddings_to_pinecone(self, list_of_embeddings, Index_Name):
        # Assume that embeddings is a list of objects with the following properties:
        # {
        #     "id": "unique_id",
        #     "embedding": [0.1, 0.2, 0.3, ...],
        #     "metadata": {
        #         "title": "Client Setup Walkthrough - IT",
        #         "url": "https://docs.google.com/document/d/1_kcSQVbuISZ7bT2prj36iKX8rxVSGzWlqc2hNg6DNB4/edit",
        #         "text": "This is the text of the document"
        #     },
        # }
       for itr in list_of_embeddings:
           obj = list_of_embeddings[itr]
           upserts = [(obj["id"],obj["embedding"],obj["metadata"])]
       index = pinecone.Index(Index_Name)
       index.upsert(upserts)
