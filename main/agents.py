import  rag
import  json
import  config
import  logger
import  geocoder
from    abc                                import ABC
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

def agent_response(prompt, answer_history, current_ReAct_history, agent_state, agent_type, system_instruction, response_format):
    print(f"Agent {agent_type} sees following state as a context: {agent_state}.")
    print(f"Agent {agent_type} sees following ReAct history as a context: {current_ReAct_history}.")
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = system_instruction,
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history} | RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | AGENT STATE: {agent_state} | PROMPT: {prompt}',
        response_format = response_format,
    )

    return interaction

def orchiestrator(prompt, answer_history, current_ReAct_history, interview_agent_state, planner_agent_state):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, INTERVIEW AGENT STATE: {interview_agent_state}, PLANNER AGENT STATE: {planner_agent_state}, PROMPT: {prompt}',
        response_format = config.llm["orchestrator_response_format"],
    )

    decision = config.OrchestratorResponse.model_validate_json(interaction.output_text)
    logger.log_orchestrator_activity(decision.agent, decision.justification)
    print("Agent chosed by an orchestrator: ", decision)

    return decision

class Agent(ABC):
    def response(self, prompt, answer_history, current_ReAct_history,):
        interaction = agent_response(prompt=prompt, 
                                    answer_history=answer_history, 
                                    current_ReAct_history=current_ReAct_history, 
                                    agent_state=self.state, 
                                    agent_type=self.agent_type, 
                                    system_instruction=self.system_prompt, 
                                    response_format=self.response_format)
        response = self.validate_json(interaction.output_text)        
        if response.state_updates is not None:
            self.state = self.state.model_copy(update=response.state_updates.model_dump(exclude_defaults=True))
        print(f"{self.agent_type} state {self.state}")   
        logger.log_agent_activity(f"{self.agent_type}", response.response_type, response.content, self.state)
        return response, self.state

class InterviewAgent(Agent):
    def __init__(self,):
        self.agent_type = "interview_agent"
        self.state = config.InterviewState()
        self.system_prompt = config.llm['interview_agent_instruction']
        self.response_format = config.llm["interview_agent_response_format"]
        self.validate_json = config.InterviewAgentResponse.model_validate_json

class PlannerAgent(Agent):
    def __init__(self,):
        self.agent_type = "planner_agent"
        self.state = config.PlannerState()
        self.system_prompt = config.llm['planner_agent_instruction']
        self.response_format = config.llm["planner_agent_response_format"]
        self.validate_json = config.PlannerAgentResponse.model_validate_json

class TrackingAgent(Agent):
    def __init__(self,):
        self.agent_type = "tracking_agent"
        self.state = config.TrackingState()
        self.system_prompt = config.llm['tracking_agent_instruction']
        self.response_format = config.llm["tracking_agent_response_format"]
        self.validate_json = config.TrackingAgentResponse.model_validate_json

# Dodaj wymuszenie stworzenia wszystkich powyzszych selfow w kazdej klasie agent za pomoca @abstractmethod