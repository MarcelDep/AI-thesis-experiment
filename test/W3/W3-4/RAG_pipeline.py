import  json
import  time
import  geocoder
import  datetime
import  chromadb
import  pandas                             as pd
import  numpy                              as np
import  chromadb.utils.embedding_functions as embedding_functions
import  streamlit                          as st
from    datetime                           import date
from    google                             import genai
from    google.genai                       import types
from    sklearn.metrics.pairwise           import cosine_similarity

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
    detected = f'{word}' in f'{text}'
    print(f"Czy poprawnie wykryto {word}: {detected}")
    return detected

def current_date():
    today = date.today()
    print(today)
    return today

def user_location():
    location = geocoder.ip('me')
    print(location)
    return location.latlng

THRESHOLD = 0.3

f = open("project_management_wiki.txt", "r")

text = f.read()

db_client = chromadb.PersistentClient(path="./chroma_db")

# Every sentence should be added to database as embedded vectors
sentence_collection = db_client.get_or_create_collection(name='embedded_sentences',)

if sentence_collection.count() == 0:
    ids = []
    documents = []
    for index, sentence in enumerate(text.split(".")):
        if (index+1)%100 != 0 and index+1 != len(text.split(".")):
            ids.append(f"sentence_{index}")
            documents.append(sentence)
        else:
            ids.append(f"sentence_{index}")
            documents.append(sentence)
            sentence_collection.add(
                ids=ids,
                documents=documents,
            )
            ids=[]
            documents=[]
            # time.sleep(60)

    # Compare sentance x to sentence y
    chunk_collection = db_client.get_or_create_collection(name='chunks',)

    index = 0 
    chunk_index = 0
    chunk_sentences = []
    for index in range(len(text.split("."))):
        sentence = sentence_collection.get(ids=[f"sentence_{index}"], include=["embeddings", "documents"])
        # For first sentence create a new chunk
        if index == 0:
            chunk_sentences.append(sentence["documents"][0])
            chunk_collection.add(
                ids=[f"chunk_{chunk_index}"],
                documents=chunk_sentences,
            )
        else:
            previous_sentence = sentence_collection.get(ids=[f"sentence_{index-1}"], include=["embeddings"])
            # Check if cosine_similarity of current sentence is over THRESHOLD in database. If it is - add current sentence to current chunk
            if cosine_similarity(sentence["embeddings"], previous_sentence["embeddings"])[0][0] > THRESHOLD:
                chunk_sentences = [chunk_sentences[0] + sentence["documents"][0]]
                chunk_collection.update(
                    ids=[f"chunk_{chunk_index}"],
                    documents=chunk_sentences,
                )
            # If not - create a new chunk and add sentence there
            else:
                chunk_index += 1
                chunk_sentences = []
                chunk_sentences.append(sentence["documents"][0])
                chunk_collection.add(
                    ids=[f"chunk_{chunk_index}"],
                    documents=chunk_sentences,
                )
else:
    chunk_collection = db_client.get_or_create_collection(name='chunks')

print("START")

if prompt := st.chat_input("Type text here") or st.session_state.thought_or_action_key_word == True:
    
    print(prompt)
    # If user send a prompt
    if prompt != None and prompt != True:
        send_msg(role="user", text=prompt)

        if st.session_state.id is None:
            interaction = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                system_instruction = 'You are an expert in project management. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: "current_date" to get current date and "user_location" to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location.',
                input = f'RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | USER TEXT {prompt}',
                generation_config = {"stop_sequences": ["</end>", "</answer>", "</thought>", "</action>"]}
                )
            print(f"Odpowiedź modelu 1 zapytanie {interaction.steps}")
            # print(interaction.output_text)
        else:
            interaction = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                system_instruction = 'You are an expert in project management. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: "current_date" to get current date and "user_location" to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location.',
                previous_interaction_id = st.session_state.id,
                input = f'RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | USER TEXT {prompt}',
                generation_config = {"stop_sequences": ["</end>", "</answer>", "</thought>", "</action>"]}
                )
            print(f"Odpowiedź modelu po kolejnych promptach {interaction.steps}")
            # print(interaction.output_text)
    # If there isn't any response (model had thought or performed an action)
    else:
        print("Tool was called")
        prompt = "Continue response based on conversation history."
        interaction = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            system_instruction = 'You are an expert in project management. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: "current_date" to get current date and "user_location" to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location.',
            previous_interaction_id = st.session_state.id,
            input = f'RAG CONTEXT: {chunk_collection.query(query_texts=prompt, n_results=3)} | USER TEXT {prompt}',
            generation_config = {"stop_sequences": ["</end>", "</answer>", "</thought>", "</action>"]}
            )
        print(f"Odpowiedź modelu po uzyciu tool'a {interaction.steps}")
        # print(interaction.steps)

    # If reponse prompt contain thoughs
    if word_detection(interaction.output_text, '<thought>') == True:
        # Add thought to conversation history and remember that model has thought in this response
        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = True
        st.rerun()
    # Else if reponse prompt contain action
    elif word_detection(interaction.output_text, '<action>') == True:
        # Use tool, add its output to conversation history and remember that model has used tool
        if word_detection(interaction.output_text, 'current_date') == True:
            date = current_date()
            prompt = f"current_date tool RESPONSE: {date}"
        elif word_detection(interaction.output_text, 'user_location') == True:
            location = user_location()
            prompt = f"user_location tool RESPONSE: {location}"
        else:
            # ERROR
            prompt = "There was an error related to calling function. Retry with <action> tool </aciton>. Accesible tools are 'current_date' and 'user_location'"

        interaction = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            system_instruction = 'You are an expert in project management. You are part of a chatbot in an application that uses AI to make it easier for users to complete IT projects. Users will come to you with project ideas, and your task is to conduct an interview with them. Based on that interview, you will define the project goals, preferred technologies, the users preferred working style, and break the project down into smaller tasks so that the user can easily start implementing it. Work in ReAct workflow. Use following syntax to send specific types of messages: <thought> thought_you_generate </end> - use this to describe your thoughts, <action> one of available tools </end> - use this to call tool, <answer> answer_you_generate </end> - use this to print your final response to user.  Send only one type per message. Available tools include: "current_date" to get current date and "user_location" to get users location. Use current_date tool if you need to know what is current date so you can plan users tasks efficently, use user_location to gather information where user lives and adjust project to their location.',
            previous_interaction_id = st.session_state.id,
            input = prompt,
            generation_config = {"stop_sequences": ["</end>", "</answer>", "</thought>", "</action>"]}
        )
        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = True
        st.rerun()

    # Else if reponse prompt contain answer
    elif word_detection(interaction.output_text, '<answer>') == True:
        # Print model response and cut <thought> and </thought> key words from it

        if interaction.output_text:
            send_msg(role="assistant", text=interaction.output_text.replace("<answer>", '', 1))
        st.session_state.id = interaction.id
        st.session_state.thought_or_action_key_word = False
    else:
        print("ERROR: try again.")