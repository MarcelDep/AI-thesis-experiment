import logging
from datetime import datetime
from pythonjsonlogger.json import JsonFormatter

logging.basicConfig(level=logging.INFO, filename=f"{current_time}.log", filemode="w",
                    format="%(asctime)s - %(levelname)s - %(message)s")

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
        extra={"response_type": f"{response}", "content": f"{content}", "state": f"{state}"},
    )

def errors_activity(error_msg, ):
    logger.info(
        f"{error_msg}",
        extra={"response_type": f"{response}", "content": f"{content}", "state": f"{state}"},
    )

current_time = datetime.now()
print(current_time.time())