import csv
import json

# Read the CSV file and write to a text file as newline-separated JSON objects
with open("/Users/grambischof/Downloads/cloud connex bert fine - tune data set - Burt Questions (2).csv", "r") as csvfile, open("output.jsonl", "w") as txtfile:
    csvreader = csv.DictReader(csvfile)
    for row in csvreader:
        messages = []
        
        # Assuming each row has the headers in a structured manner
        # You may need to adjust this according to the actual structure
        messages.append({"role": row["role1"], "content": row["content1"]})
        messages.append({"role": row["role2"], "content": row["content2"]})
        
        # Adding Classification and Full Classification to the messages list
        classification_dict = {
            "Classification": row["Classification"],
            "Full Classification": row["Full Classification"]
        }
        messages.append({"role": row["role3"], "content": json.dumps(classification_dict)})
        
        # Constructing JSON object for each row
        json_object = {
            "messages": messages
        }
        
        # Writing each JSON object to the text file, separated by newline
        txtfile.write(json.dumps(json_object) + '\n')
