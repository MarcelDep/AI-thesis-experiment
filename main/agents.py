import  rag
import  config
import  geocoder
from    datetime                           import date
from    google                             import genai

client = genai.Client()

chunk_collection = rag.database_init()

def word_detection(text, word):
    detected = f'{word}' in f'{text}'
    print(f"Word {word}: {detected}")
    return detected

def current_date():
    today = date.today()
    print(today)
    return today

def user_location():
    location = geocoder.ip('me')
    print(location)
    return location.latlng

def agent_response(prompt, answer_history, current_ReAct_history, agent_type):
    print(f"Agent {agent_type} response:")
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm[agent_type],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history} | RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | PROMPT: {prompt}',
        generation_config = config.llm["agent_config"],
    )
    return interaction

def orchiestrator(prompt, answer_history, current_ReAct_history):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, PROMPT: {prompt}',
        generation_config = config.llm["orchestrator_config"],
    )
    model_response = interaction.output_text
    if word_detection(model_response, 'planer_instruction') == True:
        agent = 'planer_instruction'
    elif word_detection(model_response, 'interviewer_instruction') == True:
        agent = 'interviewer_instruction'
    else:
        agent = "ERROR: AGENT WASN'T CHOOSED!"

    return agent, model_response

def response_type(model_response):
    if word_detection(model_response, '<thought>') == True:
        response_type = 'thought'
    elif word_detection(model_response, '<action>') == True:
        if word_detection(model_response, 'current_date') == True:
            response_type = 'action - current_date'
        elif word_detection(model_response, 'user_location') == True:
            response_type = 'action - user_location'
        elif word_detection(model_response, 'switch_agent') == True:
            response_type = 'action - switch_agent'
        else:
            response_type = 'Tool call related ERROR'
    elif word_detection(model_response, '<answer>') == True:
        response_type = 'answer'
    else:
        response_type = "Unknown key word in model response!"
    return response_type