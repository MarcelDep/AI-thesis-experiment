from google import genai

client = genai.Client() # Initialization of a client 
history = []
id = 0
id_index = 0 

print("Welcome to AI chatbot - ask about anything and enjoy AI understanding of chat history.")
print("If you want to end the conversation write 'END'.")

user_input = input()

while(user_input != "END"):
    if id == 0:
        interaction = client.interactions.create( # Set interaction parameters  
            model = "gemini-2.5-flash", # Specify model
            input = user_input # Specify prompt
        )
    else:
        user_input = input()
        interaction = client.interactions.create( # Set interaction parameters  
            model = "gemini-2.5-flash", # Specify model
            previous_interaction_id = history[id_index - 1], # Specify previous response  
            input = user_input # Specify prompt
        )
    print(f"Odpowiedź AI: {interaction.output_text}")
    id = interaction.id
    id_index += 1
    history.append(id)