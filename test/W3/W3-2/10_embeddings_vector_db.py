import  uuid
import  chromadb
import  pandas                             as pd
import  numpy                              as np
import  chromadb.utils.embedding_functions as embedding_functions
from    google                             import genai
from    google.genai                       import types

google_ef = embedding_functions.GoogleGeminiEmbeddingFunction(
    model_name="gemini-embedding-001",
    task_type="SEMANTIC_SIMILARITY",
)

texts = [
    "deadline",
    "scrum",
    "kiban",
    "project",
    "sprint",
    "team",
    "manager",
    "wbs",
    "task",
    "jira",
    "review",
]

db_client = chromadb.Client()

collection = db_client.create_collection(name='policies', embedding_function=google_ef,)

collection.add(
    ids=[str(uuid.uuid4()) for _ in texts],
    documents=[text for text in texts],
)

user_query = input("Type a word to see which one from database is most similar to it: ")

results = collection.query(
    query_texts=user_query,
    n_results=3
)

for query_result in results["documents"]:
    print(f"\n".join(query_result))