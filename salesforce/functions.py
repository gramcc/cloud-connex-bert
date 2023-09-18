import requests
import json
from . import SALESFORCE_STANDARD_OBJECTS
from datetime import datetime

class Salesforce:

    def __init__(self, login_url, openai_api_key, **kwargs):
        
        # Set needed variables
        self.login_url = login_url
        self.openai_api_key = openai_api_key
        self.api_version = "56.0"
        
        self.client_id = None
        self.client_secret = None
        self.security_token = ""
        self.username = None
        self.password = None
        self.access_token = None
        self.custom_objects = []
        self.custom_fields = {}
        self.instance_url = None

        # Process additional keyword arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    def answer_prompt(self, prompt):
        
        # login
        self.login()
        
        # retrieve relevant objects and fields
        self.get_custom_objects()
        print("get custom objects")
        resp = self.get_objects_from_prompt(prompt)
        arguments = json.loads(resp["choices"][0]["message"]["function_call"]["arguments"])
        print("arguments from get_objects_from_prompt")
        print(arguments)
        self.get_custom_fields_for_prompt(arguments)
        resp = self.get_soql_callout(prompt)
        print("get soql callout")
        print(resp)
        arguments = json.loads(resp["choices"][0]["message"]["function_call"]["arguments"])
        print("arguments from get_soql_callout")
        print(arguments)
        
        # get soql results
        print("query salesforce")
        soql_results = self.sfdc_soql_query(arguments["soql"])
        print("soql_results")
        print(soql_results.text)
        if soql_results.status_code > 300:
             print("soql failed: retry with reviewed soql")
             resp = self.review_soql_statement(soql_results.text, arguments["soql"])
             if "function_call" in resp["choices"][0]["message"]:
                arguments = json.loads(resp["choices"][0]["message"]["function_call"]["arguments"])
                print("arguments from review_soql_statement")
                print(arguments)
                soql_results = self.sfdc_soql_query(arguments["soql"])
        
        answer = self.get_answer_question(prompt, json.dumps(soql_results.json()))
        return answer
        


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
        for obj in self.custom_objects:
            obj["ApiName"] = obj["DeveloperName"] + "__c"
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
            print("getting fields for: "+custom_object_name)
            custom_object_id = self.get_custom_object_id(custom_object_name)
            self.custom_fields[custom_object_name] = self.get_custom_fields(custom_object_id)

    def get_custom_object_id(self, custom_object_name):
        for obj in self.custom_objects:
            if obj["ApiName"] == custom_object_name:
                return obj["Id"]
        return None

    def get_custom_fields(self, custom_object):
        soql = f"SELECT Id,DeveloperName FROM CustomField WHERE TableEnumOrId='{custom_object}'"
        response = self.sfdc_tooling_query(soql)
        fields = response.json()["records"]
        #print(fields)
        for field in fields:
            field["ApiName"] = field["DeveloperName"] + "__c"
            response = self.sfdc_tooling_query(f"SELECT Id,DeveloperName,Metadata FROM CustomField WHERE Id='{field['Id']}'")
            if response.status_code < 300:
                #print("metadata")
                #print(response.json())
                Metadata = response.json()["records"][0]["Metadata"]
                field["type"] = Metadata["type"]
                if field["type"] == "Lookup":
                    field["referenceTo"] = Metadata["referenceTo"]
        #print(response.status_code)
        #print(response.text)
        return fields
    
    def print_custom_fields(self):
        returnStr = ""
        for key in self.custom_fields.keys():
            returnStr = returnStr + f"\nSalesforce Object - {key}\nFields - \n"
            for field in self.custom_fields[key]:
                returnStr = returnStr + field["ApiName"] + ":" + field["type"]
                if field["type"] == "Lookup":
                    returnStr = returnStr + "(" + field["referenceTo"] + ")"
                returnStr = returnStr + "\n"
        returnStr = returnStr + "\n\n"
        return returnStr
    
    def get_objects_from_prompt(self, prompt):
        headers = {
            "Content-Type": "application/json"
        }
        custom_object_names = [ obj["ApiName"] for obj in self.custom_objects]
        custom_object_names.extend(SALESFORCE_STANDARD_OBJECTS)
        custom_objects_str = "\n".join(custom_object_names)
        print(custom_objects_str)
        content_template = f'Here are all the custom objects in your salesforce instance: \n\n{custom_objects_str}'

        #print("content_template: "+content_template)
        data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce technical architect trying to determine which objects are relevant given the user question."
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
                                "description": "An ordered list of the names of objects in the salesforce instance that appear in the user prompt",
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
         custom_objects_str = self.print_custom_fields()
         custom_obj_content_template = f'Here are all the objects and their corresponding custom fields in the salesforce org that you would use to query. Do not use any objects or custom fields not used here: \n\n{custom_objects_str}'
         #print("custom_obj_content_template: "+custom_obj_content_template)
         current_datetime = datetime.now().strftime("%m/%d/%Y")

         data = {
           "model": "gpt-4-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce developer."
                },
                {
                    "role": "system",
                    "content": "Today's date is: "+current_datetime+"."
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
                    "description": "SOQL query that answers the user question",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "soql": {
                                "type": "string",
                                "description": "A SQOL query to pull data from salesforce rest api. It should only use fields that are provided in the prompt."
                            },
                            "fields": {
                                "type": "array",
                                "description": "An ordered list of the fields that used in the query that exist from the custom objects in the prompt",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "ApiName": {
                                            "type": "string",
                                            "description": "The api name of the field"
                                        },
                                        "type": {
                                            "type": "string",
                                            "description": "The type of the field"
                                        },
                                    },
                                },
                            },
                        },
                        "required": ["soql","fields"]
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
            "model": "gpt-4-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "Review and fix the soql statement for salesforc rest api. Review the following:\nDate"
                },
                {
                    "role": "system",
                    "content": "SOQL: "+soql,
                },
                {
                    "role": "user",
                    "content": "error:\n"+prompt
                },
            ],
            "functions": [
                {
                    "name": "review_soql_statement",
                    "description": "An updated soql query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "soql": {
                                "type": "string",
                                "description": "A SQOL query as a result of fixing errors."
                            },
                        },
                        "required": ["soql"]
                    }
                }
            ]
        }
        url = "https://api.openai.com/v1/chat/completions"
        response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
        return response.json()

    def get_aggregate_colums(self, prompt, soql):
         headers = {
            "Content-Type": "application/json"
        }
         
         data = {
            "model": "gpt-3.5-turbo-0613",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce architect trying to understand good columns names if the soql statement is aggregate."
                },
                {
                    "role": "system",
                    "content": "SOQL statement: "+soql,
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "functions": [
                {
                    "name": "get_aggregate_columns",
                    "description": "Understand the possible aggregate columns in the soql statement",
                    "parameters": {
                        "type": "object",
                        "properties": {
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
                        "required": ["aggregate"]
                    }
                }
            ]
        }
         url = "https://api.openai.com/v1/chat/completions"
         response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
         return response.json()
    

    def get_answer_question(self, prompt, salesforce_data):
         headers = {
            "Content-Type": "application/json"
        }
         
         print("Salesforce data: ")
         print(salesforce_data)
         data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a salesforce developer trying to answer a question about your salesforce instance from the json. If you see an error or can't solve the question, please say 'I don't know'"
                },
                {
                    "role": "system",
                    "content": "json: "+salesforce_data,
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        }
         url = "https://api.openai.com/v1/chat/completions"
         response = requests.post(url, auth=("", self.openai_api_key), headers=headers, data=json.dumps(data))
         return response.json()

