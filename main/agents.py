import  rag
import  config
import  geocoder
from    datetime                           import date
from    google                             import genai

client = genai.Client()

chunk_collection = rag.database_init()

def word_detection(text, word):
    detected = f'{word}' in f'{text}'
    print(f"Czy poprawnie wykryto {word}: {detected}")
    return detected

def current_date():
    today = date.today()
    print(today)
    return today

def user_location():
    location = geocoder.ip('me')
    print(location)
    return location.latlng

def generate_response(prompt, previous_response_id):
    print(previous_response_id)
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["system_instruction"],
        previous_interaction_id = previous_response_id,
        input = f'RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | USER TEXT {prompt}',
        generation_config = config.llm["generation_config"],
    )
    return interaction

def response_type(current_interaction, previous_response_id):
    # If reponse prompt contain thought key word
    model_response = current_interaction.output_text
    current_id = current_interaction.id
    if word_detection(model_response, '<thought>') == True:
        # Add thought to conversation history and remember that model has thought in this response
        thought_or_action_key_word = True
        interaction_id = current_id
    # Else if reponse prompt contain action key word
    elif word_detection(model_response, '<action>') == True:
        # Use tool, add its output to conversation history and remember that model has used tool
        if word_detection(model_response, 'current_date') == True:
            date = current_date()
            prompt = f"current_date tool RESPONSE: {date}"
        elif word_detection(model_response, 'user_location') == True:
            location = user_location()
            prompt = f"user_location tool RESPONSE: {location}"
        else:
            # ERROR
            prompt = "There was an error related to calling function. Retry with <action> tool </aciton>. Accesible tools are 'current_date' and 'user_location'"

        # Generate new interaction to pass the results of called tool to conversation history also change interacion id in session state to the newest one 
        interaction = generate_response(prompt, previous_response_id)
        interaction_id = interaction.id
        thought_or_action_key_word = True

        # TUTAJ DODAJ RESPONSE_TYPE = trzeba na nowo sprawdzic jaki to typ odpowiedzi - DUUUPA

        print("INTERACTION:", interaction.output_text)
    # Else if reponse prompt contain answer key word
    elif word_detection(model_response, '<answer>') == True:
        thought_or_action_key_word = False
        interaction_id = current_id
    # Else it there wasn't any of the key words 
    else:
        prompt = "ERROR: try again. You have to use one of following key words at the end of your response to highlight on which ReAct step you are: </end>, </answer>, </thought>, </action>."
        interaction = generate_response(prompt, previous_response_id)
        interaction_id = interaction.id
        thought_or_action_key_word = False

        # TUTAJ DODAJ RESPONSE_TYPE = trzeba na nowo sprawdzic jaki to typ odpowiedzi - DUUUPA

        print("INTERACTION:", interaction.output_text)

    return interaction_id, thought_or_action_key_word