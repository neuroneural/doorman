import re
def remove_pings(user_message):
    pattern = r'<@U05EY26K3FZ>'
    #user_message = "<THESTUFFDoorman><THESTUFFDoorman><THESTUFFDoorman><THESTUFFDoorman> Wowza <THEST@UFFISAID>"
    match = re.search(pattern, user_message, re.DOTALL)
    if match:
        pings = match.group(0)
        user_message = user_message.replace(str(pings), "")
    return(user_message)