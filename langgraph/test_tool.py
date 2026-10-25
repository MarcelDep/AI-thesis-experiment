# test_tool.py
import schemas
import config
import tools
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

agent = create_agent(
    model=config.llm,
    tools=[tools.user_location],
    system_prompt = """
You are a test agent.

If the user asks for the magic number:
1. Call get_magic_number.
2. Use its result to answer.
3. Never call get_magic_number more than once.
""",
    response_format=ToolStrategy(schemas.AgentResponse)
)

print("Created agent")

result = agent.invoke({
    "messages": [
        {"role": "user", "content": "Where am i"}
    ]
})


print(result)