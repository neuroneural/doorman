import json
import slack
import openai
import os
import requests
import re
import random
import csv
import time
import numpy        as np
import pandas       as pd
from slackeventsapi import SlackEventAdapter
from pathlib        import Path
from dotenv         import load_dotenv
from flask          import Flask

def write_json_to_file(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f)

def load_json_from_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data['logs']

def append_log(logs, t_id, role, content):
    for log in logs:
        if (log['t_id'] == t_id):
            log['thread_log'].append({"role": role, "content": content})
            return logs
    new_log = {
        "t_id": t_id,
        "thread_log": [
            {"role": role, "content": content}
        ],
    }
    logs.append(new_log)
    return logs

def load_log(logs, t_id):
    for log in logs:
        if (log['t_id'] == t_id):
            return log['thread_log']
    return []

def query(t_id, prompt, answers,logs):
    # Function params, mess around with these to experiment with model behvior
    null_response = "I'm sorry, could you provide more clarifying information?"
    max_tokens = 100
    temperature = 0.8
    with open('llmlads_prompt.txt','r', encoding='utf-8') as file:
        meta_prompt = file.read()
    # Load thread log if exists
    system_prompt = np.array([{"role": "system", "content": meta_prompt}])
    user_prompt = np.array([{"role": "user", "content": prompt}])
    thread_log = np.array(load_log(logs, t_id))
    messages = np.concatenate((system_prompt, thread_log, user_prompt)).tolist()
    #print(messages)
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo-16k",
        messages = messages,
        functions = [
            {
                "name": "classify",
                "description": "classify a user statement into one of the statement groups using a json format, output 0 if there are no matches",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group": {
                            "type": "number",
                            "description": "index of group that the statement most resembles",
                        },
                    },
                },
                "required": ["group"],
            },
        ],
        function_call="auto",
        max_tokens = 100,
        temperature = 0.8,
    )
    try:
        if (response["choices"][0]["message"]["function_call"]["arguments"] != "{}"):
            index = int(response["choices"][0]["message"]["function_call"]["arguments"][13:-2])
            answer = answers[index - 1]
            logs = append_log(logs, t_id, "user", prompt)
            logs = append_log(logs, t_id, "assistant", answer)
            return index
        else:
            logs = append_log(logs, t_id, "user", prompt)
            logs = append_log(logs, t_id, "assistant", null_response)
            print(logs)
            print("Null response returned")
            return 0
    except:
        logs = append_log(logs, t_id, "user", prompt)
        logs = append_log(logs, t_id, "assistant", null_response)
        print("<dev flag> Function wasn't even called lol")
        return 0
    
def doorman(input,thread_id):
    df = pd.read_csv('QandA_list.csv', encoding='utf-8')
    answers = df["Question answers"].tolist()
    try:
        logs = load_json_from_file("doorman_log.json")
        t_id = thread_id
        prompt = input
        index = query(t_id, prompt, answers, logs)
        if index == 0:
            print("Not found")
            write_json_to_file({"logs" :logs}, "doorman_log.json")
            return(doormanFailure())
        else:
            print("Found")
            write_json_to_file({"logs" :logs}, "doorman_log.json")
            return(answers[index-1])
    except Exception as e:
        if os.path.isfile("doorman_log.json"):
            print("<dev flag> something went wrong, but doorman_log.json exists")
            print(e)
        else:
            print("<dev flag> doorman log not found, making empty file called doorman_log.json")
            logs = {"logs" : []}
            write_json_to_file(logs, "doorman_log.json")
            return doorman(input,thread_id)

def remove_pings(user_message, doorman_id):
    referencePattern = '<@'+doorman_id+'>'
    match = re.search(referencePattern, user_message, re.DOTALL)
    if match:
        pings = match.group(0)
        user_message = user_message.replace(str(pings), "")
    return(user_message)

def format_links(s):
    # Regular expression to match URLs
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    print(s)
    return url_pattern.sub(lambda x: f"<{x.group(0)}|Link>", s)

def doormanFailure():
    failure_responses = [
            "I didn't understand that, I'm just a silly lil dude! Do you mind clarifying?",
            "As an AI Large Language model I have to admit when I don't get what you're saying. Like I REALLY don't. Could you clarify for me?",
            "Can you say that in a way a 2 month old would understand, thats how old I am.",
            "I'm so sorry I'm new here, find it in your heart to forgive me and try rephrasing that. I might just get it!",
            "Whoopsie daisy! I dropped the ball on finding this answer!",
    ]
    rand = random.randint(0,len(failure_responses)-1)
    return failure_responses[rand]

def add_new_row_to_csv(csv_path, question_prompt, example_questions, answer):
    # Read the existing CSV
    df = pd.read_csv(csv_path)
    # Add a new row to the dataframe
    new_row = {
        'Question Categories': question_prompt,
        'Question answers': answer,
        'Model Questions': example_questions,
        'Keywords': ''  # Assuming an empty value for Keywords as it's not provided
    }
    new_df = pd.DataFrame(new_row, index=[0])
    updated_df = pd.concat([df, new_df], ignore_index=True)
    # Save the updated dataframe back to the CSV
    updated_df.to_csv(csv_path, index=False)

def remove_row_by_number(csv_path, row_number):
    row_number = row_number-1
    # Read the existing CSV
    df = pd.read_csv(csv_path)
    #print deleted row
    delRow = df.iloc[row_number]
    # Drop the specified row
    df.drop(index=row_number, inplace=True)
    # Reset the index
    df.reset_index(drop=True, inplace=True)
    # Save the updated dataframe back to the CSV
    df.to_csv(csv_path, index=False)
    return delRow

def get_number_of_rows(csv_path):
    # Read the existing CSV
    df = pd.read_csv(csv_path)
    # Return the number of rows
    return df.shape[0] 

def extract_and_format(csv_path, output_path):
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as csv_file:
        reader = csv.reader(csv_file)
        next(reader)  # Skip header row
        
        formatted_data = []
        group_num = 1
        for row in reader:
            formatted_data.append(f"{group_num}: {row[0]}\n{row[2]}")
            group_num += 1
        
        formatted_string = "Given the following group of statements, classify a user statement into the most similar group. If there are no matches, output 0 for the question group. Use the \"classify\" function provided:\nList of groups: \n"
        formatted_string += '\n'.join(formatted_data)
        
        with open(output_path, 'w', encoding='utf-8', errors='replace') as output_file:
            output_file.write(formatted_string)

def open_addition_modal(trigger_id):
    headers = {
        "Authorization": f"Bearer {os.environ['SLACK_TOKEN']}",
        "Content-Type": "application/json"
    }
    
    # Modal payload
    modal = {
        "trigger_id": trigger_id,
        "view": {
            "type": "modal",
            "callback_id": "question_modal",
            "title": {"type": "plain_text", "text": "Question Details"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "answer_label",
                    "label": {"type": "plain_text", "text": "Answer Label"},
                    "element": {"type": "plain_text_input", "action_id": "answer_label_input","placeholder": {
            "type": "plain_text",
            "text": "The label befitting your answer"
        }}
                },
                {
                    "type": "input",
                    "block_id": "example_questions",
                    "label": {"type": "plain_text", "text": "Example Questions"},
                    "element": {"type": "plain_text_input","multiline" : True, "action_id": "example_input", "placeholder": {
            "type": "plain_text",
            "text": "List of questions answered by your answer"
        }
}
                },
                {
                    "type": "input",
                    "block_id": "answer_input",
                    "label": {"type": "plain_text", "text": "Answer"},
                    "element": {"type": "plain_text_input", "action_id": "answer_input","placeholder": {
            "type": "plain_text",
            "text": "The answer to your question set"
        }}
                }
            ],
            "submit": {
                "type": "plain_text",
                "text": "Submit"
    }
        }
    }
    response = requests.post("https://slack.com/api/views.open", headers=headers, json=modal)

def open_deletion_modal(trigger_id):
    headers = {
        "Authorization": f"Bearer {os.environ['SLACK_TOKEN']}",
        "Content-Type": "application/json"
    }
    
    # Modal payload
    modal = {
        "trigger_id": trigger_id,
        "view": generate_modal_from_csv()
    }
    response = requests.post("https://slack.com/api/views.open", headers=headers, json=modal)
    
def generate_modal_from_csv():
    # Read the CSV
    rows = []
    with open('QandA_list.csv', 'r',encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            rows.append(row)

    # Dynamically generate the blocks based on CSV content
    blocks = []
    for index, row in enumerate(rows, 1):
        block = {
            "type": "section",
            "block_id": f"question_row_{index}",
            "text": {
                "type": "mrkdwn",
                "text": f"Question {index}: {row[0]}"  # Assuming the question is the first column
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Delete"
                },
                "action_id": f"delete_question_{index}"
            }
        }
        blocks.append(block)
        blocks.append({"type": "divider"})
    return {"type": "modal", "callback_id": "csv_modal", "title": {"type": "plain_text", "text": "Manage Questions"}, "blocks": blocks}

def update_slack_modal(trigger_id, view_id,new_modal_payload):
    url = "https://slack.com/api/views.update"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {os.environ['SLACK_TOKEN']}"  # Replace with your bot token
    }
    data = {
        "trigger_id": trigger_id,
        "view_id": view_id,
        "view": new_modal_payload
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    return response.json()