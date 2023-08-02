import numpy as np
import json
import slack
import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
import pandas as pd

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

def doorman_v0(logs, t_id, prompt, answers):
    # Function params, mess around with these to experiment with model behvior
    null_response = "I'm sorry, could you provide more clarifying information?"
    max_tokens = 100
    temperature = 0.8
    with open('llmlads_prompt.txt','r') as file:
        meta_prompt = file.read()
    # Load thread log if exists
    system_prompt = np.array([{"role": "system", "content": meta_prompt}])
    user_prompt = np.array([{"role": "user", "content": prompt}])
    thread_log = np.array(load_log(logs, t_id))
    messages = np.concatenate((system_prompt, thread_log, user_prompt)).tolist()
    print(messages)
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
            return 0
    except:
        logs = append_log(logs, t_id, "user", prompt)
        logs = append_log(logs, t_id, "assistant", null_response)
        print("<dev flag> Function wasn't even called lol")
        return 0
    
################################################
#### surround this code with __name__ block ####
################################################
if __name__ == "__main__":
    df = pd.read_csv('QandA_list.csv', encoding='utf-8')
    answers = df["Question answers"].tolist()
    env_path = Path('.')/'.env'
    load_dotenv(dotenv_path=env_path)
    openai.api_key = token=os.environ['CHAT_TOKEN']
    try:
        logs = load_json_from_file("doorman_log.json")
        while(True):
            t_id = input("Thread ID: ")
            prompt = input("User prompt: ")
            index = doorman_v0(logs, t_id, prompt, answers)
            if index == 0:
                print("Not found")
            else:
                print("Found")
                print(answers[index-1])
    except:
        print("<dev flag> doorman log not found, making empty file called doorman_log.json")
        logs = {"logs" : []}
        write_json_to_file(logs, "doorman_log.json")
################################################
################################################
################################################
