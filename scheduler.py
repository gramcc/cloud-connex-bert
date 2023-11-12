# scheduled_messages.py
import os


from salesforce.functions import Salesforce
from jira_functions.functions import Functions as jql
from config import Config


# Importing Slack libraries
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
# Initializes your app with your bot token and socket mode handler
app = App(token=Config.SLACK_BOT_TOKEN)

class ScheduledMessages:

    def __init__(self):
        self.s = Salesforce("https://bopsy.my.salesforce.com", Config.OPENAI_API_KEY, client_id=Config.SALESFORCE_CLIENT_ID, client_secret=Config.SALESFORCE_CLIENT_SECRET, username=Config.SALESFORCE_USERNAME, password=Config.SALESFORCE_PASSWORD, security_token=Config.SALESFORCE_SECURITY_TOKEN)
        self.j = jql(Config.JIRA_INSTANCE_URL, Config.JIRA_USERNAME, Config.JIRA_TOKEN, Config.OPENAI_API_KEY)
        self.report = {}
    
    
    def compileStaffingReport(self):
        report = {}
        emailToContactId = {}
        labelToAccountId = {}

        # retrieve account team member assignments from Salesforce
        login_resp = self.s.login()
        accountteammebers_soql = 'Select id,Account__r.Slack_Channel_Id__c,Account__r.JIRA_Label__c ,Account__r.Name,Account__c,Contact__r.Email,Contact__r.Name,Contact__c,Role__c, Assignment_Date__c, Weekly_Hours_Assigned__c, Monthly_Hours_Assigned__c From Account_Team_Contact_Member__c Where Active__c = true'
        response = self.s.sfdc_soql_query(accountteammebers_soql)
        print("salesforce response")
        print(response)
        if response.status_code >= 200 and response.status_code < 300:
            accountteammembers = records = response.json()["records"]
            print("accountteammembers")
            print(accountteammembers[0])
        else:
            return

        # enter assignments into report
        for accountteammember in accountteammembers:

            # input data into report
            if accountteammember["Account__c"] not in report:
                report[accountteammember["Account__c"]] =   {
                                                                "Id":accountteammember["Account__c"],
                                                                "Name":accountteammember["Account__r"]["Name"],
                                                                "channelId":accountteammember["Account__r"]["Slack_Channel_Id__c"],
                                                                "label":accountteammember["Account__r"]["JIRA_Label__c"],
                                                                "TotalHours":0.0,
                                                                "TimeRemainingInSprint":0.0,
                                                                "TotalLoggedHours":0.0,
                                                                "Employees":{},
                }


            if accountteammember["Contact__c"] not in report[accountteammember["Account__c"]]["Employees"]:
                report[accountteammember["Account__c"]]["Employees"][accountteammember["Contact__c"]] = {
                    "ContactId":accountteammember["Contact__c"],
                    "Name":accountteammember["Contact__r"]["Name"],
                    "Email":accountteammember["Contact__r"]["Email"],
                    "TotalHours":0.0,
                    "RemainingHours":0.0,
                    "LoggedHours":0.0,
                }
            
            #print(accountteammember["Weekly_Hours_Assigned__c"])
            #print(report[accountteammember["Account__c"]]["Employees"][accountteammember["Contact__c"]]["TotalHours"])
            report[accountteammember["Account__c"]]["Employees"][accountteammember["Contact__c"]]["TotalHours"] = report[accountteammember["Account__c"]]["Employees"][accountteammember["Contact__c"]]["TotalHours"] + accountteammember["Weekly_Hours_Assigned__c"]
            report[accountteammember["Account__c"]]["TotalHours"] = report[accountteammember["Account__c"]]["TotalHours"] + accountteammember["Weekly_Hours_Assigned__c"]
    
            # input data into maps
            if accountteammember["Account__r"]["JIRA_Label__c"] not in labelToAccountId:
                labelToAccountId[accountteammember["Account__r"]["JIRA_Label__c"]] = accountteammember["Account__c"]

            if accountteammember["Contact__r"]["Email"] not in emailToContactId:
                emailToContactId[accountteammember["Contact__r"]["Email"]] = accountteammember["Contact__c"]

        # retrieve JIRA issues in the current sprint
        jira_query = "sprint in openSprints()"
        response = self.j.get_jira_issues(jira_query,["summary","assignee","timeestimate","timespent","labels"])
        tickets = response["issues"]
        print(tickets[0])

        # retrieve jira users
        uql = "is assignee of PS"
        response = self.j.get_jira_users(uql)
        jira_users = response["values"]
        print(jira_users[0])
        
        # enter tickets into report
        for ticket in tickets:
        
            # skip tickets without remaining time
            if "timeestimate" not in ticket["fields"]:
                continue

            timeestimate = ticket["fields"]["timeestimate"] or 0.0
            timespent = ticket["fields"]["timespent"] or 0.0
            timeRemaining = timeestimate - timespent
            print(timeRemaining)
            
            labels = ticket["fields"]["labels"]
            for label in labels:
                if label in labelToAccountId and timeRemaining > 0:

                    # add time to customer
                    accountId = labelToAccountId[label]
                    report[accountId]["TimeRemainingInSprint"] = report[accountId]["TimeRemainingInSprint"] + timeRemaining/3600
                    
                    # get email for assignee
                    if "assignee" not in ticket["fields"] or ticket["fields"]["assignee"] is None:
                        continue 
                    
                    assignee_email = ScheduledMessages.getEmaiByAssignee(ticket["fields"]["assignee"]["accountId"],jira_users)

                    # check email was there
                    if assignee_email is None or assignee_email not in emailToContactId:
                        continue
                    
                    contactId = emailToContactId[assignee_email]
                    if contactId in report[accountId]["Employees"]:
                        report[accountId]["Employees"][contactId]["RemainingHours"] = report[accountId]["Employees"][contactId]["RemainingHours"] + timeRemaining/3600

        # retrieve logged hours by Employee
        logged_hours_soql = "Select id,Customer__c,Customer__r.Name,Customer__r.Slack_Channel_id__c,Customer__r.JIRA_Label__c,Employee__c,Employee__r.Name,Employee__r.Email,Duration_in_hours__c From Logged_Hours__c Where Date__c = THIS_WEEK ORDER BY Employee__c"
        response = self.s.sfdc_soql_query(logged_hours_soql)
        print("salesforce response")
        print(response)
        if response.status_code >= 200 and response.status_code < 300:
            loggedhours = records = response.json()["records"]
            print("loggedhours")
            print(loggedhours[0])
        else:
            return

        # add Logged Hours to report
        for hour in loggedhours:
            
            # Adjust report to include logged hours for unassigned customers to ensure exception handling
            if hour["Customer__c"] not in report:
                report[hour["Customer__c"]] = {
                                                                "Id":hour["Customer__c"],
                                                                "Name":hour["Customer__r"]["Name"],
                                                                "channelId":hour["Customer__r"]["Slack_Channel_Id__c"],
                                                                "label":hour["Customer__r"]["JIRA_Label__c"],
                                                                "TotalHours":0.0,
                                                                "TimeRemainingInSprint":0.0,
                                                                "TotalLoggedHours":0.0,
                                                                "Employees":{},
                                                                "LoggedHourExceptions":{},
                }
            
            report[hour["Customer__c"]]["TotalLoggedHours"] =  report[hour["Customer__c"]]["TotalLoggedHours"] + hour["Duration_in_hours__c"]
            if hour["Employee__c"] not in report[hour["Customer__c"]]["Employees"]:
                if "LoggedHourExceptions" not in report[hour["Customer__c"]]:
                    report[hour["Customer__c"]]["LoggedHourExceptions"] = {}
                
                if "Employee__c" not in report[hour["Customer__c"]]["LoggedHourExceptions"]:
                    report[hour["Customer__c"]]["LoggedHourExceptions"]["Employee__c"] = {
                        "Name":hour["Employee__r"]["Name"],
                        "Email":hour["Employee__r"]["Email"],
                        "LoggedHours":0.0,
                    }
                
                report[hour["Customer__c"]]["LoggedHourExceptions"]["Employee__c"]["LoggedHours"] = report[hour["Customer__c"]]["LoggedHourExceptions"]["Employee__c"]["LoggedHours"] + hour["Duration_in_hours__c"]
            else:
                report[hour["Customer__c"]]["Employees"][hour["Employee__c"]]["LoggedHours"] = report[hour["Customer__c"]]["Employees"][hour["Employee__c"]]["LoggedHours"] + hour["Duration_in_hours__c"]

        #print(report)
        self.report = report
        
    @staticmethod
    def getEmaiByAssignee(assigneeId, users):
        for user in users:
            if assigneeId == user["accountId"]:
                return user["emailAddress"]

        return None

   
    def sendStaffingReport(self):
        self.compileStaffingReport()
        reportsByClient = {}
        for key in self.report:
            reportsByClient[key] = self.createReportTable({key:self.report[key]})
            print(reportsByClient[key])
            #channel_id = os.environ.get("SLACK_DEMO_AI_CHANNEL_ID") # Get channel for demo_ai testing
            ScheduledMessages.send_mention_in_channel(self.report[key]["channelId"],"",markdown={"blocks":reportsByClient[key]})
    

    def createReportTable(self, accountMap):
        columns=["Customer", "Employee", "Assigned", "Logged", "In Sprint","Delta"]
        rows = []


        print("accountMap")
        print(accountMap)

        for accountid in accountMap:
            
            print(accountMap[accountid])
            print(accountMap[accountid]["Employees"])

            for contactid in accountMap[accountid]["Employees"]:
                row = []
                row.append(accountMap[accountid]["Name"])
                employee = accountMap[accountid]["Employees"][contactid]
                row.append(employee["Name"])
                row.append(str(round(employee["TotalHours"],2)))
                row.append(str(round(employee["LoggedHours"],2)))
                row.append(str(round(employee["RemainingHours"],2)))
                delta = employee["TotalHours"] - employee["LoggedHours"] - employee["RemainingHours"]
                row.append(str(round(delta,2)))
                rows.append(row)

        return ScheduledMessages.convertTableToSlackBlocks(rows, columns)

    def alertAccountCloseToHours():

        #print(s.login_url)
        soql = "Select id,Name,Slack_Channel_id__c,Hours_Agreed_for_the_Month__c,Hours_Pacing__c,JIRA_Label__c,(Select id,Duration_in_hours__c,Employee__r.Name From Logged_Hours__r Where Date__c = THIS_MONTH) From Account Where RecordType.Name = 'Customer'"
        
        print(login_resp)
        response = s.sfdc_soql_query(soql)
        if response.status_code >= 200 and response.status_code < 300:
            records = response.json()["records"]
            for record in records:
                if "Logged_Hours__r" in record:
                    total_hours = get_total_hours(record["Logged_Hours__r"])
                    if total_hours > record["Hours_Agreed_for_the_Month__c"]:
                        channel_id = record["Slack_Channel_id__c"]
                        message = "<!here>, hours have gone over hours allotted for the month!"
                        send_mention_in_channel(channel_id, message)


        # Replace with the actual channel_id and message you want
       
        
        
    def get_total_hours(logged_hours):
        total_hours = 0
        for logged_hour in logged_hours:
            if "Duration_in_hours__c" in logged_hour:
                total_hours = total_hours + (logged_hour["Duration_in_hours__c"] or 0)
        return total_hours
        
    @staticmethod
    def convertTableToSlackBlocks(rows, columns):
        import pandas as pd
        table = pd.DataFrame(rows,columns=columns)

        from tabulate import tabulate
        print(tabulate(table, tablefmt="orgtbl", headers="keys"))
        
        message_text = "<!here>, today's breakdown of assignments for this sprint. Pleae review to ensure we are pacing and tickets are assigned appropriately.\n\n"

        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message_text + tabulate(table, tablefmt="orgtbl", headers="keys")
                }
            }
        ]

        #ScheduledMessages.send_mention_in_channel(channel_id,"",markdown={"blocks":blocks})
        return blocks

    @staticmethod
    def send_mention_in_channel(channel_id, message, **kwargs):
        # Construct the message with the user mention
        full_message = message
        if "at_mention" in kwargs:
            user_id = kwargs["at_mention"]["user_id"]
            full_message = f"<@{user_id}> {message}"
        
        if "markdown" in kwargs:
            app.client.chat_postMessage(channel=channel_id, text=full_message,blocks=kwargs["markdown"]["blocks"])
            return 
    
        app.client.chat_postMessage(channel=channel_id, text=full_message)

if __name__ == "__main__":

    # notificatoins we should be putting out
    # 1) Account Team Contact Members vs Sprint Tickets vs Logged Hours
    # 2) tickets in the sprint without estimates on them
    # 2) Hours are getting close to limits (Month, week?)
    # 3) Ticket has changed from QA or UAT to something else too many times
    # 4) Ticket has too many sprints

    scheduler = ScheduledMessages()
    scheduler.sendStaffingReport()
