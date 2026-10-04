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
def agent_response(prompt, answer_history, current_ReAct_history, agent_state, agent_type, system_instruction, response_format, additional_context):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = system_instruction,
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history} | RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | AGENT STATE: {agent_state} | ADDITIONAL CONTEXT: {additional_context} | PROMPT: {prompt}',
        response_format = response_format,
        generation_config={
            "max_output_tokens": config.llm["max_output_tokens"],
        },
    )
    return interaction

# Rozwiąż problem manualnego dodawania agentów do promtpa - słownik z statusem kazdego agenta?
def orchiestrator(prompt, answer_history, current_ReAct_history, interview_agent_state, planner_agent_state):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION HISTORY: {answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, INTERVIEW AGENT STATE: {interview_agent_state}, PLANNER AGENT STATE: {planner_agent_state}, PROMPT: {prompt}',
        response_format = config.llm["orchestrator_response_format"],
        generation_config={
            "max_output_tokens": config.llm["max_output_tokens"],
        },
    )

    decision = config.OrchestratorResponse.model_validate_json(interaction.output_text)
    logger.log_orchestrator_activity(decision.agent, decision.justification)
    print(f"----ORCHESTRATOR choosed agent: {decision}")
    print(f"----ORCHESTRATOR decision process used {interaction.usage.total_output_tokens} tokens.")
    return decision

class Agent:
    def response(self, prompt, answer_history, current_ReAct_history, additional_context, ):
        print(f"----AGENT {self.agent_type} sees following state before response: {self.state}.")
        print(f"----AGENT {self.agent_type} sees following ReAct history as a context: {current_ReAct_history}.")        
        interaction = agent_response(prompt=prompt, 
                                    answer_history=answer_history, 
                                    current_ReAct_history=current_ReAct_history, 
                                    agent_state=self.state, 
                                    agent_type=self.agent_type, 
                                    system_instruction=self.system_prompt, 
                                    response_format=self.response_format,
                                    additional_context=additional_context)
        print(f"----AGENT {self.agent_type} response: ", interaction.output_text)
        print(f"----AGENT response process used {interaction.usage.total_output_tokens} tokens.")
        print(f"----ACTURAL token usage {interaction.usage.total_output_tokens}")
        response = self.validate_response(interaction.output_text)     
        # Rozwiąż problem tego, że czasami extrakcja dostanie nadmiarowe info (prompt wtedy kiedy go nie potrzebuje itp - moze ekstrakcja jako interfejs?)
        if (response.response_type == 'answer' and self.agent_type != 'interview_agent'):
            self.extract_state(generated_answer=interaction.output_text, prompt=prompt)
        logger.log_agent_activity(f"{self.agent_type}", response.response_type, response.content, self.state)
        return response

    def extract_state(self, generated_answer, prompt):
        print(f"----LIST of fields to fill {self.state.model_fields.keys()}")
        print(f"----GENERATED answer to extract info from: {generated_answer}")
        print(f"----PROMPT to extract info from: {prompt}")
        system_instruction = f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
        interaction = client.interactions.create(
            model = config.llm["model"],
            system_instruction = system_instruction,
            input = f"Agent answer and tool output (if empty - none tool was called) from which you're supposed to extract info form: AGENT ANSWER - {generated_answer} PROMPT - {prompt}",
            response_format = self.extract_format,
            generation_config={
                "max_output_tokens": config.llm["max_output_tokens"],
            },
        )
        response = self.validate_extraction(interaction.output_text)     
        self.state = self.state.model_copy(update=response.model_dump(exclude_defaults=True))
        print(f"----EXTRACTION of {self.agent_type} state: {self.state}")
        print(f"----EXTRACTION process used {interaction.usage.total_output_tokens} tokens.")

class InterviewAgent(Agent):
    def __init__(self,):
        self.agent_type = "interview_agent"
        self.state = config.InterviewState()
        self.system_prompt = config.llm['interview_agent_instruction']
        self.response_format = config.llm["interview_agent_response_format"]
        self.validate_response = config.InterviewAgentResponse.model_validate_json  
        self.extract_format = config.llm['interview_agent_extraction_format'] 
        self.validate_extraction = config.InterviewState.model_validate_json

    def extract_state(self, prompt):
        print("====Values which are required to be filled: ", self.state.model_fields.keys())
        system_instruction = f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
        interaction = client.interactions.create(
            model = config.llm["model"],
            system_instruction = system_instruction,
            input = f"User prompt from which you're supposed to extract info form: {prompt}",
            response_format = self.extract_format,
            generation_config={
                "max_output_tokens": config.llm["max_output_tokens"],
            },
        )
        response = self.validate_extraction(interaction.output_text)     
        self.state = self.state.model_copy(update=response.model_dump(exclude_defaults=True))
        print(f"----EXTRACTION of {self.agent_type} state: {self.state}")
        print(f"----EXTRACTION process used {interaction.usage.total_output_tokens} tokens.")

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
        self.extract_format = config.llm['tracking_agent_task_extraction_format'] 
        self.validate_extraction = config.TrackingState.model_validate_json

# Dodaj wymuszenie stworzenia wszystkich powyzszych selfow w kazdej klasie agent za pomoca @abstractmethod