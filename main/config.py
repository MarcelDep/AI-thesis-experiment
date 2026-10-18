from pydantic import BaseModel
from typing import Optional, Literal

agents_characteristic = {
    'orchestrator': '"orchestrator" analyses user needs and routes to the appropriate agent',
    'interview_agent': '"interview_agent" Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': '"planner_agent" breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': '"tracking_agent" monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

tools_info = {
    "user_location": "'user_location' returns user location.",
    "switch_agent": "'switch_agent' suggests orchestrator to swich agent that different agent than you should responde to user prompt. If switch_agent was called in previous ReAct history DON'T call it again, even if user said so.",
    "get_commit_diff": "'get_commit_diff' returns chosen commit diff - shows you what changes specifically user has made in picked commit. Before using this tool you have to gather SHA of commits you want to diff and set them as base_sha and head_sha parameters.",
    "get_commit_messages": "'get_commit_messages' returns list of commit messages and their sha of repo given by user. You won't see user credintials so dont wait for them.",
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

class PromptVariables(BaseModel):
    rag: str = ""
    prompt: str = ""
    current_ReAct_history: list = []

class GithubVariables(BaseModel):
    repo: str = ""
    token: str = ""
    owner: str = ""

# State
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

# Response
class InterviewAgentResponse(BaseModel):
    thought: str
    response_type: Literal["action", "answer"]
    tool: Optional[Literal["switch_agent", "user_location",]] = None
    content: str
    update_state: Literal[True, False]

class PlannerAgentResponse(BaseModel):
    thought: str
    response_type: Literal["action", "answer"]
    tool: Optional[Literal["switch_agent","user_location"]] = None
    content: str
    update_state: Literal[True, False]

class TrackingAgentResponse(BaseModel):
    thought: str
    response_type: Literal["action", "answer"]
    tool: Optional[Literal["get_commit_diff", "switch_agent", "get_commit_messages"]] = None
    content: str
    update_state: Literal[True, False]

class OrchestratorResponse(BaseModel):
    agent: Literal["interview_agent", "planner_agent", "tracking_agent"]
    justification: str = ""

# Extraction
class TrackingGeneralSpecificExtraction(BaseModel):
    task_id: int = 0
    status: Literal["done", "in_progress", "not_started"] = 'not_started'    

class TrackingShaExtraction(BaseModel):
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None

# Datatype
class AgentStates(BaseModel):
    interview_agent_state: InterviewState = InterviewState()
    planner_agent_state: PlannerState = PlannerState() 
    tracking_agent_state: TrackingState = TrackingState()

class SessionVariables(BaseModel):
    conv_summary: str = ""
    answer_history: list = []
    agent_states: AgentStates = AgentStates()
    current_date: str = ""

# Czy da rade jakoś zrobić, żeby zadania w tracking state to były zadania od plannera a w przypadku zmiany zadan w tracking zmianialo sie tez w planner

INTERVIEW_AGENT_RESPONSE_DESCRIPTION = f"""
You must respond in JSON format with the following fields:
- "thought": ALWAYS reason about what to do next
- "update_state": Ture or False - set True if state should be updated with new information, False if everything is up to date
- "response_type": one of "action", or "answer"
    - "action": use when calling a tool
    - "answer": use when responding directly to the user
- "content": your actual response text — thought, action reasoning, or answer to user
- "tool": only when response_type is "action", one of: {[tools_info[tool] for tool in interview_agent_tools]}. Otherwise null.
- "state_updates": ALWAYS populate this field on every "answer" turn with everything you currently know about the project. Never return null on an answer turn. Include all fields you know, even if learned in previous turns — this is a cumulative snapshot, not just what changed this turn. Use empty string "" only for fields where you genuinely have no information yet.
    - "goal": what the user wants to build
    - "region": where the user is located  
    - "deadline": project deadline
    - "technologies": preferred tech stack
    - "requirements": specific project requirements
    - "working_style": how the user prefers to work
"""

PLANNER_AGENT_RESPONSE_DESCRIPTION = f"""
You must respond in JSON format with the following fields:
- "thought": ALWAYS reason about what to do next
- "update_state": Ture or False - set True if state should be updated with new information, False if everything is up to date
- "response_type": one of "action", or "answer"
    - "action": use when calling a tool
    - "answer": use when responding directly to the user
- "content": your actual response text — thought, action reasoning, or answer to user
- "tool": only when response_type is "action", one of: {[tools_info[tool] for tool in planner_agent_tools]}. Otherwise null.
- "state_updates": ALWAYS populate on every "answer" turn with the complete current task list. Never return null or empty tasks on an answer turn where you described any tasks. Every task mentioned in content must appear here structured with name and deadline.
    - general_plan: list of task objects, each with "name" (task name) and "deadline" (task deadline, empty string if unknown), this field is reserved for general purpose tasks
    - specific_plan: list of task objects, each with "name" (task name) and "deadline" (task deadline, empty string if unknown), this field is reserved for specific tasks for each general purpose task
"""

TRACKING_AGENT_RESPONSE_DESCRIPTION = f"""
You must respond in JSON format with the following fields:
- "thought": ALWAYS reason about what to do next
- "update_state": Ture or False - set True if state should be updated with new information, False if everything is up to date
- "response_type": one of "action", or "answer"
    - "action": use when calling a tool to inspect commit details
    - "answer": use when delivering your final progress assessment to the user
- "content": your actual response text — reasoning in thought, tool call description in action, or summary assessment in answer
- "tool": only when response_type is "action", one of: {[tools_info[tool] for tool in tracking_agent_tools]}. Otherwise null.
- "state_updates": only when response_type is "answer" — provide a list of task assessments, one per planned task.
    - "tasks_status": list of tasks statuses containing - task name and task status
    - "commits_msg_sha": list of commit messages and their SHA acquired from GitHub by get_commit_messages function 
    - "base_sha": only when response_type is "action" and tool is "get_commit_diff" — provide the base sha of commit you want to compare. Otherwise null
    - "head_sha": only when response_type is "action" and tool is "get_commit_diff" — provide the head sha of commit you want to compare. Otherwise null
"""

ORCHESTRATOR_RESPONSE_DESCRIPTION = f"""
You must respond in JSON format with the following fields:
- "agent": which agent should respond next, one of following agents {[agent for agent in agents_characteristic.keys() if agent != 'orchestrator']}
- "justification": short explanation of why you chose this agent. Can be empty string if obvious.
"""

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
    "json_answer_description": INTERVIEW_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info[tool] for tool in interview_agent_tools],
}

additional_interview_agent_into = "When all required project information has been gathered (goal, technologies, deadline, working_style, requirements), do NOT send an answer message to the user. Instead, send an action turn calling switch_agent immediately."

planner_agent_info = {
    "agent_description": "You're a planner agent",
    "agent_duties": "You're task is to plan tasks for user based on information interview_agent gathered from interview with user",
    "json_answer_description": PLANNER_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info[tool] for tool in planner_agent_tools],
}

tracking_agent_info = {
    "agent_description": "You're a tracking agent",
    "agent_duties": "You're task is to track user progress - how many tasks did user finished based on planner_agent plan and users code on GitHub",
    "json_answer_description": TRACKING_AGENT_RESPONSE_DESCRIPTION,
    "tools": [tools_info[tool] for tool in tracking_agent_tools],
}

orchiestrator_info = {
    "agent_description": "You're an orchestrator",
    "agent_duties": "You're task is to decide which agent should responde to user prompt",
    "json_answer_description": ORCHESTRATOR_RESPONSE_DESCRIPTION,
    "tools": [],
}

additional_orchestrator_info = f"Only switch to other agents from interview_agent when ALL of the following fields in INTERVIEW AGENT STATE are non-empty strings: goal, technologies, deadline, working_style, requirements. If any of these fields are empty string "", keep using interview_agent regardless of what the conversation suggests. Do not infer that information is gathered from conversation text alone — check the actual state fields."

llm = {
    "model": "gemini-3.1-flash-lite",
    "max_output_tokens": 2048,
    "orchestrator_instruction": f"{orchiestrator_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {orchiestrator_info['agent_duties']}. {additional_orchestrator_info}. {orchiestrator_info['json_answer_description']}",
    "interview_agent_instruction": f"{interview_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {interview_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {interview_agent_info['tools']} {interview_agent_info['json_answer_description']}. {additional_interview_agent_into}",
    "planner_agent_instruction": f"{planner_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {planner_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {planner_agent_info['tools']} {planner_agent_info['json_answer_description']}.",
    "tracking_agent_instruction": f"{tracking_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {tracking_agent_info['agent_duties']}. {agent_info['ReAct_workflow']} You can use following tools: {tracking_agent_info['tools']} {tracking_agent_info['json_answer_description']}.",
    "interview_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": InterviewAgentResponse.model_json_schema()},
    "planner_agent_response_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerAgentResponse.model_json_schema()},
    "orchestrator_response_format":  {"type": "text", "mime_type": "application/json", "schema": OrchestratorResponse.model_json_schema()},
    "tracking_agent_response_format": {"type": "text", "mime_type": "application/json", "schema": TrackingAgentResponse.model_json_schema()},
    "interview_agent_extraction_format": {"type": "text", "mime_type": "application/json", "schema": InterviewState.model_json_schema()},
    "planner_agent_extraction_format":  {"type": "text", "mime_type": "application/json", "schema": PlannerState.model_json_schema()},
    "tracking_agent_task_extraction_format": {"type": "text", "mime_type": "application/json", "schema": TrackingTaskExtraction.model_json_schema()},    
    "tracking_agent_sha_extraction_format": {"type": "text", "mime_type": "application/json", "schema": TrackingShaExtraction.model_json_schema()},    
}