import os
import pinecone
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
from jira import JIRA

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")  # find at app.pinecone.io
PINECONE_API_ENV = os.environ.get("PINECONE_API_ENV")  # next to api key in console
JIRA_USERNAME = os.environ.get("JIRA_USERNAME")  # next to api key in console
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")  # next to api key in console

# Connect to JIRA cloud instance
jira = JIRA('https://bopsy1.atlassian.net', basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))

# Define a template string for the JIRA tickets
JIRA_TEMPLATE = """
Ticket: {ticket}

Reporter: {reporter}

Assignee: {assignee}

Status: {status}

Summary: {summary}

Description:
{description}

Current Sprint: {current_sprint}

Pull Request: {pull_request}

Changeset: {changeset}
"""

# Get all issues in the current sprint
sprint_issues = jira.search_issues('Sprint in openSprints()')

# Load the pre-trained OpenAI embeddings model
embeddings = OpenAIEmbeddings()

# Initialize a Pinecone client with your API key
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_API_ENV)

# Get the current index
index_name = "cloud-connex-burt"
pinecone_index = Pinecone.from_existing_index(index_name, embeddings, namespace="jira-current-sprint")

texts = []

# Loop through each issue in the sprint
for issue in sprint_issues:

    # Format the template string with the relevant information
    text = JIRA_TEMPLATE.format(
        ticket=issue.key,
        reporter=issue.fields.reporter.displayName if issue.fields.reporter and issue.fields.reporter.displayName else "",
        assignee=issue.fields.assignee.displayName if issue.fields.assignee and issue.fields.assignee.displayName else "",
        status=issue.fields.status.name if issue.fields.status and issue.fields.status.name else "",
        summary=issue.fields.summary if issue.fields.summary else "",
        description=issue.fields.description if issue.fields.description else "",
        current_sprint = issue.fields.customfield_11126 if issue.fields.customfield_11126 else "",
        pull_request = issue.fields.customfield_11105 if issue.fields.customfield_11105 else "",
        changeset = issue.fields.customfield_11104 if issue.fields.customfield_11104 else ""
    )
    print(text)
    texts.append(text)

# Add the text to the Pinecone index
Pinecone.from_texts(texts, embeddings, index_name=index_name, namespace="jira-current-sprint")

