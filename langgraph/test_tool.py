# test_tool.py
import schemas
import config
import tools
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

print(f"Interview_agent system prompt: {config.LLM_CONFIG['interview_agent_instruction']}")
print(f"Planner_agent system prompt: {config.LLM_CONFIG['planner_agent_instruction']}")
print(f"Tracking_agent system prompt: {config.LLM_CONFIG['tracking_agent_instruction']}")