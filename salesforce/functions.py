import requests
import json
from . import SALESFORCE_STANDARD_OBJECTS

class Salesforce:

    def __init__(self, login_url, openai_api_key, **kwargs):
        
        # Set needed variables
        self.login_url = login_url
        self.openai_api_key = openai_api_key
        self.api_version = "56.0"
        
        self.client_id = None
        self.client_secret = None
        self.security_token = None
        self.username = None
        self.password = None
        self.access_token = None
        self.custom_objects = []
        self.custom_fields = []
        self.instance_url = None

        # Process additional keyword arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    def answer_prompt(self, prompt):
        self.login()
        self.get_custom_objects()
        # print("custom objects")
        # print(self.custom_objects)
        resp = self.get_objects_from_prompt(prompt)
        #print("resp from get_objects_from_prompt")
        #print(resp)
        arguments = json.loads(resp["choices"][0]["message"]["function_call"]["arguments"])
        print("arguments from get_objects_from_prompt")
        print(arguments)
        self.get_custom_fields_for_prompt(arguments)
        print("custom fields")
        print(self.custom_fields)
        resp = self.get_soql_callout(prompt)
        return self.review_soql_statement(prompt, json.dumps(resp))


    def login(self):
        
        params = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password + self.security_token
        }

        response = requests.post(self.login_url + "/services/oauth2/token", params=params)                                    

        #print(response.status_code)
        #print(response.text)
        if response.status_code >= 200 and response.status_code < 300:
            self.access_token = response.json()["access_token"]
            self.instance_url = response.json()["instance_url"]
        
        return response

    def get_custom_objects(self):
        soql = "SELECT Id,DeveloperName FROM CustomObject"
        response = self.sfdc_tooling_query(soql)
        #print(response.status_code)
        #print(response.text)
        self.custom_objects.extend([obj for obj in response.json()["records"]])
        return self.custom_objects
    
    def sfdc_tooling_query(self, soql):
        
        # Prepare request headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        # Prepare API endpoint URL
        query_url = f'{self.instance_url}/services/data/v{self.api_version}/tooling/query'

        # Make the SOQL query request
        response = requests.get(query_url, headers=headers, params={'q': soql})
        return response

    def sfdc_soql_query(self, soql):

        # Prepare request headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        # Prepare API endpoint URL
        query_url = f'{self.instance_url}/services/data/v{self.api_version}/query'

        # Make the SOQL query request
        response = requests.get(query_url, headers=headers, params={'q': soql})
        return response

    def get_custom_fields_for_prompt(self, arguments):
        for custom_object_name in arguments["custom_objects"]:
            custom_object_id = self.get_custom_object_id(custom_object_name)
            soql = f"SELECT DeveloperName FROM CustomField WHERE TableEnumOrId='{custom_object_id}'"
            response = self.sfdc_tooling_query(soql)
            #print(response.status_code)
            #print(response.text)
            self.custom_fields.extend([obj["DeveloperName"] for obj in response.json()["records"]])
            return self.custom_fields

    def get_custom_object_id(self, custom_object_name):
        for obj in self.custom_objects:
            if obj["DeveloperName"] == custom_object_name:
                return obj["Id"]
        return None

    def get_custom_fields(self, custom_object):
        soql = f"SELECT DeveloperName FROM CustomField WHERE TableEnumOrId='{custom_object}'"
        response = self.sfdc_tooling_query(soql)
        #print(response.status_code)
        #print(response.text)
        self.custom_fields = [obj["DeveloperName"] for obj in response.json()["records"]]
        return self.custom_fields
    
    def get_objects_from_prompt(self, prompt):
        headers = {
            "Content-Type": "application/json"
        }
        custom_object_names = [obj["DeveloperName"] for obj in self.custom_objects]
        custom_objects_str = "\n".join(custom_object_names)
        content_template = f'Here are all the custom objects in your salesforce instance: \n\n{custom_objects_str}'
        print(content_template)
        data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce system administrator trying to match the custom objects with a user prompt."
                },
                {
                    "role": "system",
                    "content": content_template,
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "functions": [
                {
                    "name": "get_custom_objects",
                    "description": "List the custom object names that are referenced in the user prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "custom_objects": {
                                "type": "array",
                                "description": "An ordered list of the names of custom objects in the salesforce instance that appear in the user prompt",
                                "items": {
                                    "type": "string"
                                },
                            },
                        },
                        "required": ["custom_objects"]
                    }
                }
            ]
        }
        url = "https://api.openai.com/v1/chat/completions"
        response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
        return response.json()

    def get_soql_callout(self, prompt):
         headers = {
            "Content-Type": "application/json"
        }
         custom_object_names = [obj["DeveloperName"] for obj in self.custom_objects]
         custom_objects_str = "\n".join(custom_object_names)
         custom_field_str = "\n".join(self.custom_fields)

         custom_obj_content_template = f'Here are all the custom objects in your salesforce instance: \n\n{custom_objects_str}\n\nHere are all the custom fields in your salesforce instance: \n\n{custom_field_str}'
         
         data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce system administrator"
                },
                {
                    "role": "system",
                    "content":custom_obj_content_template,
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "functions": [
                {
                    "name": "get_soql_results",
                    "description": "Query the salesforce instance to understand data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "soql": {
                                "type": "string",
                                "description": "A SQOL query to pull data from salesforce production instance"
                            },
                            "aggregate": {
                                "type": "boolean",
                                "description": "True if the query is an aggregate query using SUM,COUNT,MIN or MAX functions, false otherwise"
                            },
                            "headers": {
                                "type": "array",
                                "description": "An ordered list of the names for aggregate columns",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {
                                            "type": "string",
                                            "description": "The api name of the field to be aggregated. This should include the function to be used in the aggregate query"
                                        },
                                        "alias": {
                                            "type": "string",
                                            "description": "The alias to be used for the aggregate column in the results"
                                        },
                                        "function": {
                                            "enum": ["SUM", "COUNT", "MIN", "MAX"],
                                            "description": "The function used on this field in the query. This can be null if the field is not an aggregate field"
                                        },
                                    },
                                },
                            },
                        },
                        "required": ["soql", "aggregate"]
                    }
                }
            ]
        }
         url = "https://api.openai.com/v1/chat/completions"
         response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
         return response.json()
    
    def review_soql_statement(self, prompt, soql):
         headers = {
            "Content-Type": "application/json"
        }
         
         data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce technical architect trying to review a function call with a soql statement created from a user prompt. You should review and revise the functions soql as needed to more accurately reflect salesforce data. Please include Salesforce standard objects and best practices in your review."
                },
                {
                    "role": "system",
                    "content": soql,
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "functions": [
                {
                    "name": "get_soql_results",
                    "description": "Query the salesforce instance to understand data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "soql": {
                                "type": "string",
                                "description": "A SQOL query to pull data from salesforce production instance"
                            },
                            "aggregate": {
                                "type": "boolean",
                                "description": "True if the query is an aggregate query using SUM,COUNT,MIN or MAX functions, false otherwise"
                            },
                            "headers": {
                                "type": "array",
                                "description": "An ordered list of the names for aggregate columns",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {
                                            "type": "string",
                                            "description": "The api name of the field to be aggregated. This should include the function to be used in the aggregate query"
                                        },
                                        "alias": {
                                            "type": "string",
                                            "description": "The alias to be used for the aggregate column in the results"
                                        },
                                        "function": {
                                            "enum": ["SUM", "COUNT", "MIN", "MAX"],
                                            "description": "The function used on this field in the query. This can be null if the field is not an aggregate field"
                                        },
                                    },
                                },
                            },
                        },
                        "required": ["soql", "aggregate"]
                    }
                }
            ]
        }
         url = "https://api.openai.com/v1/chat/completions"
         response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
         return response.json()
