import  rag
import  json
import  config
import  logger
import  geocoder
import  requests
from    abc                                import ABC
from    datetime                           import date
from    google                             import genai
from    pydantic                           import BaseModel, Field

client = genai.Client()

chunk_collection = rag.database_init()

# Może dodaj state każdego agenta jako kontekst przy jego odpowiadaniu?

def agent_response(prompt, answer_history, current_ReAct_history, agent_state, agent_type, system_instruction, response_format):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = system_instruction,
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history} | RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | AGENT STATE: {agent_state} | PROMPT: {prompt}',
        response_format = response_format,
    )
    return interaction

# Rozwiąż problem manualnego dodawania agentów do promtpa - słownik z statusem kazdego agenta?
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

class Agent:
    def response(self, prompt, answer_history, current_ReAct_history,):
        print(f"Agent {self.agent_type} sees following state before response: {self.state}.")
        print(f"Agent {self.agent_type} sees following ReAct history as a context: {current_ReAct_history}.")        
        interaction = agent_response(prompt=prompt, 
                                    answer_history=answer_history, 
                                    current_ReAct_history=current_ReAct_history, 
                                    agent_state=self.state, 
                                    agent_type=self.agent_type, 
                                    system_instruction=self.system_prompt, 
                                    response_format=self.response_format)
        response = self.validate_response(interaction.output_text)        
        if response.response_type == 'answer' and self.agent_type != 'interview_agent':
            self.extract_state(answer_history=answer_history, current_ReAct_history=current_ReAct_history)  
            print(f"Agent {self.agent_type} sees following state after response: {self.state}.")
        logger.log_agent_activity(f"{self.agent_type}", response.response_type, response.content, self.state)
        return response

    def extract_state(self, answer_history, current_ReAct_history):
        prompt = f"Given this conversation and the latest answer, extract any information relevant to: {self.state.model_fields.keys()}, that was discussed. Return only what's explicitly stated."
        system_instruction = "You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
        interaction = agent_response(prompt=prompt,
                                    answer_history=answer_history, 
                                    current_ReAct_history=[current_ReAct_history], 
                                    agent_state=self.state, 
                                    agent_type=self.agent_type, 
                                    system_instruction=system_instruction, 
                                    response_format=self.extract_format)
        response = self.validate_extraction(interaction.output_text)     
        self.state = self.state.model_copy(update=response.model_dump(exclude_defaults=True))
        print(f"{self.agent_type} state extraction: {self.state}")

class InterviewAgent(Agent):
    def __init__(self,):
        self.agent_type = "interview_agent"
        self.state = config.InterviewState()
        self.system_prompt = config.llm['interview_agent_instruction']
        self.response_format = config.llm["interview_agent_response_format"]
        self.validate_response = config.InterviewAgentResponse.model_validate_json  
        self.extract_format = config.llm['interview_agent_extraction_format'] 
        self.validate_extraction = config.InterviewState.model_validate_json

class PlannerAgent(Agent):
    def __init__(self,):
        self.agent_type = "planner_agent"
        self.state = config.PlannerState()
        self.system_prompt = config.llm['planner_agent_instruction']
        self.response_format = config.llm["planner_agent_response_format"]
        self.validate_response = config.PlannerAgentResponse.model_validate_json
        self.extract_format = config.llm['planner_agent_extraction_format'] 
        self.validate_extraction = config.PlannerState.model_validate_json

class TrackingAgent(Agent):
    def __init__(self,):
        self.agent_type = "tracking_agent"
        self.state = config.TrackingState()
        self.system_prompt = config.llm['tracking_agent_instruction']
        self.response_format = config.llm["tracking_agent_response_format"]
        self.validate_response = config.TrackingAgentResponse.model_validate_json
        self.extract_format = config.llm['tracking_agent_extraction_format'] 
        self.validate_extraction = config.TrackingState.model_validate_json

# Dodaj wymuszenie stworzenia wszystkich powyzszych selfow w kazdej klasie agent za pomoca @abstractmethod