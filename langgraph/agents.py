import  rag
import  config
import  logger
from    abc                                import ABC, abstractmethod
from    google                             import genai

client = genai.Client()

chunk_collection = rag.database_init()

llm = init_chat_model(
    "gemini-3.1-flash-lite",
    model_provider="google_genai",
)

class Agent():
    def response(state: config.State) -> str:
        print(f"----AGENT {state.choosed_agent} sees following state before response: {state.state}.")
        print(f"----AGENT {state.choosed_agent} sees following ReAct history as a context: {PromptVariables.current_ReAct_history}.")      
        prompt = state["messages"][-1]

        agent_llm - llm.with_structured_output(self.agent_response)

        response = agent_llm.invoke([
            {
                "role": "system",
                "content": self.agent_instruction
            },
            {"role": "user", "content": f"CONVERSATION SUMMARY: {state["conv_summary"]}. MESSAGES: {state["messages"]}, PREVIOUS THOUGHTs: {state["previous_thought"]}. RAG CONTEXT: {state["rag"]}. INTERVIEW AGENT STATE: {state["interview_state"]}. PLANNER AGENT STATE: {state["planner_state"]}. TRACKING AGENT STATE: {state["tracking_state"]}. CURRENT DATE: {state["current_date"]}. USER PROMPT: {state["messages"][-1]}"}
        ])
        print(f"----AGENT {state.choosed_agent} response: ", response.content)
        # print(f"----AGENT response process used {interaction.usage.total_output_tokens} tokens.")
        if response.update_state == True:
            match state.choosed_agent:
                case "interview_agent":
                    self.extract_state()
                case "planner_agent":
                    self.extract_state(generated_answer=response.content)
                case "tracking_agent":
                    self.extract_state(generated_answer=response.content)
        return response.content

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
    return {"choosed_agent": decision.choosed_agent}

class InterviewAgent(Agent):
    def __init__(self):
        self.agent_response = config.InterviewResponse()
        self.agent_instruction = config.llm["interview_agent_instruction"]
        self.agent_extraction = config.InterviewExtraction()

    def interview_agent(state: config.State):
        interview_response = response(state=state)
        return interview_response

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

    def planner_agent(state: config.State):
        planner_response = response(state=state)
        return planner_response

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

    def tracking_agent(state: config.State):
        tracking_response = response(state=state)
        return tracking_response

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