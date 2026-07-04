import requests

APIkey = open("/home/user/AiThesis/APIkey")
APItext = APIkey.read()

url = "https://generativelanguage.googleapis.com/v1beta/interactions"
payload = {"x-goog-api-key" : f"{APItext}",
           'Content-Type' : 'application/json', 
           "model": "gemini-3.5-flash", 
           "input": "Explain how AI works in a few words"}
headers = {}

res = requests.post(url, data=payload, headers=headers)

print(res)