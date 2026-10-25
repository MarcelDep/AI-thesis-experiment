from pydantic import BaseModel, Field
from typing import Optional, Literal, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

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
    last_diff: str = ""
    commits_msg_sha: list[CommitsMsgSha] = []

class TrackingShaExtraction(BaseModel):
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None

# Langgraph classes - responses
class RouterResponse(BaseModel):
    choosed_agent: Literal["interview_agent", "planner_agent", "tracking_agent"] = Field(
        ...,
        description="""
        Choose which agent should respond next, one of following agents:
            'interview_agent': Interviews user to define project goals, technologies, working style and requirements',
            'planner_agent': breaks project into structured tasks and sprint plans based on interview data',
            'tracking_agent': monitors GitHub commits and assesses whether planned tasks are correctly implemented',
        """
    )
    justification: str = Field(..., description="Short explanation of why you chose this agent.")

class AgentResponse(BaseModel):
    content: str = Field(..., description="Your actual response text")
    update_state: bool = Field(..., description="Ture or False - set True if state should be updated with new information, False if everything is up to date")

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
                "status" - status of the task (not_started by deafult)          
    """)

class TrackingExtraction(BaseModel):
    commits_msg_sha: list[CommitsMsgSha] = Field(..., description="List of objects, each with: commit_message - commit message, and commit_sha - their SHAs")

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
    rag: str
    current_date: str
    conv_summary: Annotated[list, add_messages]
    choosed_agent: str
    update_state: bool
    interview_state: InterviewState
    planner_state: PlannerState
    tracking_state: TrackingState
    github_variables: GithubVariables