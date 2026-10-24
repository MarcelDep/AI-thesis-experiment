import tools
import config
import schemas
from   langchain.agents import create_agent

interview_agent_tools = [tools.user_location,]
planner_agent_tools = [tools.user_location,]
tracking_agent_tools = [tools.get_commit_messages, tools.get_commit_diff, tools.modify_tasks_status]

llm = config.llm

class Agent():
    def response(self, agent, state):
        result = self.agent.invoke(state)
        structured_output = result.get("structured_response")

        return {
            "messages": structured_output["content"],
            }

    def extract_state(self):
        ...

def router(state: schemas.State):
    prompt = state["messages"][-1]
    conv_history = state["messages"]
    previous_thought = state["previous_thought"]
    interview_state = state["interview_state"]
    planner_state = state["planner_state"]
    tracking_state = state["tracking_state"]

    router_llm = llm.with_structured_output(schemas.RouterResponse)

    decision = router_llm.invoke([
        {
            "role": "system",
            "content": config.LLM_CONFIG.router_instruction
        },
        {"role": "user", "content": f"USER PROMPT: {prompt}. CONVERSATION HISTORY: {conv_history}. PREVIOUS THOUGHTs: {previous_thought}. INTERVIEW AGENT STATE: {interview_state}. PLANNER AGENT STATE: {planner_state}. TRACKING AGENT STATE: {tracking_state}"}
    ])

    print(f"----ROUTER picked {decision.choosed_agent} to respond because {decision.justification}.")
    return {"choosed_agent": decision.choosed_agent}

class InterviewAgent(Agent):
    def __init__(self):
        self.agent_instruction = config.LLM_CONFIG["interview_agent_instruction"]
        self.agent_extraction = schemas.InterviewExtraction()
        self.agent_tools = interview_agent_tools
        self.agent_model = config.LLM_CONFIG["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=schemas.AgentResponse)

    def extract_state(self, state: schemas.State):
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
        self.agent_instruction = config.LLM_CONFIG["planner_agent_instruction"]
        self.agent_extraction = schemas.PlannerExtraction()
        self.agent_tools = planner_agent_tools
        self.agent_model = config.LLM_CONFIG["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=schemas.AgentResponse)

    def extract_state(self, state: schemas.State, generated_answer: str,):
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
        self.agent_instruction = config.LLM_CONFIG["tracking_agent_instruction"]
        self.agent_extraction = schemas.TrackingExtraction()
        self.agent_tools = tracking_agent_tools
        self.agent_model = config.LLM_CONFIG["model"]
        self.agent = create_agent(
            model=self.agent_model, 
            tools=self.agent_tools,
            system_prompt=self.agent_instruction,
            response_format=schemas.AgentResponse)

    def extract_state(self, state: schemas.State, generated_answer: str):
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
        return {"tracking_state"["last_diff"]: response.content}

def summarize(state: config.State) -> str:
    response = llm.invoke([
        {
            "role": "system",
            "content": f"You are an summarization agent. Your task is to summarize conversation based on its history. Your summary should be rather short. If CURRENT SUMMARY isn't empty then continue this summary instead generating new one. Just generate a contuniuation of it. If summary is empty then make one."
        },
        {"role": "user", "content": f"CONVERSATION HISTORY: {state["messages"]},  CURRENT SUMMARY: {state["conv_summary"]}"}
    ])
    return {"conv_summary": response.content}