import  agents
import  config
import  geocoder
import  requests
from    google   import genai

client = genai.Client()

def user_location():
    location = geocoder.ip('me')
    print(location)
    return location.latlng

def update_state(agent_instance, prompt):
    agents.agent_instance.extract_state(prompt)

# Rozwiąż problem manualnego dodawania agentów do promtpa - słownik z statusem kazdego agenta?
def switch_agent(SessionVariables: config.SessionVariables, PromptVariables: config.PromptVariables) -> config.OrchestratorResponse:
    PromptVariables.prompt = "Current agent decided that different agent should responde right now. Review conversation and make a decision which agent should respond."
    orchestrator_decision = agents.orchiestrator(SessionVariables=SessionVariables, PromptVariables=PromptVariables)
    return orchestrator_decision

def get_commit_messages(GithubVariables: config.GithubVariables) -> list:
    headers = {"Authorization": f"Bearer {GithubVariables.token}", "Accept": "application/vnd.github+json",}
    response = requests.get(f'https://api.github.com/repos/{GithubVariables.owner}/{GithubVariables.repo}/commits', headers=headers)
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
    return commits_with_sha

def get_commit_diff(GithubVariables: config.GithubVariables, SessionVariables: config.SessionVariables, PromptVariables: config.PromptVariables) -> str:
    interaction = client.interactions.create(
        model = config.llm["model"],
        system_instruction = "You're extraction agent. Other agent decided that it needs to get diff of two github commits. Based on conversation history, user prompt and list of commit messages pick base_sha and head_sha values. Both base_sha and head_sha are sha's of commits from list. Base sha is base commit and changes in head sha will be compared to base sha commit.",
        input = f'CONVERSATION HISTORY: {SessionVariables.answer_history}, AGENT THINKING HISTORY FROM NEWEST USER PROMPT: {PromptVariables.current_ReAct_history}, USER_PROMPT: {PromptVariables.prompt}, LIST OF COMMITS AND THEIR SHAs {SessionVariables.agent_states.tracking_agent_state.commits_msg_sha}',
        response_format = config.llm["tracking_agent_sha_extraction_format"],
        generation_config={
            "max_output_tokens": config.llm["max_output_tokens"],
        },
    )
    headers = {"Authorization": f"Bearer {GithubVariables.token}", "Accept": "application/vnd.github.diff",}
    shas = config.TrackingShaExtraction.model_validate_json(interaction.output_text)
    basehead = f"{shas.base_sha}...{shas.head_sha}"
    response = requests.get(f'https://api.github.com/repos/{GithubVariables.owner}/{GithubVariables.repo}/compare/{basehead}', headers=headers)
    if response.status_code != 200:
        if response["message"] == "Bad credentials":
            print(f"----RESPONSE: {response['message']}")
            diff = "ERROR: user has provided invalid GitHub credintials. Check if they are correct and try again."
        else:
            response = response.json()
            print(f"----BASE and head shas: {interaction.output_text}")
            print(response.text)
            diff = response.text
    return diff

# def get_commit_metadata():