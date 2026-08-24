import  rag
import  json
import  config
import  geocoder
from    datetime                           import date
from    google                             import genai
from    pydantic                           import BaseModel

client = genai.Client()

chunk_collection = rag.database_init()

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
        system_instruction = config.llm[agent_type+'_instruction'],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history} | RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | PROMPT: {prompt}',
        generation_config = config.llm["agent_config"],
        response_format = config.llm[agent_type+"_response_format"],
    )

    # Zapisujesz wynik do klasy - po co? Po 2 jak możesz później uzyskać dostęp do tych informacji z klasy. To co teraz jest ponizej jest chyba bez sensu bo nie mam jeszcze nic zapisane w tych klasach

    #if agent_type == 'interview_agent':
     #   result = config.InterviewAgentResponse.model_validate_json(interaction.output_text)
    #elif agent_type == 'planner_agent':
     #   result = config.PlannerAgentResponse.model_validate_json(interaction.output_text)
    
    print("Response type before json: ", type(interaction.output_text))

    agent_answer = json.loads(interaction.output_text)

    print("Agent response: ", agent_answer)
    print("Response type: ", type(agent_answer))
    print("Agent response content: ", agent_answer["content"])

    return interaction

def orchiestrator(prompt, answer_history, current_ReAct_history):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, PROMPT: {prompt}',
        generation_config = config.llm["orchestrator_config"],
        response_format = config.llm["orchestrator_response_format"],
    )

    print("Response type before json: ", type(interaction.output_text))

    orchestrator_answer = json.loads(interaction.output_text)

    print("Agent chosed by an orchestrator: ", orchestrator_answer)
    print("Response type: ", type(orchestrator_answer))
    print("Agent: ", orchestrator_answer["agent"])

    return orchestrator_answer

class InterviewAgent:
    def __init__(self):
        self.state = config.InterveiwState()

    def response(self, prompt, answer_history, current_ReAct_history):
        interaction = agent_response(prompt=prompt, answer_history=answer_history, current_ReAct_history=current_ReAct_history, agent_type="interview_agent")
        self.state = interaction.output_text["state_updates"]
        
        return interaction

class PlannerAgent:
    def __init__(self):
        self.state = config.PlanningState()

    def response(self, prompt, answer_history, current_ReAct_history):
        interaction = agent_response(prompt=prompt, answer_history=answer_history, current_ReAct_history=current_ReAct_history, agent_type="planner_agent")
        self.state = interaction.output_text["state_updates"]
        
        return interaction