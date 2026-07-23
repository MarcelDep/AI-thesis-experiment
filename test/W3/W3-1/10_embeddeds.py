from google                     import genai
from google.genai               import types
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def my_cosine_similarity(vectors):
    vectors_lenght = len(vectors)
    multiplied_vectors = np.zeros(shape=(vectors_lenght, vectors_lenght))
    vector_pythagoreans = np.zeros(shape=(vectors_lenght, vectors_lenght))
    results = []
    result = 0
    for vector_x in range(vectors_lenght):
        for vector_y in range(vectors_lenght):
            vector_A_pythagorean = 0
            vector_B_pythagorean = 0
            for value in range(len(vectors[vector_x])):
                multiplied_vectors[vector_x, vector_y] += (vectors[vector_x][value] * vectors[vector_y][value])
                vector_A_pythagorean += (vectors[vector_x][value])**2
                vector_B_pythagorean += (vectors[vector_y][value])**2
            vector_pythagoreans[vector_x, vector_y] = (vector_A_pythagorean)**(1/2) * (vector_B_pythagorean)**(1/2)
            result = multiplied_vectors[vector_x, vector_y] / vector_pythagoreans[vector_x, vector_y]
            results.append(result)

    reshaped_result = np.reshape(results, shape=(vectors_lenght, vectors_lenght))
    return reshaped_result

client = genai.Client()
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
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=texts,
    config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
)

pd.options.display.float_format = '{:.8f}'.format

print("My cosine fun")
df = pd.DataFrame(
    my_cosine_similarity([e.values for e in result.embeddings]),
    index=texts,
    columns=texts,
)
print(df)