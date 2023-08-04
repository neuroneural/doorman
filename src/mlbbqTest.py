import slack
import random
import openai
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from flask import request
from slackeventsapi import SlackEventAdapter
import pandas as pd
import time
from doormanFunction import doorman
from wakeUp import wakeUp
from remove_pings import remove_pings
from doormanFailure import doormanFailure
from MLBBQ_script import *
import requests
#Main things to remove hard coding from (Bot's user id)
#also todo (Remove the @Doorman from context being questioned in a good way)
df = pd.read_csv('QandA_list.csv', encoding='utf-8')
answers = df["Question answers"].tolist()

env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

openai.api_key = token=os.environ['CHAT_TOKEN']



app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events',app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

#response = client.api_call("auth.text")
#BOT_ID = response['user_id']

wakeUp()


@app.route('/dumbitdown', methods=['GET','POST'])
def returnDumbedDown():
    try:
        data = request.form
        link = data.get('text')
        response_url = data.get('response_url')
        payload = {
            "text": dumb_down_abstract(link),
            "response_type": "in_channel",
            "replace_original": True
        }
        return payload
    finally:
        requests.post(response_url, data=payload)
  
    



@app.route('/getAuthor', methods=['GET','POST'])
def returnAuth():
    data = request.form
    link = data.get('text')
    response = get_authors(link)
    payload = {
        "text": str(response),
        "response_type": "in_channel",
        "delete_original": "true"
    }
    return payload

@app.route('/getTitle', methods=['GET','POST'])
def returnTitle():
    data = request.form
    link = data.get('text')
    response = get_title(link)
    payload = {
        "text": str(response),
        "response_type": "in_channel",
        "replace_original": False
    }
    return payload

@app.route('/getAbstract', methods=['GET','POST'])
def returnAbs():
    data = request.form
    link = data.get('text')
    response = get_abstract(link)
    payload = {
        "text": str(response),
        "response_type": "in_channel",
        "replace_original": False
    }
    return payload

@app.route('/getIntro', methods=['GET','POST'])
def returnIntro():
    data = request.form
    link = data.get('text')
    response = get_intro(link)
    payload = {
        "text": str(response),
        "response_type": "in_channel",
        "replace_original": False
    }
    return payload


@app.route('/getConclusion', methods=['GET','POST'])
def returnConclusion():
    data = request.form
    link = data.get('text')
    response = get_conclusion(link)
    payload = {
        "text": str(response),
        "response_type": "in_channel",
        "replace_original": False
    }
    return payload



if __name__ == "__main__":
    app.run(debug=True, port=4999)
if 1==1:
    print("0")