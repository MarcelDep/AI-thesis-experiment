import  json
import  geocoder
import  datetime
import  streamlit   as st
from    google      import genai
from    datetime    import date

st.title("Project Management Agent")

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

def word_detection(text, word):
    return f' {word} ' in f' {text} '

def current_date():
    today = date.today()
    today_str = today.strftime("%Y-%m-%d %H:%M:%S")
    json_date = json.dumps(today_str)
    return {"current_date": json_date}

def user_location():
    location = geocoder.ip('me')
    return location.latlng

tools_dict = {
    "current_date_declaration": current_date(),
    "user_location_declaration": user_location()
}

print("START")

if prompt := st.chat_input("Type text here") or session_state.thought_or_action_key_word == True:
    
    # If user send a prompt
    if prompt := st.chat_input("Type text here"):
        send_msg(role="user", text=prompt)

        if st.session_state.id is None:
            interaction = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, call tools if you decide that you need them, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
                input = f'USER TEXT {prompt}',
                stop_sequences = ['</thought>', '</action>', '</answer>']
                )
        else:
            interaction = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, call tools if you decide that you need them, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
                previous_interaction_id = st.session_state.id,
                input = prompt,
                stop_sequences = ['</thought>', '</action>', '</answer>']
                )
    # If there isn't any response (model had thought or performed an action)
    else:
        prompt = "Continue response based on conversation history."
        interaction = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, call tools if you decide that you need them, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
            previous_interaction_id = st.session_state.id,
            input = prompt,
            stop_sequences = ['</thought>', '</action>', '</answer>']
            )

    # If reponse prompt contain thoughs
    if word_detection(interaction.output_text, '</thought>') == True:
        # Add thought to conversation history and remember that model has thought in this response
        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = True

    # Else if reponse prompt contain action
    else if word_detection(interaction.output_text, '</action>') == True:
        # Use tool, add its output to conversation history and remember that model has used tool
        if word_detection(interaction.output_text, 'current_date') == True:
            date = current_date()
            prompt = f"Continue response based on conversation history - current date is {date}"
        else if word_detection(interaction.output_text, 'user_location') == True:
            location = user_location()
            prompt = f"Continue response based on conversation history - user location is {location}"
        else:
            # ERROR
            prompt = "There was an error related to calling function. Retry with <action> tool </aciton>. Accesible tools are 'current_date' and 'user_location'"

        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = True

    # Else if reponse prompt contain answer
    else if word_detection(interaction.output_text, '</answer>') == True:
        # Print model response and cut <thought> and </thought> key words from it
        if interaction.output_text:
            send_msg(role="assistant", text=interaction.output_text)
        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = False

    print(interaction.steps)