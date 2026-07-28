import  config
import  chromadb
import  chromadb.utils.embedding_functions as embedding_functions
from    sklearn.metrics.pairwise           import cosine_similarity

def database_init():
    f = open("./documents/project_management_wiki.txt", "r")

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
                if cosine_similarity(sentence["embeddings"], previous_sentence["embeddings"])[0][0] > config.database["THRESHOLD"]:
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