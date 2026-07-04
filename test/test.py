from google import genai

client = genai.Client() # Initialization of a client 

interaction = client.interactions.create( # Set interaction parameters  
    model = "gemini-3.5-flash", # Specify model 
    input = "Explain how AI works in few seconds" # Specify prompt
)

print(interaction.output_text)