import random
def doormanFailure():
    randRoll = random.randint(0,3)
    match randRoll:
        case 0:
            text="I didn't understand that, I'm just a silly lil dude! Do you mind clarifying?"
        case 1:
            text="As an AI Large Language model I have to admit when I don't get what you're saying. Like I REALLY don't. Could you clarify for me?"
        case 2:
            text="Can you say that in a way a 2 month old would understand, thats how old I am."
        case 3:
            text="I'm so sorry I'm new here, find it in your heart to forgive me and try rephrasing that. I might just get it!"
        case _:
            text="def Case"
    return text