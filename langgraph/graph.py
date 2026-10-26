import tools
import config
import agents
import schemas
from langgraph.graph import StateGraph, START, END

State = schemas.State

interview = agents.InterviewAgent()
planner   = agents.PlannerAgent()
tracking  = agents.TrackingAgent()

graph_builder = StateGraph(State)

graph_builder.add_node("router", agents.router)
graph_builder.add_node("interview_agent", interview.response)
graph_builder.add_node("planner_agent", planner.response)
graph_builder.add_node("tracking_agent", tracking.response)
graph_builder.add_node("interview_extraction", interview.extract_state)
graph_builder.add_node("planner_extraction", planner.extract_state)
graph_builder.add_node("tracking_extraction", tracking.extract_state)

graph_builder.add_edge(START, "router")

graph_builder.add_conditional_edges(
    "router",
    lambda state: state.get("choosed_agent"),
    {"interview_agent": "interview_agent", "planner_agent": "planner_agent", "tracking_agent": "tracking_agent"}
)

graph_builder.add_conditional_edges(
    "interview_agent",
    lambda state: state.get("update_state"),
    {True: "interview_extraction", False: END}
)
graph_builder.add_conditional_edges(
    "planner_agent",
    lambda state: state.get("update_state"),
    {True: "planner_extraction", False: END}
)
graph_builder.add_conditional_edges(
    "tracking_agent",
    lambda state: state.get("update_state"),
    {True: "tracking_extraction", False: END}
)

graph_builder.add_edge("interview_extraction", END)
graph_builder.add_edge("planner_extraction", END)
graph_builder.add_edge("tracking_extraction", END)

graph = graph_builder.compile()

def run_chatbot():
    state = {
    "messages": [],
    "conv_summary": [],
    "choosed_agent": '',
    "update_state": False,
    "interview_state": schemas.InterviewState(),
    "planner_state": schemas.PlannerState(),
    "tracking_state": schemas.TrackingState(),
    "github_variables": schemas.GithubVariables(),
    }

    while True:
        user_input = input("Message: ")
        if user_input == "exit":
            print("Bye")
            break

        state["messages"] = state.get("messages", []) + [
            {"role": "user", "content": user_input}
        ]

        state = graph.invoke(state)

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            print(f"Assistant: {last_message.content}")

if __name__ == "__main__":
    run_chatbot()