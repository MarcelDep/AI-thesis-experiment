from pydantic import BaseModel
from typing import Optional, Literal
from typing_extensions import TypedDict

llm = init_chat_model(
    "gemini-3.1-flash-lite",
    model_provider="google_genai",
)

agents_characteristic = {
    'router': '"router" analyses user needs and routes to the appropriate agent',
    'interview_agent': '"interview_agent" Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': '"planner_agent" breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': '"tracking_agent" monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

tools_info = {
    "user_location": "'user_location' returns user location.",
    "switch_agent": "'switch_agent' suggests router to swich agent that different agent than you should responde to user prompt. If switch_agent was called in previous ReAct history DON'T call it again, even if user said so.",
    "get_commit_diff": "'get_commit_diff' returns chosen commit diff - shows you what changes specifically user has made in picked commit. Before using this tool you have to gather SHA of commits you want to diff and set them as base_sha and head_sha parameters.",
    "get_commit_messages": "'get_commit_messages' returns list of commit messages and their sha of repo given by user. You won't see user credintials so dont wait for them.",
    "modify_tasks_status": "'modify_tasks_status' updates statuses of tasks in the plan based on the commit messages and the last fetched commit diff. Call it AFTER get_commit_messages and/or get_commit_diff when you want to record progress. Takes no parameters."
}

interview_agent_tools = ['user_location', 'switch_agent',]
planner_agent_tools = ['user_location', 'switch_agent',]
tracking_agent_tools = ['switch_agent', 'get_commit_messages', 'get_commit_diff',]

database = {
    "THRESHOLD": 0.3,
}

# Datatype
class Task(BaseModel):
    task_id: int
    task_name: str
    deadline: str = ""
    status: Literal["done", "in_progress", "not_started"] = 'not_started'

class GeneralPlan(BaseModel):
    phase_id: int
    phase_name: str
    description: str
    deadline: str

class SpecificTask(BaseModel):
    phase_id: int
    phase_name: str
    tasks: list[Task]

class CommitsMsgSha(BaseModel):
    commit_message: str = ''
    commit_sha: str = ''

class GithubVariables(BaseModel):
    repo: str = ""
    token: str = ""
    owner: str = ""

# Extraction
class TrackingExtraction(BaseModel):
    task_id: list[int]
    status: list[Literal["done", "in_progress", "not_started"]]

class TrackingShaExtraction(BaseModel):
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None

# Langgraph classes

class RouterResponse(BaseModel):
    choosed_agent: Literal["interview_agent", "planner_agent", "tracking_agent"] = Field(
        ...,
        description=f"Choose which agent should respond next, one of following agents {[agent for agent in agents_characteristic.keys() if agent != 'orchestrator']}"
    )
    justification: str = Field(..., description="Short explanation of why you chose this agent.")

class AgentResponse(BaseModel):
    thought: str = Field(..., description="Reason about what to do next - thinking proces before final response or action.")
    response_type: Literal["action", "answer"] = Field(...,
        description="""Pick one response type: 
            "action": use when calling a tool
            "answer": use when responding directly to the user"""
    )
    tool: Optional[str] = Field(None, description="...")
    content: str = Field(..., description="Your actual response text - answer to user or action.")
    update_state: Literal[True, False] = Field(..., description="Ture or False - set True if state should be updated with new information, False if everything is up to date")

class InterviewResponse(AgentResponse, BaseModel):
    tool: Optional[Literal["switch_agent", "user_location",]] = Field(...,
        description=f"{[tools_info[tool] for tool in interview_agent_tools]}"
    )

class PlannerResponse(AgentResponse, BaseModel):
    tool: Optional[Literal["switch_agent", "user_location",]] = Field(...,
        description=f"{[tools_info[tool] for tool in planner_agent_tools]}"
    )

class TrackingResponse(AgentResponse, BaseModel):
    tool: Optional[Literal["get_commit_diff", "switch_agent", "get_commit_messages",]] = Field(...,
        description=f"{[tools_info[tool] for tool in tracking_agent_tools]}"
    )

class InterviewExtraction(BaseModel):
    goal: str = Field(..., description="What the user wants to build")
    region: str = Field(..., description="Region where project would be deplyed in")
    deadline: str = Field(..., description="Project deadline")
    technologies: str = Field(..., description="Preferred tech stack")
    requirements: str = Field(..., description="Specific project requirements")
    working_style: str = Field(..., description="How the user prefers to work e.g. scrum or kanban.")

class PlannerExtraction(BaseModel):
    general_plan: list[GeneralPlan] = Field(..., description="""
        list of objects, each with:
            "phase_id" - id of phase (general plan step)
            "phase_name" - name of this phase
            "description" - short description of this phase
            "deadline" - when this phase should end
    """
    )
    specific_plan: list[SpecificTask] = Field(..., description="""
        list of objects, each with:
            "phase_id" - id of phase specific task belong to
            "sub_phase_name" - name of this phase inside general phase
            "tasks" - list of Task object, each containt:
                "task_id" - uniqe id of task for every phase
                "task_name" - name of the task
                "deadline" - when this task should ended
                "status" - status of the task          
    """)

class TrackingExtraction(BaseModel):
    commits_msg_sha: list[CommitsMsgSha] = Field(..., description="List of ibjects, each with: commit_message - commit message, and commit_sha - their SHAs")

class TaskStateUpdate(BaseModel):
    task_id: list[int] = Field(..., description="List of id of tasks where status should be changed")
    status: list[Literal["done", "in_progress", "not_started"]] = Field(..., description="New statuses for tasks where status should be changed")

class TrackingShaExtraction(BaseModel):
    base_sha: Optional[str] = Field(..., description="SHA of base commit to compare")
    head_sha: Optional[str] = Field(..., description="SHA of head commit to compare")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    previous_thought: Annotated[list, add_messages]
    rag: str
    current_date: str
    conv_summary: str
    message_type: str
    choosed_agent: str
    interview_state: InterviewState()
    planner_state: PlannerState()
    tracking_state: TrackingState()
    github_variables: GithubVariables()

REACT_INSTRUCTIONS = """Work in ReAct workflow. You MUST follow this exact sequence for every response:
1. ALWAYS fill a thought field in your response — use it to plan what you need, decide whether to call a tool, and determine if you have enough information to answer.
2. (Optional) An action message (if you need a tool) 
3. An answer message AFTER thought - final response that will be shown to user.
NEVER send an answer without a preceding thought before.
Response type field values: thought — reasoning step, action — tool call, answer — final response to user.
User response messages will start with 'USER PROMPT:' — everything else is a message agents have generated."""

agent_info = {
    "project_description": "You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects.",
    "amount_of_agents": len(agents_characteristic),
    "agents_description": agents_characteristic,
    "ReAct_workflow": REACT_INSTRUCTIONS,
}

interview_agent_info = {
    "agent_description": "You're an interview agent",
    "agent_duties": "You're task is to interview user. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style",
    "tools": [tools_info[tool] for tool in interview_agent_tools],
}

planner_agent_info = {
    "agent_description": "You're a planner agent",
    "agent_duties": "You're task is to plan tasks for user based on information interview_agent gathered from interview with user",
    "tools": [tools_info[tool] for tool in planner_agent_tools],
}

tracking_agent_info = {
    "agent_description": "You're a tracking agent",
    "agent_duties": "You're task is to track user progress - how many tasks did user finished based on planner_agent plan and users code on GitHub",
    "tools": [tools_info[tool] for tool in tracking_agent_tools],
}

router_info = {
    "agent_description": "You're an router.",
    "agent_duties": "Your task is to decide which agent should responde to user prompt",
    "tools": [],
}

additional_orchestrator_info = f"Only switch to other agents from interview_agent when ALL of the fields in interview_state are non-empty strings: goal, technologies, deadline, working_style, requirements. If any of these fields are empty string "", keep using interview_agent regardless of what the conversation suggests. Do not infer that information is gathered from conversation text alone — check the actual state fields."
additional_interview_agent_into = f"When whole infomration in InerviewAgent state is filled, call switch_agent tool. Else, keep askign for missing info untill state is full."
additional_tracking_agent_info = f"If you've requested diff or commit messeges in previous messages in current ReAct history, then don't request it again."

llm = {
    "model": "gemini-3.1-flash-lite",
    "max_output_tokens": 2048,
    "router_instruction": f"{router_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {router_info['agent_duties']}. {additional_orchestrator_info}.",
    "interview_agent_instruction": f"{interview_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {interview_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {interview_agent_info['tools']}. {additional_interview_agent_into}",
    "planner_agent_instruction": f"{planner_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {planner_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {planner_agent_info['tools']}.",
    "tracking_agent_instruction": f"{tracking_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {tracking_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {tracking_agent_info['tools']}.",    
}