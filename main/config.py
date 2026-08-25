from pydantic import BaseModel
from typing import Optional, Literal

database = {
    "THRESHOLD": 0.3,
}

class Task(BaseModel):
    name: str
    deadline: str = ""

class InterveiwState(BaseModel):
    goal: str = ""
    region: str = ""
    deadline: str = ""
    technologies: str = ""
    requirements: str = ""
    working_style: str = ""
    extra_content: str = ""
    
class PlanningState(BaseModel):
    tasks: list[Task] = []
    extra_content: str = ""

class InterviewAgentResponse(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["switch_agent", "current_date", "user_location"]] = None
    state_updates: Optional[InterveiwState] = None

class PlannerAgentResponse(BaseModel):
    response_type: Literal["thought", "action", "answer"]
    content: str
    tool: Optional[Literal["switch_agent", "current_date", "user_location"]] = None
    state_updates: Optional[PlanningState] = None

class OrchestratorResponse(BaseModel):
    agent: Literal["interview_agent", "planner_agent"]
    justification: str = ""

llm = {
    "model": "gemini-3.1-flash-lite",
    "orchestrator_instruction": "You are an orchestrator project management AI-Agent. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Your response is to analyse user needs based on their prompt and choose which agent should response. There are three agents in this app - orchestrator (you), interview agent (it's task is to task is to interview user and define the project goals, preferred technologies, the users preferred working style) and planner agent (its task is to break the project down into smaller tasks so that the user can easily start implementing it based on information gathered from interview agent). User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated. If you want interview agent to response write 'interviewer_instruction' if planner then 'planer_instruction' after choosing end response with '</end>' key word. If you choose agent add short justification for your decision.",
    "interview_agent_instruction": "You are a project management agent specialized in interviewing clients. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. There are three agents in this app - orchestrator (decide which agent will respond), interview agent (you) and planner agent. You're task is to interview user. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: 'switch_agent' use it if you think that other agent should reponse - this tool will ask orchestrator to make decisipon which agent should response again, 'current_date' to get current date and 'user_location' to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "planer_agent_instruction": "You are a project management agent specialized in planning tasks based on interview with user.  You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. There are three agents in this app - orchestrator (decide which agent will respond), interview agent (interview user to gather information necessary for proper task planning) and planner agent (you). Your task is to break the project down into smaller tasks so that the user can easily start implementing it based on information gathered from interview agent. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: 'switch_agent' use it if you think that other agent should reponse - this tool will ask orchestrator to make decisipon which agent should response again, 'current_date' to get current date and 'user_location' to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location. User response messeges will start with 'USER PROMPT:' - everything else is message, agents have generated.",
    "agent_config": {"stop_sequences": ["</end>", "</answer>", "</thought>", "</action>"]},
    "orchestrator_config": {"stop_sequences": ["</end>"]},
    "interview_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": InterviewAgentResponse.model_json_schema()},
    "planner_agent_response_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerAgentResponse.model_json_schema()},
    "orchestrator_response_format":  {"type": "text", "mime_type": "application/json", "schema": OrchestratorResponse.model_json_schema()},
}