import  json
import  agents
import  geocoder
import  requests
from    datetime                           import date

def current_date():
    today = date.today()
    print(today)
    return today

def user_location():
    location = geocoder.ip('me')
    print(location)
    return location.latlng

# Rozwiąż problem manualnego dodawania agentów do promtpa - słownik z statusem kazdego agenta?
def switch_agent(answer_history, current_ReAct_history, interview_agent_state, planner_agent_state):
    prompt = "Current agent decided that different agent should responde right now. Review conversation and make a decision which agent should respond."
    orchestrator_decision = agents.orchiestrator(prompt=prompt, answer_history=answer_history, current_ReAct_history=current_ReAct_history, interview_agent_state=interview_agent_state, planner_agent_state=planner_agent_state)
    return orchestrator_decision

def get_commit_messages(owner, repo, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",}
    response = requests.get(f'https://api.github.com/repos/{owner}/{repo}/commits', headers=headers).json()
    commits_with_sha = [[commit["commit"]["message"],commit["sha"]] for commit in response]
    print(f"COMMIT MESSAGES: {commits_with_sha}")
    return commits_with_sha

def get_commit_diff(owner, repo, token, base_sha, head_sha):
    basehead = f"{base_sha}...{head_sha}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.diff",}
    response = requests.get(f'https://api.github.com/repos/{owner}/{repo}/compare/{basehead}', headers).json()
    changes = [[file["filename"], file["patch"]] for file in response["files"]]
    return changes

# def get_commit_metadata():