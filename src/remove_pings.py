import re
def remove_pings(user_message, doorman_id):
    referencePattern = '<@'+doorman_id+'>'
    #re.search(referencePattern,user_message)
    #pattern = r''
    #user_message = "<THESTUFFDoorman><THESTUFFDoorman><THESTUFFDoorman><THESTUFFDoorman> Wowza <THEST@UFFISAID>"
    match = re.search(referencePattern, user_message, re.DOTALL)
    if match:
        pings = match.group(0)
        user_message = user_message.replace(str(pings), "")
    return(user_message)