import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", "! ", "? "]
)

# Initialize Vietnamese bi-encoder model
model = SentenceTransformer('bkai-foundation-models/vietnamese-bi-encoder').to('cuda')

# Initialize Qdrant client with cloud configuration
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Create collection if it doesn't exist
try:
    client.create_collection(
        collection_name="articles2",
        vectors_config=models.VectorParams(
            size=768,  # Size of the embeddings from vietnamese-bi-encoder
            distance=models.Distance.COSINE
        )
    )
except Exception as e:
    print(f"Collection might already exist: {e}")

def process_articles():
    with open("./data/traveloka_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    for article in articles:
        metadata = article.get('metadata', {})
        
        # Combine content paragraphs
        content = " ".join(article.get('content', []))
        
        # Split text into chunks
        chunks = text_splitter.split_text(content)
        
        # Create embeddings and store in Qdrant
        for i, chunk in enumerate(chunks):
            embedding = model.encode(chunk, device='cuda')
            
            chunk_metadata = {
                "article_id": str(uuid.uuid4()),
                "chunk_index": i,
                "text": chunk,
                "title": metadata.get('title', ''),
                "time": metadata.get('time', ''),
                "url": metadata.get('url', '')
            }
            
            client.upsert(
                collection_name="articles2",
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=chunk_metadata
                    )
                ]
            )

    # Process articles_transformed.json
    with open("./data/articles_transformed.json", "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    for article in articles:
        metadata = article.get('metadata', {})
        
        # Combine content paragraphs
        content = " ".join(article.get('content', []))
        
        # Split text into chunks
        chunks = text_splitter.split_text(content)
        
        # Create embeddings and store in Qdrant
        for i, chunk in enumerate(chunks):
            embedding = model.encode(chunk, device='cuda')
            
            chunk_metadata = {
                "article_id": str(uuid.uuid4()),
                "chunk_index": i,
                "text": chunk,
                "title": metadata.get('title', ''),
                "time": metadata.get('time', ''),
                "url": metadata.get('url', '')
            }
            
            client.upsert(
                collection_name="articles2",
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=chunk_metadata
                    )
                ]
            )

if __name__ == "__main__":
    process_articles()
    print("Articles processed and stored in Qdrant Cloud successfully!")
