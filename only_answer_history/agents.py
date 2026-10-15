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
        input = f'PROMPT: {PromptVariables.prompt}, CONVERSATION SUMMARY: {SessionVariables.answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {PromptVariables.current_ReAct_history}',
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
        print(f"----AGENT {self.agent_type} sees following ReAct history as a context: {PromptVariables.current_ReAct_history}.")      
        interaction = client.interactions.create(
            model = config.llm["model"],
            system_instruction = self.system_prompt,
            input = f'PROMPT: {PromptVariables.prompt}, CONVERSATION SUMMARY: {SessionVariables.answer_history}, ReAct HISTORY FROM NEWEST USER PROMPT: {PromptVariables.current_ReAct_history}',
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
        return response

class InterviewAgent(Agent):
    def __init__(self,):
        self.agent_type = "interview_agent"
        self.system_prompt = config.llm['interview_agent_instruction']
        self.response_format = config.llm["interview_agent_response_format"]
        self.validate_response = config.InterviewAgentResponse.model_validate_json

class PlannerAgent(Agent):
    def __init__(self,):
        self.agent_type = "planner_agent"
        self.system_prompt = config.llm['planner_agent_instruction']
        self.response_format = config.llm["planner_agent_response_format"]
        self.validate_response = config.PlannerAgentResponse.model_validate_json

class TrackingAgent(Agent):
    def __init__(self,):
        self.agent_type = "tracking_agent"
        self.system_prompt = config.llm['tracking_agent_instruction']
        self.response_format = config.llm["tracking_agent_response_format"]
        self.validate_response = config.TrackingAgentResponse.model_validate_json