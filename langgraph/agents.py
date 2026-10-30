import tools
import config
import schemas
from datetime import date
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver  
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import AIMessage, HumanMessage, SystemMessage

thread_config = {"configurable": {"thread_id": "1"}}

interview_agent_tools = [tools.user_location,]
planner_agent_tools = [tools.user_location,]
tracking_agent_tools = [tools.get_commit_messages, tools.get_commit_diff, tools.modify_tasks_status]

llm = config.llm

def extract_interview_state(state: schemas.State) -> schemas.InterviewState:
    current = state["interview_state"]
    user_text = state["messages"][-1].content

    extract_llm = llm.with_structured_output(schemas.InterviewExtraction)
    extracted = extract_llm.invoke([
        {"role": "system", "content": "You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."},
        {"role": "user", "content": f"User prompt from which you're supposed to extract info: {user_text}"},
    ])

    new_values = {k: v for k, v in extracted.model_dump().items() if v.strip()}
    updated = current.model_copy(update=new_values)
    print(f"----EXTRACTION of interview_agent state: {updated.model_dump()}")
    return updated

class Agent():
    def response(self, state: schemas.State):
        print(f"----MESSEGES: {state['messages']}")
        prompt = state["messages"][-1]
        print(f'----AGENT {state["choosed_agent"]} will respond')
        result = self.agent.invoke(
            {"messages": [prompt], **state,}, config=thread_config,
        )
        print(f"----RESULT {result}")
        structured_output = result.get("structured_response")
        print(f'----AGENT {state["choosed_agent"]} answer: {structured_output}')
        response = {
            "messages": [AIMessage(content=structured_output.content)],
            "update_state": structured_output.update_state,
        }

        if state["choosed_agent"] == "tracking_agent":
            for key in ["tracking_state", "planner_state"]:
                if result[key] != state[key]:
                    response[key] = result[key]

        return response

    def extract_state(self):
        ...

def router(state: schemas.State):
    update = {}
    interview_agent_state = state.get("interview_state")
    planner_agent_state = state.get("planner_state")
    tracking_agent_state = state.get("tracking_agent")

    print(f"----INTERVIEW AGENT TYPE: {type(interview_agent_state)}")

    if any(value == "" for value in interview_agent_state.model_dump().values()):
        interview_state = extract_interview_state(state)
        update["interview_state"] = interview_state

    system_prompt = (
        config.LLM_CONFIG["router_instruction"] + 
        f"\nInformation that interview agent gathered: {interview_agent_state}"
        f"\nPlans that planner agent has made: {planner_agent_state}"
        f"\nTracking agent state: {tracking_agent_state}"
    )

    router_llm = llm.with_structured_output(schemas.RouterResponse)

    messages = [
        {"role": "system", "content": system_prompt}
    ] + state["messages"]

    decision = router_llm.invoke(messages)
    print(f"----ROUTER picked {decision.choosed_agent} to respond because {decision.justification}")
    update["choosed_agent"] = decision.choosed_agent
    return update

class InterviewAgent(Agent):
    @dynamic_prompt
    def dynamic_system_prompt(request) -> str:
        interview_agent_state = request.state.get("interview_state")
        system_prompt = config.LLM_CONFIG["interview_agent_instruction"] + f"\nInformation you've gathered by now: {interview_agent_state}.\nCurrent date:{date.today()}"
        return system_prompt

    def __init__(self):
        self.agent = create_agent(
            model=llm, 
            tools=interview_agent_tools,
            middleware=[self.dynamic_system_prompt],
            response_format=ToolStrategy(schemas.AgentResponse),
            checkpointer=InMemorySaver(),
            state_schema=schemas.State,
        )

    def extract_state(self, state: schemas.State):
        print(f'----AGENT {state["choosed_agent"]} response will be extracted to its state')
        prompt = state["messages"][-1]
        extract_llm = llm.with_structured_output(schemas.InterviewExtraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"User prompt from which you're supposed to extract info form: {prompt}."}
        ])

        print(f"----EXTRACTION of {state['choosed_agent']} state: {response.model_dump()}")
        return {"interview_state": schemas.InterviewState(**response.model_dump())}

class PlannerAgent(Agent):
    @dynamic_prompt
    def dynamic_system_prompt(request) -> str:
        interview_agent_state = request.state.get("interview_state")
        planner_agent_state = request.state.get("planner_state")
        system_prompt = config.LLM_CONFIG["planner_agent_instruction"] + f"\nInformation that interview agent gathered: {interview_agent_state}.\nPlans you've made by far: {planner_agent_state}.\nCurrent date:{date.today()}"
        return system_prompt

    def __init__(self):
        self.agent = create_agent(
            model=llm, 
            tools=planner_agent_tools,
            middleware=[self.dynamic_system_prompt],
            response_format=ToolStrategy(schemas.AgentResponse),
            checkpointer=InMemorySaver(),
            state_schema=schemas.State,
            )

    def extract_state(self, state: schemas.State):
        print(f"----MESSEGES: {state['messages']}")
        generated_answer = state["messages"][-1]
        print(f'----AGENT {state["choosed_agent"]} response will be extracted to its state')
        prompt = state["messages"][-2]
        extract_llm = llm.with_structured_output(schemas.PlannerExtraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"CURRENT PLANNER STATE: {state['planner_state']}. Agent answer you're supposed to extract info form - {generated_answer}."}
        ])

        print(f"----EXTRACTION of {state['choosed_agent']} state: {response.model_dump()}")
        return {"planner_state": schemas.PlannerState(general_plan=response.general_plan, specific_plan=response.specific_plan)}

class TrackingAgent(Agent):
    @dynamic_prompt
    def dynamic_system_prompt(request) -> str:
        planner_agent_state = request.state.get("planner_state")
        system_prompt = config.LLM_CONFIG["tracking_agent_instruction"] + f"\nPlans that planner agent has made: {planner_agent_state}.\nCurrent date:{date.today()}"
        return system_prompt

    def __init__(self):
        self.agent = create_agent(
            model=llm, 
            tools=tracking_agent_tools,
            middleware=[self.dynamic_system_prompt],
            response_format=ToolStrategy(schemas.AgentResponse),
            checkpointer=InMemorySaver(),
            state_schema=schemas.State,
            )

    def extract_state(self, state: schemas.State,):
        print(f'----AGENT {state["choosed_agent"]} response will be extracted to its state')
        prompt = state["messages"][-1]
        generated_answer = state["messages"][-1]
        extract_llm = llm.with_structured_output(schemas.TrackingExtraction)

        response = extract_llm.invoke([
            {
                "role": "system",
                "content": f"You are a data extraction assistant. Extract only the fields requested. Do not infer, expand, or add context. Return empty string for unknown fields."
            },
            {"role": "user", "content": f"Agent answer and tool output (if empty - none tool was called) from which you're supposed to extract info form: AGENT ANSWER - {generated_answer} PROMPT - {prompt}"}
        ])

        print(f"----EXTRACTION of {state['choosed_agent']} state: {response.model_dump()}")
        return {"tracking_state": state["tracking_state"].model_copy(update={"commits_msg_sha": response.commits_msg_sha})}

def summarize(state: schemas.State) -> str:
    response = llm.invoke([
        {
            "role": "system",
            "content": f"You are an summarization agent. Your task is to summarize conversation based on its history. Your summary should be rather short. If CURRENT SUMMARY isn't empty then continue this summary instead generating new one. Just generate a contuniuation of it. If summary is empty then make one."
        },
        {"role": "user", "content": f'CONVERSATION HISTORY: {state["messages"]},  CURRENT SUMMARY: {state["conv_summary"]}'}
    ])
    return {"conv_summary": response.content}