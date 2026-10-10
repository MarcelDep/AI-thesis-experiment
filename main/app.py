import  os
import  rag
import  tools
import  config
import  agents
import  logger
import  streamlit                          as st
from    google                             import genai
from    dotenv                             import load_dotenv

chunk_collection = rag.database_init()
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

if "error_retry_count" not in st.session_state:
    st.session_state.error_retry_count = 0

if "interview_agent_instance" not in st.session_state:
    st.session_state.interview_agent_instance = agents.InterviewAgent()

if "planner_agent_instance" not in st.session_state:
    st.session_state.planner_agent_instance = agents.PlannerAgent()

if "tracking_agent_instance" not in st.session_state:
    st.session_state.tracking_agent_instance = agents.TrackingAgent()

if "switch_agent_called" not in st.session_state:
    st.session_state.switch_agent_called = False

if "session_variables_instance" not in st.session_state:
    st.session_state.session_variables_instance = config.SessionVariables()

if "prompt_variables_instance" not in st.session_state:
    st.session_state.prompt_variables_instance = config.PromptVariables()

if "github_variables_instance" not in st.session_state:
    st.session_state.github_variables_instance = config.GithubVariables()
    st.session_state.github_variables_instance.token = os.getenv("GITHUB_PAT")

st.session_state.github_variables_instance.repo = st.sidebar.text_input("GitHub repo", value=st.session_state.github_variables_instance.repo)
st.session_state.github_variables_instance.owner = st.sidebar.text_input("GitHub owner", value=st.session_state.github_variables_instance.owner)

# Streamlit roles
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

# Variables
modelReponses = ['action',] 
available_tools = ['current_date', 'user_location', 'switch_agent', 'get_commit_messages', 'get_commit_diff',]
available_agents = ['interview_agent', 'planner_agent', 'tracking_agent',]

# Trigger when user has send a prompt or when previous message has been a thought or an action
if prompt := st.chat_input("Type text here") or st.session_state.previous_response_type in modelReponses:
    # If user has send a prompt
    if prompt != None and prompt != True:
        print(f"----USER: {prompt}")
        logger.log_user_messages(prompt)
        send_msg(role="user", text=prompt)
        prompt_variables = config.PromptVariables()
        st.session_state.prompt_variables_instance.current_ReAct_history = []
        st.session_state.prompt_variables_instance.rag = chunk_collection.query(query_texts=prompt, n_results=3)
        st.session_state.session_variables_instance.answer_history.append(f"USER PROMPT: {prompt}")
        st.session_state.interview_agent_instance.extract_state(prompt=prompt)
        # Orchestrator choose which agent should response
        orchestrator_decision = agents.orchiestrator(SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)
        st.session_state.current_agent = orchestrator_decision.agent
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
            orchestrator_decision = tools.switch_agent(SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)
            st.session_state.current_agent = orchestrator_decision.agent
            prompt = f"Continue based on conversation history. Orchestration decision with justification: {orchestrator_decision}"
        else:
            prompt = f"You have been selected by the orchestrator to respond. Continue the conversation directly. Do NOT call switch_agent."
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'get_commit_messages':
        if st.session_state.github_variables_instance.repo == "" or st.session_state.github_variables_instance.owner == "":
            print("You need to provide GitHub creditials before calling github related tools.")
            prompt = "ERROR - NO GITHUB CREDITIALS - Inform user that they need to provide GitHub creditials before calling github related tools."
        else:
            commit_messages = tools.get_commit_messages(GithubVariables=st.session_state.github_variables_instance)
            print(st.session_state.tracking_agent_instance)
            st.session_state.tracking_agent_instance.state.commits_msg_sha = commit_messages
            prompt = f"get_commit_messages tool RESPONSE: {commit_messages}"
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool == 'get_commit_diff':
        if st.session_state.github_variables_instance.repo == "" or st.session_state.github_variables_instance.owner == "":
            print("You need to provide GitHub creditials before calling github related tools.")
            prompt = "ERROR - NO GITHUB CREDITIALS - Inform user that they need to provide GitHub creditials before calling github related tools."
        else:
            if st.session_state.tracking_agent_instance.state.commits_msg_sha != []:
                commit_diff = tools.get_commit_diff(GithubVariables=st.session_state.github_variables_instance, SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)
                prompt = f"get_commit_diif tool RESPONSE: {commit_diff}"
            else: 
                prompt = f"ERROR: There aren't any commits messages in Tracking Agent state. You need to get users commits first with get_commit_messages before trying to diff two commits."
                print(f"ERROR: There aren't any commits messages in Tracking Agent state. You need to get users commits first with get_commit_messages before trying to diff two commits.")
    # Else - call an error
    else:
        error_msg = f"ERROR: {st.session_state.previous_response_type}"
        logger.log_errors(error_msg)
        prompt = f"UKNOWN ERROR. Previous response_type was: {st.session_state.previous_response_type}"
    
    # Check which agent was chosed to answer, if none of availeble call an error
    if st.session_state.current_agent not in available_agents:
        error_msg = f'There was an unexpected ERROR related to agent role. Current agent: {st.session_state.current_agent}'
        send_msg(role="assistant", text=f'{error_msg}. Please try again.')
        st.session_state.previous_response_type = "ERROR"
        logger.log_errors(error_msg)
        st.rerun()
    # Czy da się jakoś pozbyć tej ściany ifów?
    # If interview agent was chosen
    elif st.session_state.current_agent == 'interview_agent':
        interaction = st.session_state.interview_agent_instance.response(SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)
    # If planner agent was chosen
    elif st.session_state.current_agent == 'planner_agent':
        interaction = st.session_state.planner_agent_instance.response(SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)
    # If tracking agent was chosen
    elif st.session_state.current_agent == 'tracking_agent':
        interaction = st.session_state.tracking_agent_instance.response(SessionVariables=st.session_state.session_variables_instance, PromptVariables=st.session_state.prompt_variables_instance)

    # Save agent response type as session vaviable and make neccesary steps after that
    if interaction.response_type == 'answer':
        st.session_state.conv_summary = agents.summarize(answer_history=st.session_state.session_variables_instance.answer_history,)
        send_msg(role="assistant", text=interaction.content)
        st.session_state.previous_response_type = interaction.response_type
        st.session_state.session_variables_instance.answer_history.append(f"AGENT ANSWER: {interaction.content}")
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

    # To jest nadmiarowe - agent nie musi miec w self informacji o state skoro jest ona przechowywana w session_variables
    st.session_state.session_variables_instance.agent_states.interview_agent_state = st.session_state.interview_agent_instance.state
    st.session_state.session_variables_instance.agent_states.planner_agent_state = st.session_state.planner_agent_instance.state
    st.session_state.session_variables_instance.agent_states.tracking_agent_state = st.session_state.tracking_agent_instance.state
    st.session_state.prompt_variables_instance.current_ReAct_history.append(interaction.content)
    st.rerun()