import  agents
import  config
import  geocoder
import  requests
from    datetime import date
from    google   import genai

client = genai.Client()

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

def get_commit_diff(owner, repo, token, prompt, answer_history, current_ReAct_history, commits_msg_sha):
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = "You're extraction agent. Other agent decided that it needs to get diff of two github commits. Based on conversation history, user prompt and list of commit messages pick base_sha and head_sha values. Both base_sha and head_sha are sha's of commits from list. Base sha is base commit and changes in head sha will be compared to base sha commit.",
        input = f'CONVERSATION HISTORY: {answer_history}, AGENT THINKING HISTORY FROM NEWEST USER PROMPT: {current_ReAct_history}, USER_PROMPT: {prompt}, LIST OF COMMITS AND THEIR SHAs {commits_msg_sha}',
        response_format = config.llm["tracking_agent_sha_extraction_format"],
        generation_config={
            "max_output_tokens": config.llm["max_output_tokens"],
        },
    )
    print(f"----BASE and head shas: {interaction.output_text}")
    shas = config.TrackingShaExtraction.model_validate_json(interaction.output_text)
    basehead = f"{shas.base_sha}...{shas.head_sha}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.diff",}
    response = requests.get(f'https://api.github.com/repos/{owner}/{repo}/compare/{basehead}', headers=headers)
    print(response.text)
    diff = response.text
    return diff

# def get_commit_metadata():