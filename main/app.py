import  rag
import  agents
import  streamlit                          as st
from    google                             import genai
from    config                             import INTERACTION_ID, KEY_WORD_STATUS_ID

st.title("Project Management Agent")

print('================START================')

client = genai.Client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "id" not in st.session_state:
    st.session_state.id = None

if "previous_response_type" not in st.session_state:
    st.session_state.previous_response_type = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

modelReponses = ['thought', 'action - current_date', 'action - user_location'] 

if prompt := st.chat_input("Type text here") or st.session_state.previous_response_type in modelReponses:    
    # If it's user fisrt message 
    if st.session_state.previous_response_type == None:
        send_msg(role="user", text=prompt)
        previous_response_id=None
        #interaction = agents.generate_response(prompt=f"USER TEXT: {prompt}", previous_response_id=None)
        #print(f"Model first response: {interaction.steps}")
    # If model previous message has been a thought
    elif st.session_state.previous_response_type == 'thought':
        prompt = "NOT USER RESPONSE: Continue response based on conversation history."
        #interaction = agents.generate_response(prompt=f"USER TEXT: {prompt}", previous_response_id=st.session_state.id)
        #print(f"Model response: {interaction.steps}")
    # If model previous message has been an action - more specifically current_date tool call
    elif st.session_state.previous_response_type == 'action - current_date':
        date = agents.current_date()
        prompt = f"current_date tool RESPONSE: {date}"
        #interaction = agents.generate_response(prompt=prompt, previous_response_id=previous_response_id)
    # If model previous message has been an action - more specifically user_location tool call
    elif st.session_state.previous_response_type == 'action - user_location':
        location = agents.user_location()
        prompt = f"user_location tool RESPONSE: {location}"
        #interaction = agents.generate_response(prompt=prompt, previous_response_id=previous_response_id)
    else:
        print(f"ERROR: {st.session_state.previous_response_type}")

    interaction = agents.generate_response(prompt=prompt, previous_response_id=st.session_state.id)

    print("PROMPT:", prompt)
    print("INTERACTION:", interaction.output_text)

    # Set steamlit state variables based on response_type funcion results 
    model_response_type = agents.response_type(model_response=interaction.output_text)
    
    if model_response_type == 'answer':
        send_msg(role="assistant", text=interaction.output_text.replace("<answer>", '', 1))
        st.session_state.previous_response_type = model_response_type
    elif model_response_type in modelReponses:
        st.session_state.previous_response_type = model_response_type
    else:
        print(f"ERROR - model will try again: {st.session_state.previous_response_type}")
        send_msg(role="assistant", text=f'There was an unexpected ERROR: {st.session_state.previous_response_type}. Please try again.')
        st.session_state.previous_response_type = "ERROR"

    st.session_state.id = interaction.id
    st.rerun()