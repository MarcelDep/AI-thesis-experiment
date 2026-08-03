import  rag
import  agents
import  streamlit                          as st
from    google                             import genai
from    config                             import INTERACTION_ID, KEY_WORD_STATUS_ID

st.title("Project Management Agent")

print('START')

client = genai.Client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "id" not in st.session_state:
    st.session_state.id = None

if "thought_or_action_key_word" not in st.session_state:
    st.session_state.thought_or_action_key_word = False

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

if prompt := st.chat_input("Type text here") or st.session_state.thought_or_action_key_word == True:    
    print(prompt)
    # If user send a prompt
    if prompt != None and prompt != True:
        send_msg(role="user", text=prompt)

        if st.session_state.id is None:
            # generate_response(prompt, previous_id=None) funtion that returns interaction
            interaction = agents.generate_response(prompt=f"USER TEXT: {prompt}", previous_response_id=None)
            print(f"Model first response: {interaction.steps}")
        else:
            # generate_response(prompt, previous_id=st.session_state.id) funtion that returns interaction
            interaction = agents.generate_response(prompt=f"USER TEXT: {prompt}", previous_response_id=st.session_state.id)
            print(f"Model response: {interaction.steps}")
    # If there isn't any response (model had thought or performed an action)
    else:
        # Think, use tool, or answer user quenstion - generate_response(prompt, previous_id=st.session_state.id) funtion that returns interaction
        prompt = "NOT USER RESPONSE: Continue response based on conversation history."
        interaction = agents.generate_response(prompt=prompt, previous_response_id=st.session_state.id)

    # Check response_type(interaction.output_text) that returns thought_or_action_key_word, interaction.id, 
    # Set steamlit state variables based on response_type funcion results 
    result = agents.response_type(current_interaction=interaction, previous_response_id=st.session_state.id)

    print("PROMPT:", prompt)
    print("INTERACTION:", interaction.output_text)

    if result[1] == False:
        send_msg(role="assistant", text=interaction.output_text.replace("<answer>", '', 1))

    st.session_state.id = result[INTERACTION_ID]
    st.session_state.thought_or_action_key_word = result[KEY_WORD_STATUS_ID] 
    st.rerun()