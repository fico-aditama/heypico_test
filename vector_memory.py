import chromadb
from chromadb.config import Settings
import time

# Create a local persistent Vector DB on disk
client = chromadb.PersistentClient(path="./chroma_db")

# Automatically creates embeddings using the built-in all-MiniLM-L6-v2 model 
# (Standard light model for RAG text similarity)
collection = client.get_or_create_collection(name="chat_history")

def add_memory(role: str, content: str):
    """Stores a message into the Vector DB with a timestamp."""
    timestamp = str(int(time.time() * 1000))
    # We use the timestamp as ID to maintain chronological order later
    doc_id = f"msg_{timestamp}"
    
    collection.add(
        documents=[content],
        metadatas=[{"role": role, "timestamp": timestamp}],
        ids=[doc_id]
    )
    return doc_id

def get_recent_history(limit: int = 20):
    """Retrieve the chronological chat history to restore the UI."""
    try:
        # Get all records
        results = collection.get(include=["documents", "metadatas"])
        if not results or not results["ids"]:
            return []
        
        # Zip them together and sort by timestamp (encoded in ID)
        history = []
        for i in range(len(results["ids"])):
            history.append({
                "id": results["ids"][i],
                "role": results["metadatas"][i]["role"],
                "content": results["documents"][i],
                "timestamp": int(results["metadatas"][i]["timestamp"])
            })
        
        # Sort chronologically and take the last 'limit' items
        history.sort(key=lambda x: x["timestamp"])
        return history[-limit:]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

def get_semantic_memory(user_query: str, limit: int = 3):
    """
    RAG Search: Find past messages that are semantically close to the user's current query.
    Used for Long-term AI memory!
    """
    try:
        if collection.count() == 0:
            return ""
            
        results = collection.query(
            query_texts=[user_query],
            n_results=min(collection.count(), limit)
        )
        
        if not results['documents'][0]:
            return ""
            
        context = []
        for i, doc in enumerate(results['documents'][0]):
            role = results['metadatas'][0][i]['role']
            context.append(f"[{role}]: {doc}")
            
        return "\n".join(context)
    except Exception as e:
        print(f"Semantic memory error: {e}")
        return ""

def clear_vector_db():
    """Wipe the database."""
    global collection
    client.delete_collection("chat_history")
    collection = client.create_collection(name="chat_history")
    return True
