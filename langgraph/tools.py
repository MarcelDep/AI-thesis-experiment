import  agents
import  config
import  geocoder
import  requests
from    google   import genai
from    langchain_core.tools import tool

client = genai.Client()

@tool
def user_location():
    location = geocoder.ip('me')
    print(location)
    return {"previous_thought": f"user_location tool response: {location}"}

# Rozważ czy nie warto usunąć - ale jak nie to dodaj tu powrót do router
'''@tool
def switch_agent(state: config.State):
    PromptVariables.prompt = "Current agent decided that different agent should responde right now. Review conversation and make a decision which agent should respond."
    orchestrator_decision = agents.orchiestrator(SessionVariables=SessionVariables, PromptVariables=PromptVariables)
    return orchestrator_decision'''

@tool
def get_commit_messages(state: config.State):
    headers = {"Authorization": f"Bearer {state.github_variables.token}", "Accept": "application/vnd.github+json",}
    response = requests.get(f'https://api.github.com/repos/{state.github_variables.owner}/{state.github_variables.repo}/commits', headers=headers)
    if response.status_code != 200:
        if response["message"] == "Bad credentials":
            print(f"----RESPONSE: {response['message']}")
            commits_with_sha = "ERROR: user has provided invalid GitHub credintials. Check if they are correct and try again."
        else:
            print(f"----RESPONSE: {response['message']}")
            commits_with_sha = "UKNOWN ERROR." 
    else:
        response = response.json()
        commits_with_sha = [[commit["commit"]["message"],commit["sha"]] for commit in response]
        print(f"COMMIT MESSAGES: {commits_with_sha}")
    return {"previous_thought": f"get_commit_messages tool response: {commits_with_sha}"}

@tool
def get_commit_diff(state: config.State) -> str:
    prompt = state["messages"][-1]

    extract_llm = llm.with_structured_output(config.TrackingShaExtraction)

    shas = extract_llm.invoke([
        {
            "role": "system",
            "content": f"You're extraction agent. Other agent decided that it needs to get diff of two github commits. Based on conversation history, user prompt and list of commit messages pick base_sha and head_sha values. Both base_sha and head_sha are sha's of commits from list. Base sha is base commit and changes in head sha will be compared to base sha commit."
        },
        {"role": "user", "content": f"CONVERSATION HISTORY: {state["messages"]}, AGENT THINKING HISTORY FROM NEWEST USER PROMPT: {state["previous_thought"]}, USER_PROMPT: {prompt}, LIST OF COMMITS AND THEIR SHAs {state["tracking_state"]}"}
    ])

    headers = {"Authorization": f"Bearer {state.github_variables.token}", "Accept": "application/vnd.github.diff",}
    basehead = f"{shas.base_sha}...{shas.head_sha}"
    response = requests.get(f'https://api.github.com/repos/{state.github_variables.owner}/{state.github_variables.repo}/compare/{basehead}', headers=headers)
    print("STATUS:", response.status_code)
    print("CONTENT-TYPE:", response.headers.get("Content-Type"))
    print("URL:", response.url)
    print("RESPONSE:", response.text[:2000])
    if response.status_code != 200:
        if response["message"] == "Bad credentials":
            print(f"----RESPONSE: {response['message']}")
            diff = "ERROR: user has provided invalid GitHub credintials. Check if they are correct and try again."
        else:
            print(f"----RESPONSE: {response['message']}")
            commits_with_sha = "UKNOWN ERROR."
    else:
        print(f"----BASE and head shas: {shas.content}")
        print(response.text)
        diff = response.text[:20000]
    return {"previous_thought": f"get_commit_messages tool response: {diff}"}

@tool
def modify_tasks_status(state) -> dict:
    planner_state = state["planner_state"]
    tracking_state = state["tracking_state"]

    if not planner_state.specific_plan:
        return {"previous_thought": [("system", "modify_tasks_status ERROR: there is no plan yet. The planner has to create one first.")]}
    if not tracking_state.commits_msg_sha and not tracking_state.last_diff:
        return {"previous_thought": [("system", "modify_tasks_status ERROR: no commit data. Call get_commit_messages first.")]}

    tasks_text = "\n".join(
        f"phase {phase.phase_id} | task {task.task_id} | {task.task_name} | {task.status}"
        for phase in planner_state.specific_plan
        for task in phase.tasks
    )
    commits_text = "\n".join(
        f"{c.commit_sha} | {c.commit_message}" for c in tracking_state.commits_msg_sha
    )

    updater = llm.with_structured_output(config.TaskStatusUpdates)
    result = updater.invoke([
        {"role": "system", "content": ('''
            You update task statuses. Each task line is: phase_id | task_id | name | current status.
            Based on the commit messages and/or diff (one may be empty), return an update only for tasks
            the evidence clearly shows are in_progress or done. Omit every task you are unsure about.'''
        )},
        {"role": "user", "content": (
            f"TASKS: {tasks_text} COMMITS: {commits_text} DIFF: {tracking_state.last_diff[:20000]}"
        )},
    ])

    new_plan = planner_state.model_copy(deep=True)
    tasks = {(phase.phase_id, task.task_id): task for phase in new_plan.specific_plan for task in phase.tasks}

    changed = []
    for update in result.updates:
        task = tasks.get((update.phase_id, update.task_id))
        if task is None or task.status == "done":
            continue
        task.status = update.status
        changed.append(f"phase {update.phase_id} task {update.task_id}: {update.status}")

    summary = "Updated: " + "; ".join(changed) if changed else "No task statuses changed."
    return {
        "planner_state": new_plan,
        "previous_thought": [("system", f"modify_tasks_status RESULT: {summary}")],
    }