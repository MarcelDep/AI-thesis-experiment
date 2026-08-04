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

def response_type(model_response):
    if word_detection(model_response, '<thought>') == True:
        response_type = 'thought'
    elif word_detection(model_response, '<action>') == True:
        if word_detection(model_response, 'current_date') == True:
            response_type = 'action - current_date'
        elif word_detection(model_response, 'user_location') == True:
            response_type = 'action - user_location'
        else:
            response_type = 'Tool call related ERROR'
    elif word_detection(model_response, '<answer>') == True:
        response_type = 'answer'
    else:
        response_type = "Unknown key word in model response!"
    return response_type