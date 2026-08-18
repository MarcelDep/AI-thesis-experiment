import  rag
import  agents
import  streamlit                          as st
from    google                             import genai

st.title("Project Management Agent")

print('================START================')

client = genai.Client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "previous_response_type" not in st.session_state:
    st.session_state.previous_response_type = None

if "current_agent" not in st.session_state:
    st.session_state.current_agent = ''

if "answer_history" not in st.session_state:
    st.session_state.answer_history = []

if "current_thinking_process" not in st.session_state:
    st.session_state.current_thinking_process = []

if "error_retry_count" not in st.session_state:
    st.session_state.error_retry_count = 0

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

modelReponses = ['thought', 'action - current_date', 'action - user_location', 'action - switch_agent'] 

if prompt := st.chat_input("Type text here") or st.session_state.previous_response_type in modelReponses:    
    # If user has send a prompt
    if prompt != None and prompt != True:
        send_msg(role="user", text=prompt)
        st.session_state.answer_history.append(f"USER PROMPT: {prompt}")
        st.session_state.current_thinking_process = []
        # Orchestrator choose which agent should response
        orchestrator_decision = agents.orchiestrator(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process)
        st.session_state.current_agent = orchestrator_decision[0]
        print(st.session_state.current_agent)
    # If model previous message has been a thought
    elif st.session_state.previous_response_type == 'thought':
        prompt = "NOT USER RESPONSE: Continue response based on conversation history."
    # If model previous message has been an action - more specifically current_date tool call
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool = 'current_date':
        date = agents.current_date()
        prompt = f"current_date tool RESPONSE: {date}"
    # If model previous message has been an action - more specifically user_location tool call
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool = 'user_location':
        location = agents.user_location()
        prompt = f"user_location tool RESPONSE: {location}"
    elif st.session_state.previous_response_type == 'action' and st.session_state.previous_tool = 'switch_agent':
        prompt = "Current agent decided that different agent should responde right now. Review conversation and make a decision which agent should respond."
        orchestrator_decision = agents.orchiestrator(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process)
        st.session_state.current_agent = orchestrator_decision[0]
        prompt = f"Continue based on conversation history. Orchestration decision: {orchestrator_decision[1]}"
    else:
        print(f"ERROR: {st.session_state.previous_response_type}")
        prompt = f"UKNOWN ERROR related to ReAct pipeline. Previous response_type was: {st.session_state.previous_response_type}"
    
    if st.session_state.current_agent != 'interviewer_instruction' and st.session_state.current_agent != 'planer_instruction':
        send_msg(role="assistant", text=f'There was an unexpected ERROR related to agent role. Current agent: {st.session_state.current_agent}. Please try again.')
        st.session_state.previous_response_type = "ERROR"
        print(st.session_state.current_agent)
        st.rerun()

    interaction = agents.agent_response(prompt=prompt, answer_history=st.session_state.answer_history, current_ReAct_history=st.session_state.current_thinking_process, agent_type=st.session_state.current_agent)

    print("PROMPT:", prompt)
    print("INTERACTION:", interaction.output_text)

    # Set steamlit state variables based on response_type funcion results 
    model_response_type = interaction["type"]
    
    if model_response_type == 'answer':
        send_msg(role="assistant", text=interaction.output_text["content"])
        st.session_state.previous_response_type = model_response_type
        st.session_state.answer_history.append(interaction.output_text["content"])
    elif model_response_type in modelReponses:
        st.session_state.previous_response_type = model_response_type
    else:
        print(f"ERROR - model will try again: {st.session_state.previous_response_type}")
        send_msg(role="assistant", text=f'There was an unexpected ERROR: {st.session_state.previous_response_type}. Please try again.')
        st.session_state.previous_response_type = "ERROR"

    st.session_state.current_thinking_process.append(interaction.output_text)
    st.rerun()