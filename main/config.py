from pydantic import BaseModel
from typing import Optional, Literal

agents = {
    'orchestrator': 'Analyses user needs and routes to the appropriate agent',
    'interview_agent': 'Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': 'Breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': 'Monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

database = {
    "THRESHOLD": 0.3,
}

class Task(BaseModel):
    name: str
    deadline: str = ""

class InterviewState(BaseModel):
    goal: str = ""
    region: str = ""
    deadline: str = ""
    technologies: str = ""
    requirements: str = ""
    working_style: str = ""
    extra_content: str = ""
    
class PlannerState(BaseModel):
    tasks: list[Task] = []
    extra_content: str = ""

class TrackingState(BaseModel):
    task_name: str
    status: Literal["done", "in_progress", "not_started"]
    justification: str = ''
    confidence: float = 0.0

class InterviewAgentResponse(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["switch_agent", "current_date", "user_location"]] = None
    state_updates: Optional[InterviewState] = None

class PlannerAgentResponse(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["switch_agent", "current_date", "user_location"]] = None
    state_updates: Optional[PlannerState] = None

class OrchestratorResponse(BaseModel):
    agent: Literal["interview_agent", "planner_agent"]
    justification: str = ""

class TrackingAgentResponse(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["get_commit_diff", "switch_agent"]] = None
    tool_input: Optional[str] = None
    state_updates: Optional[list[TrackingState]] = None

ORCHESTRATOR_RESPONSE_DESCRIPTION = """
You must respond in JSON format with the following fields:
- "agent": which agent should respond next, either "interview_agent" or "planner_agent"
- "justification": short explanation of why you chose this agent. Can be empty string if obvious.
"""

TRACKING_AGENT_RESPONSE_DESCRIPTION = """
You must respond in JSON format with the following fields:
- "response_type": one of "thought", "action", or "answer"
    - "thought": use when reasoning about which commits to inspect, how they relate to planned tasks, or evaluating confidence in your assessment
    - "action": use when calling a tool to inspect commit details
    - "answer": use when delivering your final progress assessment to the user
- "content": your actual response text — reasoning in thought, tool call description in action, or summary assessment in answer
- "tool": only when response_type is "action", one of: "get_commit_diff" to inspect actual code changes for a specific commit, "switch_agent" if a different agent should handle the current request. Otherwise null.
- "tool_input": only when response_type is "action" and tool is "get_commit_diff" — provide the commit SHA you want to inspect. Otherwise null.
- "state_updates": only when response_type is "answer" — provide a list of task assessments, one per planned task. Otherwise null. Each assessment contains:
    - "task_name": exact name of the task from the project plan
    - "status": one of "done", "in_progress", or "not_started" based on commit evidence
    - "justification": brief explanation of why you assigned this status, referencing specific commits where possible
    - "confidence": float between 0.0 and 1.0 indicating how confident you are in this assessment — lower when commit messages are vague or diffs weren't inspected, higher when code changes clearly match task requirements
"""

def format_agents_context():
    return "\n".join([f"- {name}: {description}" for name, description in agents.items()])

REACT_INSTRUCTIONS = """Work in ReAct workflow. You MUST follow this exact sequence for every response:
1. First always send a thought message — use it to plan what you need, decide whether to call a tool, and determine if you have enough information to answer.
2. Then either an action message (if you need a tool) or an answer message.
Never send an answer without a preceding thought in the same turn.
Response type field values: thought — reasoning step, action — tool call, answer — final response to user.
User response messages will start with 'USER PROMPT:' — everything else is a message agents have generated."""

llm = {
    "model": "gemini-3.1-flash-lite",
    
    "orchestrator_instruction": f"""You are an orchestrator project management AI-Agent. Your responsibility is to {agents['orchestrator']}.
    
There are {len(agents)} agents in this app:
{format_agents_context()}

Interview agent must gather all information described in the state_updates section of {INTERVIEW_AGENT_RESPONSE_DESCRIPTION} before switching to planner agent.

Your answers will be JSON structured. Here is the description of available fields: {ORCHESTRATOR_RESPONSE_DESCRIPTION}
User response messages will start with 'USER PROMPT:' — everything else is a message agents have generated.""",

    "interview_agent_instruction": f"""You are a project management agent. Your responsibility is to {agents['interview_agent']}.

There are {len(agents)} agents in this app:
{format_agents_context()}

{REACT_INSTRUCTIONS}
Your answers will be JSON structured. Here is the description of available fields: {INTERVIEW_AGENT_RESPONSE_DESCRIPTION}""",

    "planner_agent_instruction": f"""You are a project management agent. Your responsibility is to {agents['planner_agent']}.

There are {len(agents)} agents in this app:
{format_agents_context()}

{REACT_INSTRUCTIONS}
Your answers will be JSON structured. Here is the description of available fields: {PLANNER_AGENT_RESPONSE_DESCRIPTION}""",

    "tracking_agent_instruction": f"""You are a project management agent. Your responsibility is to {agents['tracking_agent']}.

There are {len(agents)} agents in this app:
{format_agents_context()}

You receive a list of commits with messages, authors and timestamps. For each planned task, determine its status based on available commit data. Use get_commit_diff tool when you need to inspect actual code changes for a specific commit. When producing your final answer, populate the assessments field with per-task status, justification and confidence score.

{REACT_INSTRUCTIONS}
Your answers will be JSON structured. Here is the description of available fields: {TRACKING_AGENT_RESPONSE_DESCRIPTION}""",
}