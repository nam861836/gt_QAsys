import os
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# Initialize models and clients
retrieval_model = SentenceTransformer('bkai-foundation-models/vietnamese-bi-encoder')
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Text splitter for chunking documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

def get_user_collection_name(user_id: int) -> str:
    """Generate a unique collection name for each user"""
    return f"user_{user_id}_documents"

def process_document(text: str, user_id: int, document_id: int) -> List[Dict]:
    """
    Process a document by splitting it into chunks and storing in Qdrant
    """
    # Split text into chunks
    chunks = text_splitter.split_text(text)
    
    # Generate embeddings for chunks
    embeddings = retrieval_model.encode(chunks)
    
    # Get user-specific collection name
    collection_name = get_user_collection_name(user_id)
    
    # Prepare points for Qdrant
    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(models.PointStruct(
            id=f"{document_id}_{i}",  # Simplified ID since we're in user-specific collection
            vector=embedding.tolist(),
            payload={
                "text": chunk,
                "document_id": document_id
            }
        ))
    
    # Create collection if it doesn't exist
    try:
        qdrant_client.get_collection(collection_name)
    except:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=retrieval_model.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE
            )
        )
    
    # Upload points to Qdrant
    qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )
    
    return points

def retrieve_relevant_chunks(query: str, user_id: int, top_k: int = 5) -> List[Dict]:
    """
    Retrieve relevant chunks from Qdrant based on the query
    """
    # Get user-specific collection name
    collection_name = get_user_collection_name(user_id)
    
    # Generate query embedding
    query_embedding = retrieval_model.encode(query)
    
    # Search in Qdrant
    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=top_k
    )
    
    # Format results
    chunks = []
    for hit in search_results:
        chunks.append({
            "text": hit.payload["text"],
            "score": hit.score,
            "document_id": hit.payload["document_id"]
        })
    
    return chunks

def delete_document_chunks(user_id: int, document_id: int):
    """
    Delete all chunks associated with a document
    """
    collection_name = get_user_collection_name(user_id)
    qdrant_client.delete(
        collection_name=collection_name,
        points_selector=models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id)
                )
            ]
        )
    ) 