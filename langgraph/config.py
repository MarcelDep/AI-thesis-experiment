from pydantic import BaseModel
from typing import Optional, Literal
from typing_extensions import TypedDict

llm = init_chat_model(
    config.llm["model"],
    model_provider=config.llm["model_provider"],
)

agents_characteristic = {
    'router': '"router" analyses user needs and routes to the appropriate agent',
    'interview_agent': '"interview_agent" Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': '"planner_agent" breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': '"tracking_agent" monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

interview_agent_tools = [tools.user_location,]
planner_agent_tools = [tools.user_location,]
tracking_agent_tools = [tools.get_commit_messages, tools.get_commit_diff, tools.modify_tasks_status]

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

class InterviewState(BaseModel):
    goal: str = ""
    region: str = ""
    deadline: str = ""
    technologies: str = ""
    requirements: str = ""
    working_style: str = ""
    
class PlannerState(BaseModel):
    general_plan: list[GeneralPlan] = []
    specific_plan: list[SpecificTask] = []

class TrackingState(BaseModel):
    commits_msg_sha: list[CommitsMsgSha] = []

class TrackingShaExtraction(BaseModel):
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None

# Langgraph classes - responses
class RouterResponse(BaseModel):
    choosed_agent: Literal["interview_agent", "planner_agent", "tracking_agent"] = Field(
        ...,
        description=f"Choose which agent should respond next, one of following agents {[agent for agent in agents_characteristic.keys() if agent != 'orchestrator']}"
    )
    justification: str = Field(..., description="Short explanation of why you chose this agent.")

class AgentResponse(BaseModel):
    thought: str = Field(..., description="Reason about what to do next - thinking proces before final response or action.")
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

# Langgraph classes - extraction
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

class TaskStatusUpdate(BaseModel):
    phase_id: int = Field(..., description="phase_id of the phase the task belongs to")
    task_id: int = Field(..., description="task_id of the task inside that phase")
    status: Literal["in_progress", "done"] = Field(..., description="New status, only if the evidence clearly shows it")

class TaskStatusUpdates(BaseModel):
    updates: list[TaskStatusUpdate] = Field([], description="Only tasks you are sure about. Empty list if none.")

# State
class State(TypedDict):
    messages: Annotated[list, add_messages]
    previous_thought: Annotated[list, add_messages]
    rag: str
    current_date: str
    conv_summary: Annotated[list, add_messages]
    message_type: str
    next_node: str
    interview_state: InterviewState()
    planner_state: PlannerState()
    tracking_state: TrackingState()
    github_variables: GithubVariables()

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
    "model_provider": "google_genai",
    "max_output_tokens": 2048,
    "router_instruction": f"{router_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {router_info['agent_duties']}. {additional_orchestrator_info}.",
    "interview_agent_instruction": f"{interview_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {interview_agent_info['agent_duties']}. {additional_interview_agent_into}",
    "planner_agent_instruction": f"{planner_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {planner_agent_info['agent_duties']}.",
    "tracking_agent_instruction": f"{tracking_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {tracking_agent_info['agent_duties']}.",    
}