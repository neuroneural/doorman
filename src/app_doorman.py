import slack
import csv
import random
import openai
import time
import os
import re
import jsonify              
import json
import pandas               as pd
from doorman_functions      import *
from pathlib                import Path
from dotenv                 import load_dotenv
from flask                  import Flask
from flask                  import request
from slackeventsapi         import SlackEventAdapter

app = Flask(__name__)
env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)
with open("adminKeys.json", "r") as file:
    loaded_keys = json.load(file)
# Load OpenAI, BotID, Slack Token and Slack Events Token
openai.api_key = token=os.environ['CHAT_TOKEN']
doorman_id = token=os.environ['DOORMAN_ID']
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/doorman/', app)

# Load question set and construct updated prompt
df = pd.read_csv('QandA_list.csv', encoding='utf-8')
answers = df["Question answers"].tolist()
extract_and_format("QandA_list.csv","llmlads_prompt.txt")
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
    if user_id == doorman_id:
        return None
    if (channel_id[0]!='D' and doorman_id in text):
        inp = remove_pings(inp,doorman_id)
        if len(inp) != 0:       
            index = format_links(doorman(inp,message_ts))
            client.chat_postMessage(
                    channel=channel_id,
                    text=index,
                    thread_ts=message_ts)
        else:
            client.chat_postMessage(
                    channel=channel_id,
                    text="Please ensure that your question is in the message you are mentioning Doorman in",
                    thread_ts=message_ts)
    elif (channel_id[0] == 'D'):
        index = doorman(inp,message_ts)
        print(f"Doorman response: {index}")
        if index != None:
            client.chat_postMessage(channel=user_id, text=index,thread_ts=message_ts)

@app.route('/doorman/addnewgroup', methods=['GET','POST'])
def addingGroup():
    data = request.form
    user = data.get('user_id')
    if adminAuth(user) is False:
        return "I appreciate your attempt to fix up the question set but you aren't authorized"
    text = data.get('text')
    trigger_id = request.form['trigger_id']
    open_addition_modal(trigger_id)
    return '', 200

@app.route('/doorman/claimadmin', methods=['GET','POST'])
def adminClaim():
    with open('adminKeys.json', "r") as file:
            user_ids = json.load(file)
    if not user_ids:
        data = request.form
        user = data.get('user_id')
        adminAdd(user) 
    else:
        return f"Admin slot has already been claimed, please ask an admin to promote you.", 200
    return 'Welcome to the Admin Team', 200

@app.route('/doorman/addadmin', methods=['GET','POST'])
def adminAddition():
    data=request.form
    user = data.get('user_id')   
    text = data.get('text') 
    if adminAuth(user) is False:
        return("Only admins are allowed to promote users")
    with open('adminKeys.json', "r") as file:
            user_ids = json.load(file)
    if text in user_ids:
        return f'{text} is already an admin'
    adminAdd(text)
    return f'User {text} added to admins', 200

@app.route('/doorman/removeadmin', methods=['GET','POST'])
def adminRemoval():
    data=request.form
    user = data.get('user_id')   
    text = data.get('text') 
    if adminAuth(user) is False:
        return("Only admins are allowed to demote users")
    with open('adminKeys.json', "r") as file:
            user_ids = json.load(file)
    if text not in user_ids:
        return f'{text} is not an admin'
    adminRemove(text)
    
    return f'User {text} removed from admins', 200

@app.route('/doorman/rmgroup', methods=['GET','POST'])
def questionSetRemove():
    data=request.form
    user = data.get('user_id')
    if adminAuth(user) is False:
        return "I appreciate your attempt to fix up the question set but you aren't authorized"
    text = data.get('text')
    trigger_id = request.form['trigger_id']
    open_deletion_modal(trigger_id)
    extract_and_format("QandA_list.csv","llmlads_prompt.txt")
    client.chat_postMessage(channel='#test', text=f'Current amount of questions:{get_number_of_rows("QandA_list.csv")}' )

    return '', 200

@app.route('/doorman/howmanyqs', methods=['GET','POST'])
def howManyQuestions():
    client.chat_postMessage(channel='#test', text=f'Current amount of questions:{get_number_of_rows("QandA_list.csv")}' )
    return '', 200

@app.route('/doorman/printqlist', methods=['GET','POST'])
def printQuestionList():
    with open('llmlads_prompt.txt', 'r', encoding='utf-8') as file:
        content = file.read()
    return f'Current question list:{content}', 200

@app.route('/doorman/interactive', methods=['POST'])
def slack_interactive():
    payload = request.form['payload']
    data = json.loads(payload)

    # Check for modal submission
    if data["type"] == "view_submission" and data["view"]["callback_id"] == "question_modal":
        # Extract data from the modal
        values = data["view"]["state"]["values"]
        question_prompt = values["answer_label"]["answer_label_input"]["value"]
        example_questions = values["example_questions"]["example_input"]["value"]
        answer = values["answer_input"]["answer_input"]["value"]

        add_new_row_to_csv("QandA_list.csv",question_prompt,example_questions,answer)
        extract_and_format("QandA_list.csv","llmlads_prompt.txt")
        client.chat_postMessage(channel='#test', text=f'Current amount of questions:{get_number_of_rows("QandA_list.csv")}' )
    if 'actions' in data:
        action = data['actions'][0]
        
        if action['action_id'].startswith('delete_question_'):
            question_index = int(action['action_id'].split('_')[-1])-1# Subtract 1 for zero-based indexing
            remove_row_by_number("QandA_list.csv",question_index)
            
            # Generate the new modal content
            new_modal = generate_modal_from_csv()
            response = update_slack_modal(data['trigger_id'],data['view']['id'], new_modal)
    return '', 200

def adminAuth(key_to_check, filename="adminKeys.json"):
    try:
        with open(filename, "r") as file:
            admin_keys = json.load(file)
            return key_to_check in admin_keys
    except FileNotFoundError:
        print(f"File {filename} not found!")
        return False
    
def adminAdd(user, filename="adminKeys.json"):
    """Add a new user ID to the specified JSON file without overwriting existing IDs."""
    # Load existing user IDs, if any
    try:
        with open(filename, "r") as file:
            user_ids = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        user_ids = []
    # Add the new user ID if it's not already in the list
    if user not in user_ids:
        user_ids.append(user)
        # Save the updated list back to the file
        with open(filename, "w") as file:
            json.dump(user_ids, file)

def adminRemove(user, filename="adminKeys.json"):
    """Remove a new user ID to the specified JSON file without overwriting existing IDs."""
    # Load existing user IDs, if any
    try:
        with open(filename, "r") as file:
            user_ids = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        user_ids = []
    # Add the new user ID if it's not already in the list
    if user in user_ids:
        user_ids.remove(user)
        # Save the updated list back to the file
        with open(filename, "w") as file:
            json.dump(user_ids, file)

# Surely we can do something better than this 
def wakeUp():
    time_string = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime())
    client.chat_postMessage(channel='#test', text='Hello LLMYST I woke up at: '+ time_string)

if __name__ == "__main__":
    wakeUp()
    app.run(debug=True, port=5000)
    print("Terminated Doorman")
