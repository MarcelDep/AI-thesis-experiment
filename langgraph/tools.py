import os
import config
import schemas
import geocoder
import requests
from   langchain_core.tools import tool
from   langgraph.types      import Command
from   langchain.tools      import ToolRuntime
from   langchain.messages   import ToolMessage

llm = config.llm

@tool
def user_location():
    """Get the approximate location of the user."""
    print(f'----TOOL user_location was called')
    location = geocoder.ip('me')
    return f"DONT CALL user_location tool output: the user is in city: {location.city}, country: {location.country}."

@tool
def get_commit_messages(runtime: ToolRuntime):
    """Fetch the list of  commits (message and SHA) from the user's GitHub repository."""
    print(f'----TOOL get_commit_messages was called')
    state = runtime.state
    print(f"TRACKING STATE TYPE {type(state["tracking_state"])}")
    print(f'----STATE: {state["tracking_state"]}')
    gh = state["github_variables"]
    tracking = state["tracking_state"]
    update = {}
    if not gh.owner or not gh.repo:
        text = "ERROR: GitHub owner or repo is not set. Ask the user to fill them in the sidebar."
    else:
        headers = {"Authorization": f"Bearer {os.getenv('GITHUB_PAT')}", "Accept": "application/vnd.github+json",}
        response = requests.get(f'https://api.github.com/repos/{gh.owner}/{gh.repo}/commits', headers=headers)
        if response.status_code != 200:
            if response["message"] == "Bad credentials":
                print(f"----RESPONSE: {response['message']}")
                text  = "ERROR: user has provided invalid GitHub credintials. Check if they are correct and try again."
            else:
                print(f"----RESPONSE: {response['message']}")
                text = "UKNOWN ERROR." 
        else:
            response = response.json()
            commits_with_sha = [
                schemas.CommitsMsgSha(
                    commit_message=commit["commit"]["message"],
                    commit_sha=commit["sha"],
                )
                for commit in response
            ]
            print(f"COMMIT MESSAGES: {commits_with_sha}")
            update["tracking_state"] = tracking.model_copy(update={"commits_msg_sha": commits_with_sha})
            updated_tracking_state = state['tracking_state'].model_copy(update={"commits_msg_sha": commits_with_sha})
            text = f"Commit messeges resolved correctly: {commits_with_sha}"

    update["messages"] = [ToolMessage(content=text, tool_call_id=runtime.tool_call_id)]
    return Command(update=update)

@tool
def get_commit_diff(runtime: ToolRuntime) -> str:
    """Fetch the code changes between two commits of the user's GitHub repository."""    
    print(f'----TOOL get_commit_diff was called')
    state = runtime.state
    print(f"TRACKING STATE TYPE {type(state["tracking_state"])}")
    print(f'----STATE: {state["tracking_state"]}')
    prompt = state["messages"][-1]
    print(f"----BEFORE SHA EXTRACTION CALLED")
    extract_llm = llm.with_structured_output(schemas.TrackingShaExtraction)
    print(f"----SHA EXTRACTION CALLED")
    shas = extract_llm.invoke([
        {
            "role": "system",
            "content": f"You're extraction agent. Other agent decided that it needs to get diff of two github commits. Based on conversation history, user prompt and list of commit messages pick base_sha and head_sha values. Both base_sha and head_sha are sha's of commits from list. Base sha is base commit and changes in head sha will be compared to base sha commit."
        },
        {"role": "user", "content": f'CONVERSATION HISTORY: {state["messages"]}, USER_PROMPT: {prompt}, LIST OF COMMITS AND THEIR SHAs {state["tracking_state"]}'}
    ])
    print(f"----SHA EXTRACTION FINISHED")
    headers = {"Authorization": f"Bearer {os.getenv('GITHUB_PAT')}", "Accept": "application/vnd.github.diff",}
    basehead = f"{shas.base_sha}...{shas.head_sha}"
    response = requests.get(f'https://api.github.com/repos/{state["github_variables"].owner}/{state["github_variables"].repo}/compare/{basehead}', headers=headers)
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
            diff = "UKNOWN ERROR."
    else:
        print(f"----BASE and head shas: {shas}")
        print(response.text)
        diff = response.text[:20000]

    tracking_state = state["tracking_state"]

    updated_tracking_state = tracking_state.model_copy(
        update={"last_diff": diff}
    )

    return Command(
        update={
            "tracking_state": updated_tracking_state,
            "messages": [ToolMessage(
                    content="get_commit_diff tool was called",
                    tool_call_id=runtime.tool_call_id,)]})

@tool
def modify_tasks_status(runtime: ToolRuntime) -> dict:
    """Update the status of tasks in the project plan based on the fetched commits and diff."""
    print(f'----TOOL modify_tasks_status was called')    
    state = runtime.state
    planner_state = state.planner_state
    tracking_state = state.tracking_state

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
    return Command(update={
        "planner_state": new_plan,
        "messages": [ToolMessage(content=f"modify_tasks_status tool was called: {summary}", tool_call_id=runtime.tool_call_id)],
    })