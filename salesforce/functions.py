import requests

class Salesforce:

    def __init__(self, username, password, login_url, security_token):
        self.client_id = None
        self.client_secret = None
        self.security_token = security_token
        self.username = username
        self.password = password
        self.login_url = login_url
        self.access_token = None
        self.custom_objects = None
        self.custom_fields = None

    def login(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password + self.security_token
        }

        response = requests.post(self.login_url, headers=headers, data=data)
        self.access_token = response.json()["access_token"]
        
        

    def soql_callout(self, prompt):
         headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce system administrator"
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