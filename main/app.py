import  os
import  rag
import  json
import  tools
import  agents
import  logger
import  streamlit                          as st
from    google                             import genai
from    github                             import Github
from    dotenv                             import load_dotenv

load_dotenv()

# UI

st.title("Project Management Agent")

print('================START================')

client = genai.Client()

# Session state variables

if "messages" not in st.session_state:
    st.session_state.messages = []

if "previous_response_type" not in st.session_state:
    st.session_state.previous_response_type = None

if "previous_tool" not in st.session_state:
    st.session_state.previous_tool = None

if "current_agent" not in st.session_state:
    st.session_state.current_agent = ''

if "answer_history" not in st.session_state:
    st.session_state.answer_history = []

if "current_thinking_process" not in st.session_state:
    st.session_state.current_thinking_process = []

if "error_retry_count" not in st.session_state:
    st.session_state.error_retry_count = 0

if "agents" not in st.session_state:
    st.session_state.interview_agent_instance = agents.InterviewAgent()
    st.session_state.planner_agent_instance = agents.PlannerAgent()
    st.session_state.tracking_agent_instance = agents.TrackingAgent()

if "github_token" not in st.session_state:
    st.session_state.github_token = os.getenv("GITHUB_PAT")

if "github_repo" not in st.session_state:
    st.session_state.github_repo = ""

if "github_owner" not in st.session_state:
    st.session_state.github_owner = ""

st.session_state.github_repo = st.sidebar.text_input("GitHub repo", value=st.session_state.github_repo)
st.session_state.github_owner = st.sidebar.text_input("GitHub owner", value=st.session_state.github_owner)

if "switch_agent_called" not in st.session_state:
    st.session_state.switch_agent_called = False

# Streamlit roles
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

# Variables
modelReponses = ['thought', 'action',] 
available_tools = ['current_date', 'user_location', 'switch_agent', 'get_commit_messages', 'get_commit_diff',]
available_agents = ['interview_agent', 'planner_agent', 'tracking_agent',]

# Trigger when user has send a prompt or when previous message has been a thought or an action
if prompt := st.chat_input("Type text here") or st.session_state.previous_response_type in modelReponses:    
    # If user has send a prompt
    if prompt != None and prompt != True:
        print(f"USER: {prompt}")
        logger.log_user_messages(prompt)
        send_msg(role="user", text=prompt)
        st.session_state.answer_history.append(f"USER PROMPT: {prompt}")
        st.session_state.current_thinking_process = []
        st.session_state.interview_agent_instance.extract_state(st.session_state.answer_history)
        # Orchestrator choose which agent should response
        orchestrator_decision = agents.orchiestrator(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process, interview_agent_state=st.session_state.interview_agent_instance.state, planner_agent_state=st.session_state.planner_agent_instance.state)
        st.session_state.current_agent = orchestrator_decision.agent
    # If model previous message has been a thought
    elif st.session_state.previous_response_type == 'thought':
        prompt = "NOT USER RESPONSE: Continue response based on conversation history."
    # If model previous message has been an action - more specifically current_date tool call
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'current_date':
        date = tools.current_date()
        prompt = f"current_date tool RESPONSE: {date}"
    # If model previous message has been an action - more specifically user_location tool call
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'user_location':
        location = tools.user_location()
        prompt = f"user_location tool RESPONSE: {location}"
    # If model previous message has been an action - more specifically switch_agent tool call
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'switch_agent':
        if st.session_state.switch_agent_called == False:
            st.session_state.switch_agent_called = True
            orchestrator_decision = tools.switch_agent(answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process, interview_agent_state=st.session_state.interview_agent_instance.state, planner_agent_state=st.session_state.planner_agent_instance.state)
            st.session_state.current_agent = orchestrator_decision.agent
            prompt = f"Continue based on conversation history. Orchestration decision with justification: {orchestrator_decision}"
        else:
            prompt = f"You have been selected by the orchestrator to respond. Continue the conversation directly. Do NOT call switch_agent."
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'get_commit_messages':
        commit_messages = tools.get_commit_messages(owner=st.session_state.github_owner, repo=st.session_state.github_repo, token=st.session_state.github_token)
        prompt = f"get_commit_messages tool RESPONSE: {commit_messages}"
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'get_commit_diff':
        commit_diff = tools.get_commit_diff(owner=st.session_state.github_owner, repo=st.session_state.github_repo, token=st.session_state.github_token, base_sha=st.session_state.tracking_agent_instance.base_sha, head_sha=st.session_state.tracking_agent_instance.head_sha)
 
    # Else - call an error
    else:
        error_msg = f"ERROR: {st.session_state.previous_response_type}"
        logger.log_errors(error_msg)
        prompt = f"UKNOWN ERROR related to ReAct pipeline. Previous response_type was: {st.session_state.previous_response_type}"
    
    # Check which agent was chosen to answer, if none of availeble call an error
    if st.session_state.current_agent not in available_agents:
        error_msg = f'There was an unexpected ERROR related to agent role. Current agent: {st.session_state.current_agent}'
        send_msg(role="assistant", text=f'{error_msg}. Please try again.')
        st.session_state.previous_response_type = "ERROR"
        logger.log_errors(error_msg)
        st.rerun()
    # Czy da się jakoś pozbyć tej ściany ifów?
    # If interview agent was chosen
    elif st.session_state.current_agent == 'interview_agent':
        interaction = st.session_state.interview_agent_instance.response(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process,)
    # If planner agent was chosen
    elif st.session_state.current_agent == 'planner_agent':
        interaction = st.session_state.planner_agent_instance.response(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process,)
    # If tracking agent was chosen
    elif st.session_state.current_agent == 'tracking_agent':
        interaction = st.session_state.tracking_agent_instance.response(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process,)

    print(f"Agent {st.session_state.current_agent} response: ", interaction)

    # Save agent response type as session vaviable and make neccesary steps after that
    if interaction.response_type == 'answer':
        send_msg(role="assistant", text=interaction.content)
        st.session_state.previous_response_type = interaction.response_type
        st.session_state.answer_history.append(interaction.content)
        st.session_state.switch_agent_called = False
    elif interaction.response_type == 'action':
        st.session_state.previous_tool = interaction.tool
        st.session_state.previous_response_type = interaction.response_type
    elif interaction.response_type in modelReponses:
        st.session_state.previous_response_type = interaction.response_type
    else:
        error_msg = f"There was an unexpected ERROR related to generated message_type: {st.session_state.previous_response_type}."
        send_msg(role="assistant", text=f'{error_msg}. Please try again.')
        st.session_state.previous_response_type = "ERROR"
        logger.log_errors(error_msg)

    st.session_state.current_thinking_process.append(interaction.content)
    st.rerun()