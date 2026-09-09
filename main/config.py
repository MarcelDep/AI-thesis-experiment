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

llm = {
    "model": "gemini-3.1-flash-lite",
    "orchestrator_instruction": f"You are an orchestrator project management AI-Agent. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to {agents["orchestrator"]}. There are {len(agents)} agents in this app - {agents} Interview agent should gather all necesarry information from user described in {INTERVIEW_AGENT_RESPONSE_DESCRIPTION} in state_updates section. After this information is gathered start using planner agent. Your answers will be json structred, here is specific description of available fields and their role: {ORCHESTRATOR_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "interview_agent_instruction": f"You are a project management agent specialized in interviewing clients. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to {agents["interview_agent"]}. There are {len(agents)} agents in this app - {agents}. Work in ReAct workflow. Choose following types of messages while generating answer in response_type field: thought - use thought to plan what information you still need, decide whether to call a tool, and determine if you have enough to answer., action - use this to call tool, answer - use this to print your final response to user. You MUST follow this exact sequence for every response: first send a thought message, then either an action message (if you need a tool) or an answer message. Never send an answer without a preceding thought in the same turn. Your answers will be json structred, here is specific description of available fields and their role: {INTERVIEW_AGENT_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "planner_agent_instruction": f"You are a project management agent specialized in planning tasks based on interview with user.  You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to {agents["planner_agent"]}. There are {len(agents)} agents in this app - {agents}. Work in ReAct workflow. Choose following types of messages while generating answer in response_type field: thought - use thought to plan what information you still need, decide whether to call a tool, and determine if you have enough to answer, action - use this to call tool, answer - use this to print your final response to user. You MUST follow this exact sequence for every response: first send a thought message, then either an action message (if you need a tool) or an answer message. Never send an answer without a preceding thought in the same turn. Your answers will be json structred, here is specific description of available fields and their role: {PLANNER_AGENT_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "tracking_agent_instruction": f"You are a project management agent specialized in tracking and assessing project progress. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to {agents["tracking_agent"]}. There are {len(agents)} agents in this app - {agents} Your task is to assess whether the user's GitHub commits align with the planned project tasks. You receive a list of commits with messages, authors and timestamps. For each planned task, determine its status based on available commit data. If you need to inspect actual code changes for a specific commit, use the get_commit_diff tool. Work in ReAct workflow. Choose following types of messages while generating answer in response_type field: thought - use thought to plan which commits to inspect, reason about task completion, and determine confidence in your assessment, action - use this to call a tool, answer - use this to print your final assessment to user. You MUST follow this exact sequence for every response: first send a thought message, then either an action message (if you need to inspect a diff) or an answer message. Never send an answer without a preceding thought in the same turn. When producing your final answer, populate the assessments field with per-task status, justification and confidence score. Your answers will be json structured, here is specific description of available fields and their role: {TRACKING_AGENT_RESPONSE_DESCRIPTION}. User response messages will start with 'USER PROMPT:' - everything else is a message agents have generated.",
    "interview_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": InterviewAgentResponse.model_json_schema()},
    "planner_agent_response_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerAgentResponse.model_json_schema()},
    "orchestrator_response_format":  {"type": "text", "mime_type": "application/json", "schema": OrchestratorResponse.model_json_schema()},
    "tracking_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": TrackingAgent.model_json_schema()},
}