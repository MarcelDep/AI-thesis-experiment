from langchain.chat_models import init_chat_model

llm = init_chat_model(
    config.LLM_CONFIG["model"],
    model_provider=config.LLM_CONFIG["model_provider"],
)

agents_characteristic = {
    'router': '"router" analyses user needs and routes to the appropriate agent',
    'interview_agent': '"interview_agent" Interviews user to define project goals, technologies, working style and requirements',
    'planner_agent': '"planner_agent" breaks project into structured tasks and sprint plans based on interview data',
    'tracking_agent': '"tracking_agent" monitors GitHub commits and assesses whether planned tasks are correctly implemented',
}

database = {
    "THRESHOLD": 0.3,
}

agent_info = {
    "project_description": "You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects.",
    "amount_of_agents": len(agents_characteristic),
    "agents_description": agents_characteristic,
}

interview_agent_info = {
    "agent_description": "You're an interview agent",
    "agent_duties": "You're task is to interview user. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style",
}

planner_agent_info = {
    "agent_description": "You're a planner agent",
    "agent_duties": "You're task is to plan tasks for user based on information interview_agent gathered from interview with user",
}

tracking_agent_info = {
    "agent_description": "You're a tracking agent",
    "agent_duties": "You're task is to track user progress - how many tasks did user finished based on planner_agent plan and users code on GitHub",
}

router_info = {
    "agent_description": "You're an router.",
    "agent_duties": "Your task is to decide which agent should responde to user prompt",
}

additional_orchestrator_info = f"Only switch to other agents from interview_agent when ALL of the fields in interview_state are non-empty strings: goal, technologies, deadline, working_style, requirements. If any of these fields are empty string "", keep using interview_agent regardless of what the conversation suggests. Do not infer that information is gathered from conversation text alone — check the actual state fields."
additional_interview_agent_into = f"When whole infomration in InerviewAgent state is filled, call switch_agent tool. Else, keep askign for missing info untill state is full."
additional_tracking_agent_info = f"If you've requested diff or commit messeges in previous messages in current ReAct history, then don't request it again."

LLM_CONFIG = {
    "model": "gemini-3.1-flash-lite",
    "model_provider": "google_genai",
    "max_output_tokens": 2048,
    "router_instruction": f"{router_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {router_info['agent_duties']}. {additional_orchestrator_info}.",
    "interview_agent_instruction": f"{interview_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {interview_agent_info['agent_duties']}. {additional_interview_agent_into}",
    "planner_agent_instruction": f"{planner_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {planner_agent_info['agent_duties']}.",
    "tracking_agent_instruction": f"{tracking_agent_info['agent_description']}. {agent_info['project_description']}. There are {agent_info['amount_of_agents']} agents in this app - {agent_info['agents_description']}. {tracking_agent_info['agent_duties']}.",    
}