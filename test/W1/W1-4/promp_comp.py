from google import genai

client = genai.Client() # Initialization of a client 
history = []
id = 0
id_index = 0 

print("Welcome to AI Project Manager chat bot - ask question related to PM field and choose best answer to continue your chat with this model.")
print("If you want to end the conversation write 'END'.")

user_input = input()

while(user_input != 'END'):
    if id_index == 0:
        interaction1 = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            input = f'ROLA: Jesteś ekspertem z zakresu project managementu. KONTEKST: jesteś elementem chatbota w aplikacji wykorzystującej AI do ułatwienia użytkownikom realizację projektów IT. Użytkownicy będą do ciebie pisali z pomysłami projektów i twoim zdaniem jest przeprowadzenie z nimi wywiadu na podstawie którego określisz cele projektu, preferowane technologie, preferowany styl pracy użytkownika i rozdzielisz projekt na mniejsze zadania tak, żeby użytkownik bez problemu mogł zabrać się za jego realizację. TEKST UŻYTKOWNIKA {user_input}'  
        ) 
        interaction2 = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            input = f'ROLA: Jesteś ekspertem z zakresu project managementu. KONTEKST: jesteś agentem AI w aplikacji wykorzystującej AI do zarządzania projektami IT. Użytkownicy będą do ciebie pisali z pomysłami projektów. TWOJE ZADANIE: Ustal potrzebne dla ciebie informacje odnośnie projektu użytkownika tak, żebyś mógł rozplanować cały projekt w najlepszy możliwy sposób, jeżeli czegoś nie wiesz to zapytaj użytkownika o to w wywiadzie. TEKST UŻYTKOWNIKA {user_input}'  
        ) 
        interaction3 = client.interactions.create(
            model = 'gemini-3.1-flash-lite',
            input = f'ROLA: Jesteś ekspertem z zakresu project managementu. KONTEKST: Prowadź rozmowę z użytkownikiem jak najlepszy project manager na świecie i rób to co taki project manager by robił. TEKST UŻYTKOWNIKA {user_input}'  
        ) 
        print(f"Odpowiedź agenta nr. 1 {interaction1.output_text}")
        print(f"Odpowiedź agenta nr. 2 {interaction2.output_text}")
        print(f"Odpowiedź agenta nr. 3 {interaction3.output_text}")
        print("Wybierz, którą odpowiedź wolisz aby kontynuować rozmowę z tym agentem. Wpisz numer preferowanego agenta.")
        preferred_agent = int(input())
        while preferred_agent not in {1, 2, 3}:
            print("ERROR: wpisz numer preferowanego agenta (1, 2 lub 3).")
            preferred_agent = int(input())
    else:
        if preferred_agent == 1:
            user_input = input()
            interaction1 = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                previous_interaction_id = id1,
                input = user_input
            ) 
            print(interaction1.output_text)
        elif preferred_agent == 2:
            interaction2 = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                previous_interaction_id = id2,
                input = user_input
            )
            print(interaction2.output_text)
        else:
            interaction3 = client.interactions.create(
                model = 'gemini-3.1-flash-lite',
                previous_interaction_id = id3,
                input = user_input  
            ) 
            print(interaction3.output_text)
    id_index += 1
    id1 = interaction1.id
    id2 = interaction2.id
    id3 = interaction3.id