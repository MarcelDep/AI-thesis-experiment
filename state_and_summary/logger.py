import logging
from datetime import datetime
from pythonjsonlogger.json import JsonFormatter

current_time = current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

handler = logging.FileHandler(f"logs/{current_time}.log")
handler.setFormatter(JsonFormatter())

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def log_user_messages(prompt):
    logger.info(
        f"User message: {prompt}",
    )

def log_orchestrator_activity(agent, justification):
    logger.info(
        f"Orchestrator decision: {agent}",
        extra={"justification": f"{justification}"},
    )
    
def log_agent_activity(agent, response_type, content, state):
    logger.info(
        f"Agent: {agent}",
        extra={"response_type": f"{response_type}", "content": f"{content}", "state": f"{state}"},
    )

def log_errors(error_msg,):
    logger.error(
        f"{error_msg}",
    )