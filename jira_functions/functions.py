import requests
import json
import base64

# class that allows functions to be called from OpenAI for JIRA
# TODO: add another classificaiton for JIRA requests into aggregate, comparison, details
class Functions:

    def __init__(self, jira_instance_url, jira_username, jira_password, openai_api_key):
        self.openai_api_key = openai_api_key
        self.username = jira_username
        self.password = jira_password
        self.instance_url = jira_instance_url


    def answer_prompt(self, prompt):
        resp =self.jql_callout(prompt)
        arguments = jql = json.loads(resp["choices"][0]["message"]["function_call"]["arguments"])
        print("arguments:")
        print(arguments)
        resp = self.get_jira_issues(arguments["jql"], arguments["fields"])
        return self.get_message_from_jql(prompt,json.dumps(arguments), json.dumps(resp))

    def jql_callout(self, query):

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a atlassian system administrator who know the most used board has this filter: project in (\"Professional Services\", Twilio, \"Blueboard 2\", NexHealth,Density,Phenomex) ORDER BY Rank ASC"
                },
                {
                    "role": "system",
                    "content": """There are custom fields that in JIRA that are described as:
                      [
                        {
                            "id":"customfield_11104",
                            "name": "Changeset",
                            "description": "This is the changeset available for all SFDC Work"
                        },
                         {
                            "id":"customfield_11105",
                            "name": "Pull Request",
                            "description": "Pull request for any changes that have been made"
                        }
                      ]
                    """
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "functions": [
                {
                    "name": "get_jira_issues",
                    "description": "Query the JIRA instance",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "A JQL query to pull data from JIRA cloud instance"
                            },
                            "fields": {
                                "type": "array",
                                "description": "A list of fields to return from the JIRA query",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["jql","fields"]
                    }
                }
            ]
        }

        url = "https://api.openai.com/v1/chat/completions"

        response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
        return response.json()
    

    def get_jira_issues(self, jql, fields):
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "jql": jql,
            "fields": fields
        }

        response = requests.post(f"{self.instance_url}/rest/api/3/search",auth=(self.username,self.password), headers=headers, data=json.dumps(data))
        response_json = response.json()

        # Process the response as needed
        return response_json
    
    def get_message_from_jql(self, query, arguments, content):
        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "user",
                    "content": query
                },
                {
                    "role": "assistant", 
                    "content": None, 
                    "function_call": {
                        "name": "get_jira_issues", 
                        "arguments": arguments
                    }
                },
                {
                    "role": "function", 
                    "name": "get_jira_issues", "content": content
                },
            ],
            "functions": [
                {
                    "name": "get_jira_issues",
                    "description": "Query the JIRA instance",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "A JQL query to pull data from JIRA cloud instance"
                            },
                            "fields": {
                                "type": "array",
                                "description": "A list of fields to return from the JIRA query",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["jql","fields"]
                    }
                }
            ]
        }

        url = "https://api.openai.com/v1/chat/completions"

        response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
        return response.json()
    

    #How much time has been logged to tickets in the sprint?

