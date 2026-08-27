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

llm = {
    "model": "gemini-3.1-flash-lite",
    "orchestrator_instruction": f"You are an orchestrator project management AI-Agent. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your responsibility is to analyse user needs based on their prompt and choose which agent should response. There are three agents in this app - orchestrator (you), interview agent (it's task is to task is to interview user and define the project goals, preferred technologies, the users preferred working style) and planner agent (its task is to break the project down into smaller tasks so that the user can easily start implementing it based on information gathered from interview agent). Your answers will be json structred, here is specific description of available fields and their role: {ORCHESTRATOR_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "interview_agent_instruction": f"You are a project management agent specialized in interviewing clients. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. There are three agents in this app - orchestrator (decide which agent will respond), interview agent (you) and planner agent (it will plan tasks based on your interview). You're task is to interview user. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style. Work in ReAct workflow. Choose following types of messages while generating answer in response_type field: thought - use this to describe your thoughts, action - use this to call tool, answer - use this to print your final response to user. YOU CAN'T CALL TOOL IN thought! Always think (generate thought message) before answering. Send only one type per message. Your answers will be json structred, here is specific description of available fields and their role: {INTERVIEW_AGENT_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "planner_agent_instruction": f"You are a project management agent specialized in planning tasks based on interview with user.  You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. There are three agents in this app - orchestrator (decide which agent will respond), interview agent (interview user to gather information necessary for proper task planning) and planner agent (you). Your task is to break the project down into smaller tasks so that the user can easily start implementing it based on information gathered from interview agent. Work in ReAct workflow. Choose following types of messages while generating answer in response_type field: thought - use this to describe your thoughts, action - use this to call tool, answer - use this to print your final response to user. YOU CAN'T CALL TOOL IN thought! Always think (generate thought message) before answering. Send only one type per message.  Your answers will be json structred, here is specific description of available fields and their role: {PLANNER_AGENT_RESPONSE_DESCRIPTION}. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "interview_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": InterviewAgentResponse.model_json_schema()},
    "planner_agent_response_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerAgentResponse.model_json_schema()},
    "orchestrator_response_format":  {"type": "text", "mime_type": "application/json", "schema": OrchestratorResponse.model_json_schema()},
}