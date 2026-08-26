import  rag
import  json
import  config
import  geocoder
from    datetime                           import date
from    google                             import genai
from    pydantic                           import BaseModel, Field

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
    response = config.InterviewAgentResponse.model_validate_json(interaction.output_text)

    return response

def orchiestrator(prompt, answer_history, current_ReAct_history):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, PROMPT: {prompt}',
        generation_config = config.llm["orchestrator_config"],
        response_format = config.llm["orchestrator_response_format"],
    )
    print("Response type before json: ", type(interaction.output_text))

    decision = config.OrchestratorResponse.model_validate_json(interaction.output_text)

    print("Agent chosed by an orchestrator: ", decision)

    return decision

class InterviewAgent:
    def __init__(self):
        self.state = config.InterviewState()

    def response(self, prompt, answer_history, current_ReAct_history):
        response = agent_response(prompt=prompt, answer_history=answer_history, current_ReAct_history=current_ReAct_history, agent_type="interview_agent")
        if response.state_updates is not None:
            self.state = self.state.model_copy(update=response.state_updates.model_dump(exclude_defaults=True))
        return response

class PlannerAgent:
    def __init__(self):
        self.state = config.PlannerState()

    def response(self, prompt, answer_history, current_ReAct_history):
        response = agent_response(prompt=prompt, answer_history=answer_history, current_ReAct_history=current_ReAct_history, agent_type="planner_agent")
        if response.state_updates is not None:
            self.state = self.state.model_copy(update=response.state_updates.model_dump(exclude_defaults=True))
        return response