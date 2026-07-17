import  streamlit   as st
from    google      import genai
from    datetime    import date

st.title("Project Management Agent")

client = genai.Client()

def send_msg(role, text):
    with st.chat_message(role):
        st.markdown(text)
    st.session_state.messages.append({'role': role, "content": text})

def word_detection(text, word):
    return f' {word} ' in f' {text} '

def current_date():
    today = date.today()
    return f"Current date is {today}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "id" not in st.session_state:
    st.session_state.id = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Type text here"):
    send_msg(role="user", text=prompt)

    if st.session_state.id is None:
        interaction = client.interactions.create(
            model = 'gemini-2.5-flash',
            system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, "Action:" to call tool. Tools include "date_", and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
            input = f'ROLE: You are an expert in project management. CONTEXT: You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Generate responses based on shich ReAct setp you are. USER TEXT {prompt}'
            stop_sequences = "Action: date_"
            )
    else:
        interaction = client.interactions.create(
            model = 'gemini-2.5-flash',
            system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, "Action:" to call tool for finding current date, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
            previous_interaction_id = st.session_state.id,
            input = prompt
            stop_sequence = "Action: date_"
            )

    if interaction.output_text:
        send_msg(role="assistant", text=interaction.output_text)

    print(word_detection(interaction.output_text, 'Answer:'))

    st.session_state.id = interaction.id