import chromadb


CHROMA_PATH = "data/chromadb"


client = chromadb.PersistentClient(path="data/chromadb")

def get_chroma_client():
    return client