import  streamlit   as st
import  json
import  datetime
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
    today_str = today.strftime("%Y-%m-%d %H:%M:%S")
    json_date = json.dumps(today_str)
    return {"current_date": json_date}

current_date_declaration = {
    "type": "function",
    "name": "current_date",
    "description": "Get current date",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "id" not in st.session_state:
    st.session_state.id = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

print("START")

if prompt := st.chat_input("Type text here"):
    send_msg(role="user", text=prompt)

    if st.session_state.id is None:
        interaction = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, call tools if you decide that you need them, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
            input = f'ROLE: You are an expert in project management. CONTEXT: You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Generate responses based on shich ReAct setp you are. USER TEXT {prompt}',
            tools = [current_date_declaration]
            )
    else:
        interaction = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            system_instruction = 'Work in ReAct pattern send one key word per message. Use "Though:" to describe what you think you should do, call tools if you decide that you need them, and "Answer:" for printing final answer to user. Send only one keyword per message. Dont send multiple ReAct steps in one message',
            previous_interaction_id = st.session_state.id,
            input = prompt,
            tools = [current_date_declaration]
            )

    print(interaction.steps)

    if any(s.type == "function_call" for s in interaction.steps):

        fc_step = next(s for s in interaction.steps if s.type == "function_call")
        if fc_step.name == "current_date":
            result = current_date()
            print("Checked current date.")

            final_interaction = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                input = [
                    {
                        "type": "function_result",
                        "name": fc_step.name,
                        "call_id": fc_step.id,
                        "result": [{"type": "text", "text": json.dumps(result)}],
                    }
                ],
                tools = [current_date_declaration],
                previous_interaction_id=interaction.id
            )
        print(final_interaction.steps)
        if final_interaction.output_text:
            send_msg(role="assistant", text=final_interaction.output_text)
        st.session_state.id = final_interaction.id

    else:
        if interaction.output_text:
            send_msg(role="assistant", text=interaction.output_text)
        st.session_state.id = interaction.id