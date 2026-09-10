from pydantic import BaseModel
from typing import Optional, Literal

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

class TaskAssessment(BaseModel):
    task_name: str
    status: Literal["done", "in_progress", "not_started"]
    justification: str = ''
    confidence: float = 0.0

class TrackingAgent(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["get_commit_diff", "switch_agent"]] = None
    tool_input: Optional[str] = None
    assessments: Optional[list[TaskAssessment]] = None

INTERVIEW_AGENT_RESPONSE_DESCRIPTION = """
You must respond in JSON format with the following fields:
- "response_type": one of "thought", "action", or "answer"
    - "thought": use when reasoning about what to do next
    - "action": use when calling a tool
    - "answer": use when responding directly to the user
- "content": your actual response text — thought, action reasoning, or answer to user
- "tool": only when response_type is "action", one of: "switch_agent", "current_date", "user_location". Otherwise null.
- "state_updates": when you learn something new about the project this turn, populate the relevant fields. Otherwise null.
    - "goal": what the user wants to build
    - "region": where the user is located
    - "deadline": project deadline
    - "technologies": preferred tech stack
    - "requirements": specific project requirements
    - "working_style": how the user prefers to work
    - "extra_content": anything else relevant that doesn't fit above fields
"""

PLANNER_AGENT_RESPONSE_DESCRIPTION = """
You must respond in JSON format with the following fields:
- "response_type": one of "thought", "action", or "answer"
    - "thought": use when reasoning about what to do next
    - "action": use when calling a tool
    - "answer": use when responding directly to the user
- "content": your actual response text — thought, action reasoning, or answer to user
- "tool": only when response_type is "action", one of: "switch_agent", "current_date", "user_location". Otherwise null.
- "state_updates": when you produce or update the task breakdown, populate the relevant fields. Otherwise null.
    - "tasks": list of task objects, each with "name" (task name) and "deadline" (task deadline, empty string if unknown)
    - "extra_content": anything else relevant about the plan
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

ORCHESTRATOR_RESPONSE_DESCRIPTION = """
You must respond in JSON format with the following fields:
- "agent": which agent should respond next, either "interview_agent" or "planner_agent"
- "justification": short explanation of why you chose this agent. Can be empty string if obvious.
"""

REACT_INSTRUCTIONS = """Work in ReAct workflow. You MUST follow this exact sequence for every response:
1. First always send a thought message — use it to plan what you need, decide whether to call a tool, and determine if you have enough information to answer.
2. Then either an action message (if you need a tool) or an answer message.
Never send an answer without a preceding thought in the same turn.
Response type field values: thought — reasoning step, action — tool call, answer — final response to user.
User response messages will start with 'USER PROMPT:' — everything else is a message agents have generated."""

agents_characteristic = {
    'orchestrator': 'Analyses user needs and routes to the appropriate agent',
    'interview_agent': 'Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': 'Breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': 'Monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

tools_info = {
    "current_date": "'current_date' returns current date - day, month and year in YYYY-MM-DD format.",
    "user_location": "'user_location' returns user location.",
    "switch_agent": "'switch_agent' suggests orchestrator to swich agent that different agent than you should responde to user prompt.",
    "get_commit_diff": "'get_commit_diff' returns chosen commit diff - shows you what changes specifically user has made in picked commit.",
}

agent_info = {
    "project_description": "You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects.",
    "amount_of_agents": len(agents),
    "agents_description": agents_characteristic,
    "ReAct_workflow": REACT_INSTRUCTIONS,
}

interview_agent_info = {
    "agent_descrition": "You're an interview agent - A project management agent specialized in interviewing clients",
    "agent_duties": "You're task is to interview user. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style.",
    "json_answer_description": INTERVIEW_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info["current_date"], tools_info["user_location"], tools_info["switch_agent"]],
}

planner_agent_info = {
    "agent_descrition": "You're a planner agent.",
    "agent_duties": "You're task is to plan tasks for user based on information interview_agent gathered from interview with user.",
    "json_answer_description": PLANNER_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info["current_date"], tools_info["user_location"], tools_info["switch_agent"]],
}

tracking_agent_info = {
    "agent_descrition": "You're a tracking agent.",
    "agent_duties": "You're task is to track user progress - how many tasks did user finished based on planner_agent plan and users code on GitHub.",
    "json_answer_description": TRACKING_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info["switch_user"], tools_info["get_commit_diff"]],
}

orchiestrator_info = {
    "agent_descrition": "You're an orchestrator.",
    "agent_duties": "You're task is to decide which agent should responde to user prompt.",
    "json_answer_description": ORCHESTRATOR_RESPONSE_DESCRIPTION,
    "tools": [],
}

llm = {
    "model": "gemini-3.1-flash-lite",
    "orchestrator_instruction": f"You are an orchestrator project management AI-Agent. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to analyse user needs based on their prompt and choose which agent should response. There are three agents in this app - orchestrator (you), interview agent (it's task is to task is to interview user and define the project goals, preferred technologies, the users preferred working style) and planner agent (its task is to break the project down into smaller tasks so that the user can easily start implementing it based on information gathered from interview agent). Interview agent should gather all necesarry information from user described in {INTERVIEW_AGENT_RESPONSE_DESCRIPTION} in state_updates section. After this information is gathered start using planner agent. Your answers will be json structred, here is specific description of available fields and their role: {ORCHESTRATOR_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "interview_agent_instruction": f"{interview_agent_info["agent_descrition"]}. {agent_info["project_description"]}. There are {agent_info["amount_of_agents"]} agents in this app - {agent_info["agents_description"]}. {interview_agent_info["agent_duties"]}. {agent_info["ReAct_workflow"]} You can use following tools: {interview_agent_info["tools"]} {interview_agent_info["json_answer_description"]}",
    "planner_agent_instruction": f"{planner_agent_info["agent_descrition"]}. {agent_info["project_description"]}. There are {agent_info["amount_of_agents"]} agents in this app - {agent_info["agents_description"]}. {planner_agent_info["agent_duties"]}. {agent_info["ReAct_workflow"]} You can use following tools: {planner_agent_info["tools"]} {planner_agent_info["json_answer_description"]}",
    "tracking_agent_instruction": f"{tracking_agent_info["agent_descrition"]}. {agent_info["project_description"]}. There are {agent_info["amount_of_agents"]} agents in this app - {agent_info["agents_description"]}. {tracking_agent_info["agent_duties"]}. {agent_info["ReAct_workflow"]} You can use following tools: {tracking_agent_info["tools"]} {tracking_agent_info["json_answer_description"]}",
    "interview_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": InterviewAgentResponse.model_json_schema()},
    "planner_agent_response_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerAgentResponse.model_json_schema()},
    "orchestrator_response_format":  {"type": "text", "mime_type": "application/json", "schema": OrchestratorResponse.model_json_schema()},
    "tracking_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": TrackingAgent.model_json_schema()},
}