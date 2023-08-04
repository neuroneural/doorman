import openai

def doorman(prompt):
    #Load meta prompt
    with open('llmlads_prompt.txt','r') as file:
        meta_prompt = file.read()
    #Define API Call
    response = openai.ChatCompletion.create(
        #Choose model
        model = "gpt-3.5-turbo-16k",
        #Define 
        messages = [
            {"role": "system", "content": meta_prompt},
            {"role": "user", "content": prompt},
        ],
        #Define 'function' for model to call during execution
        functions = [
            {
                "name": "classify",
                #Verbal description to help the model use the function correctly,
                #for the time being, telling the model to return 0 if no matches are found
                #seems to do absolutely nothing
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
                #This actually does absolutely nothing, model frequently returns empty json
                #anyway, needs further testing
                "required": ["group"],
            },
        ],
        #Define model parameters
        max_tokens = 100,
        temperature = 0.8,
    )
    try:
        if (response["choices"][0]["message"]["function_call"]["arguments"] != "{}"):
            return int(response["choices"][0]["message"]["function_call"]["arguments"][13:-2])
        else:
            return 0
    except:
        return 0