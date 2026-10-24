import config
import schemas
import geocoder
import requests
from   langchain_core.tools import tool
from   langgraph.types      import Command
from   langchain.tools      import ToolRuntime

llm = config.llm

@tool
def user_location():
    """Get the approximate location of the user (based on IP address).

    Use this tool ONLY when the user's region or country is needed and the user
    has not stated it. Do not use it if the location is already known from the
    conversation. Takes no arguments.

    Returns: city of the user.
    """
    location = geocoder.ip('me')
    print(location)
    return Command(update={"previous_thought": f"user_location tool response: {location}"})

@tool
def get_commit_messages(runtime: ToolRuntime):
    """Fetch the list of recent commits (message and SHA) from the user's GitHub repository.

    Use this tool when the user asks about their progress, recent work, or commits,
    and ALWAYS before get_commit_diff or modify_tasks_status, because those need the
    SHAs from this list. Do not call it again if the commit list is already in the
    conversation. Takes no arguments: the repository and credentials are configured
    by the application.

    Returns: list of commits with message and SHA, or an error message
    (e.g. missing or invalid credentials).
    """
    state = runtime.state
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
    return Command(update={"tracking_state": f"get_commit_messages tool response: {commits_with_sha}", "previous_thought": f"get_commit_messages tool response: {commits_with_sha}"})

@tool
def get_commit_diff(runtime: ToolRuntime) -> str:
    """Fetch the code changes between two commits of the user's GitHub repository.

    Use this tool ONLY when the user asks what specifically changed between commits,
    or when commit messages are not enough to judge whether a task is done.
    It automatically determines the correct SHAs from the conversation history.

    Returns: the diff text (truncated if very long), or an error message.
    """
    state = runtime.state
    prompt = state["messages"][-1]

    extract_llm = llm.with_structured_output(schemas.TrackingShaExtraction)

    shas = extract_llm.invoke([
        {
            "role": "system",
            "content": f"You're extraction agent. Other agent decided that it needs to get diff of two github commits. Based on conversation history, user prompt and list of commit messages pick base_sha and head_sha values. Both base_sha and head_sha are sha's of commits from list. Base sha is base commit and changes in head sha will be compared to base sha commit."
        },
        {"role": "user", "content": f'CONVERSATION HISTORY: {state["messages"]}, AGENT THINKING HISTORY FROM NEWEST USER PROMPT: {state["previous_thought"]}, USER_PROMPT: {prompt}, LIST OF COMMITS AND THEIR SHAs {state["tracking_state"]}'}
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
    return Command(update={"last_diff": f"{diff}"})

@tool
def modify_tasks_status(runtime: ToolRuntime) -> dict:
    """Update the status of tasks in the project plan based on the fetched commits and diff.

    Use this tool AFTER get_commit_messages (and optionally get_commit_diff), when the
    user wants their progress recorded or asks which tasks are done. It requires an
    existing plan and fetched commits, otherwise it returns an error. Call it once
    per request; do not call it again unless new commits were fetched.
    Takes no arguments: it reads the plan and commits itself and only marks tasks
    it is sure about.

    Returns: a summary of which tasks changed status, or "No task statuses changed".
    """
    state = runtime.state
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

    updater = llm.with_structured_output(schemas.TaskStatusUpdates)
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