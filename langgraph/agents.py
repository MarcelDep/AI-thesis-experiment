import  rag
import  config
import  logger
from    abc              import ABC, abstractmethod
from    google           import genai
from    langchain.agents import create_agent

client = genai.Client()

chunk_collection = rag.database_init()

llm = init_chat_model(
    config.llm["model"],
    model_provider=config.llm["model_provider"],
)

class Agent():
    def response(self, agent, state):
        return self.agent.invoke(state)

    @abstractmethod
    def extract_state(self):
        ...

def router(state: config.State):
    prompt = state["messages"][-1]
    conv_history = state["messages"]
    previous_thought = state["previous_thought"]
    interview_state = state["interview_state"]
    planner_state = state["planner_state"]
    tracking_state = state["tracking_state"]

    router_llm = llm.with_structured_output(config.RouterResponse)

    decision = router_llm.invoke([
        {
            "role": "system",
            "content": config.llm.router_instruction
        },
        {"role": "user", "content": f"USER PROMPT: {prompt}. CONVERSATION HISTORY: {conv_history}. PREVIOUS THOUGHTs: {previous_thought}. INTERVIEW AGENT STATE: {interview_state}. PLANNER AGENT STATE: {planner_state}. TRACKING AGENT STATE: {tracking_state}"}
    ])

    print(f"----ROUTER picked {decision.choosed_agent} to respond because {decision.justification}.")
    return {"next_node": decision.choosed_agent}

class InterviewAgent(Agent):
    def __init__(self):
        self.agent_response = config.InterviewResponse()
        self.agent_instruction = config.llm["interview_agent_instruction"]
        self.agent_extraction = config.InterviewExtraction()
        self.agent_tools = config.interview_agent_tools
        self.agent_model = config.llm["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=self.agent_response)

    def extract_state(self, state: config.State):
        prompt = state["messages"][-1]
        extract_llm = llm.with_structured_output(self.agent_extraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"User prompt from which you're supposed to extract info form: {prompt}."}
        ])

        print(f"----EXTRACTION of {state.choosed_agent} state: {response.content}")
        return {"interview_state": response.content}

class PlannerAgent(Agent):
    def __init__(self):
        self.agent_response = config.PlannerResponse()
        self.agent_instruction = config.llm["planner_agent_instruction"]
        self.agent_extraction = config.PlannerExtraction()
        self.agent_tools = config.interview_agent_tools
        self.agent_model = config.llm["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=self.agent_response)

    def extract_state(self, state: config.State, generated_answer: str,):
        prompt = state["messages"][-1]
        extract_llm = llm.with_structured_output(self.agent_extraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"CURRENT PLANNER STATE: {state.planner_state}. Agent answer you're supposed to extract info form - {generated_answer}."}
        ])

        print(f"----EXTRACTION of {state.choosed_agent} state: {response.content}")
        return {"planner_state": response.content}

class TrackingAgent(Agent):
    def __init__(self):
        self.agent_response = config.TrackingResponse()
        self.agent_instruction = config.llm["tracking_agent_instruction"]
        self.agent_extraction = config.TrackingExtraction()
        self.agent_tools = config.tracking_agent_tools
        self.agent_model = config.llm["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=self.agent_response)

    def extract_state(self, state: config.State, generated_answer: str):
        prompt = state["messages"][-1]
        extract_llm = llm.with_structured_output(self.agent_extraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"Agent answer and tool output (if empty - none tool was called) from which you're supposed to extract info form: AGENT ANSWER - {generated_answer} PROMPT - {prompt}"}
        ])

        print(f"----EXTRACTION of {state.choosed_agent} state: {response.content}")
        return {"tracking_state": response.content}

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