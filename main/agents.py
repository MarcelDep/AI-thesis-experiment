import  rag
import  config
import  logger
from    abc                                import ABC, abstractmethod
from    google                             import genai

client = genai.Client()

chunk_collection = rag.database_init()

# Czy orchiestrator potrzebuje state tracking agenta i plannera? Moze uzyj jev'a do tego 
def orchiestrator(SessionVariables: config.SessionVariables, PromptVariables: config.PromptVariables) -> config.OrchestratorResponse:
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = config.llm["orchestrator_instruction"],
        input = f'CONVERSATION SUMMARY: {SessionVariables.conv_summary} LAST 4 MESSAGES: {SessionVariables.answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {PromptVariables.current_ReAct_history}, INTERVIEW AGENT STATE: {SessionVariables.agent_states.interview_agent_state}, PLANNER AGENT STATE: {SessionVariables.agent_states.planner_agent_state}, TRACKING AGENT STATE: {SessionVariables.agent_states.tracking_agent_state}, PROMPT: {PromptVariables.prompt}',
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

class Agent(ABC):
    def response(self, SessionVariables: config.SessionVariables, PromptVariables: config.PromptVariables) -> str:
        print(f"----AGENT {self.agent_type} sees following state before response: {self.state}.")
        print(f"----AGENT {self.agent_type} sees following ReAct history as a context: {PromptVariables.current_ReAct_history}.")      
        interaction = client.interactions.create(
            model = config.llm["model"],
            system_instruction = self.system_prompt,
            # Dodaj jakoś zeby były automatycznie odpisuwane state agentów - nie ogólnie agents state tylko PLaner agent state: [state] itp
            input = f'CONVERSATION SUMMARY: {SessionVariables.conv_summary} LAST 4 MESSAGES: {SessionVariables.answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {PromptVariables.current_ReAct_history} | RAG CONTEXT: {PromptVariables.rag} | AGENT STATEs: {SessionVariables.agent_states} | PROMPT: {PromptVariables.prompt}',
            response_format = self.response_format,
            generation_config={
                "max_output_tokens": config.llm["max_output_tokens"],
            },
        )
        print(f"----AGENT {self.agent_type} response: ", interaction.output_text)
        print(f"----AGENT response process used {interaction.usage.total_output_tokens} tokens.")
        print(f"----ACTURAL token usage {interaction.usage.total_output_tokens}")
        response = self.validate_response(interaction.output_text)     
        # Rozwiąż problem tego, że czasami extrakcja dostanie nadmiarowe info (prompt wtedy kiedy go nie potrzebuje itp - moze ekstrakcja jako interfejs?)
        if response.response_type == 'answer':
            match self.agent_type:
                case "planner_agent":
                    self.extract_state(generated_answer=interaction.output_text)
                case "tracking_agent":
                    self.extract_state(prompt=PromptVariables.prompt, generated_answer=interaction.output_text)
        logger.log_agent_activity(f"{self.agent_type}", response.response_type, response.content, self.state)
        return response

    @abstractmethod
    def extract_state(self):
        ...

class InterviewAgent(Agent):
    def __init__(self,):
        self.agent_type = "interview_agent"
        self.state = config.InterviewState()
        self.system_prompt = config.llm['interview_agent_instruction']
        self.response_format = config.llm["interview_agent_response_format"]
        self.validate_response = config.InterviewAgentResponse.model_validate_json  
        self.extract_format = config.llm['interview_agent_extraction_format'] 
        self.validate_extraction = config.InterviewState.model_validate_json

    def extract_state(self, prompt: str):
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

    def extract_state(self, generated_answer: str,):
        print(f"----GENERATED answer to extract info from: {generated_answer}")
        system_instruction = f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
        interaction = client.interactions.create(
            model = config.llm["model"],
            system_instruction = system_instruction,
            input = f"Agent answer you're supposed to extract info form: AGENT ANSWER - {generated_answer}.",
            response_format = self.extract_format,
            generation_config={
                "max_output_tokens": config.llm["max_output_tokens"],
            },
        )
        response = self.validate_extraction(interaction.output_text)     
        self.state = self.state.model_copy(update=response.model_dump(exclude_defaults=True))
        print(f"----EXTRACTION of {self.agent_type} state: {self.state}")
        print(f"----EXTRACTION process used {interaction.usage.total_output_tokens} tokens.")

class TrackingAgent(Agent):
    def __init__(self,):
        self.agent_type = "tracking_agent"
        self.state = config.TrackingState()
        self.system_prompt = config.llm['tracking_agent_instruction']
        self.response_format = config.llm["tracking_agent_response_format"]
        self.validate_response = config.TrackingAgentResponse.model_validate_json
        self.extract_format = config.llm['tracking_agent_task_extraction_format'] 
        self.validate_extraction = config.TrackingState.model_validate_json

    def extract_state(self, generated_answer: str, prompt: str):
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

def summarize(summary: str, answer_history: list,) -> str:
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = f"You are an summarization agent. Your task is to summarize conversation based on its history. Your summary should be rather short. If CURRENT SUMMARY isn't empty then continue this summary instead generating new one. Just generate a contuniuation of it. If summary is empty then make one.",
        input = f'CONVERSATION HISTORY: {answer_history},  CURRENT SUMMARY: {summary}',
        generation_config={
            "max_output_tokens": config.llm["max_output_tokens"],
        },
    )
    return interaction.output_text
# Dodaj wymuszenie stworzenia wszystkich powyzszych selfow w kazdej klasie agent za pomoca @abstractmethod