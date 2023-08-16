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
from wakeUp import wakeUp
from remove_pings import remove_pings
from doormanFailure import doormanFailure
from MLBBQ_script import *
from doorman_with_thread_mem import *
#Main things to remove hard coding from (Bot's user id)
#also todo (Remove the @Doorman from context being questioned in a good way)
df = pd.read_csv('QandA_list.csv', encoding='utf-8')
answers = df["Question answers"].tolist()

env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

openai.api_key = token=os.environ['CHAT_TOKEN']

doorman_id = token=os.environ['DOORMAN_ID']

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/doorman/',app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

#response = client.api_call("auth.text")
#BOT_ID = response['user_id']

wakeUp()

@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event',{})
    message_ts = event.get('ts')
    message_thread = event.get('thread_ts')
    print("Message ts:" + str(message_ts))
    print("Message thread:" + str(message_thread))
    if message_thread != None:
        message_ts=message_thread
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    inp = "User input: " + "\"" + text + "\""
    if user_id != doorman_id:
        if channel_id[0]!='D':
            if(doorman_id in text or checkFor(message_thread)):
                text = remove_pings(text,doorman_id)
                if len(text) != 0:       
                    index = doormanWMemory(text,message_ts)
                    client.chat_postMessage(channel=channel_id, text=index,thread_ts=message_ts)
                else:
                    client.chat_postMessage(channel=channel_id, text="Please ensure that your question is in the message you are mentioning Doorman in",thread_ts=message_ts)
        else:
            index = doormanWMemory(inp,message_ts)
            print("Doorman response:")
            print(index)
            if index != None:
                client.chat_postMessage(channel=user_id, text=index,thread_ts=message_ts)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
if 1==1:
    print("0")
