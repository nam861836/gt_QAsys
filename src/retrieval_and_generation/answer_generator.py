import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from openai import OpenAI # Using for OpenAI API

# Load environment variables
load_dotenv()

# Initialize Vietnamese bi-encoder model for retrieval
retrieval_model = SentenceTransformer('bkai-foundation-models/vietnamese-bi-encoder').to('cuda')

# Initialize cross-encoder model for reranking
reranker_model = CrossEncoder('BAAI/bge-reranker-base').to('cuda')

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)


# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables. OpenAI API calls will fail.")
    openai_client = None
else:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            # base_url is not set, defaults to OpenAI's API
        )
        print(f"OpenAI client initialized to use model: {OPENAI_MODEL_NAME}")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        openai_client = None

def get_relevant_chunks(user_query: str, top_k: int = 20, rerank_top_k: int = 10) -> list:
    """
    Encodes the user query and retrieves the top_k most relevant chunks
    from the Qdrant collection, then reranks them using a cross-encoder model.
    
    Args:
        user_query: The user's query
        top_k: Number of initial documents to retrieve from Qdrant (default: 20)
        rerank_top_k: Number of top documents to keep after reranking (default: 10)
    """
    if not retrieval_model or not reranker_model:
        print("Retrieval or reranking model not loaded. Cannot get relevant chunks.")
        return []
        
    # First stage: Retrieve documents using bi-encoder
    query_embedding = retrieval_model.encode(user_query, device='cuda')
    search_results = qdrant_client.search(
        collection_name="articles2",
        query_vector=query_embedding.tolist(),
        limit=top_k,
        with_payload=True
    )

    # Prepare documents for reranking
    documents = []
    for hit in search_results:
        payload = hit.payload if hit.payload else {}
        chunk_text = payload.get("text", "")
        if chunk_text:
            documents.append({
                "text": chunk_text,
                "title": payload.get("title", ""),
                "url": payload.get("url", ""),
                "initial_score": hit.score
            })

    if not documents:
        return []

    # Second stage: Rerank documents using cross-encoder
    pairs = [(user_query, doc["text"]) for doc in documents]
    rerank_scores = reranker_model.predict(pairs)
    
    # Combine rerank scores with documents
    for doc, score in zip(documents, rerank_scores):
        doc["rerank_score"] = float(score)
    
    # Sort by rerank score and take top_k
    reranked_documents = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)[:rerank_top_k]
    
    return reranked_documents

def generate_answer_with_openai(user_query: str, retrieved_chunks: list) -> str:
    """
    Generates an answer using the OpenAI API based on the user query and retrieved chunks.
    Uses the model name defined by OPENAI_MODEL_NAME environment variable or defaults.
    """
    if not openai_client:
        return "OpenAI client not initialized. Check OPENAI_API_KEY."

    context = "\n\n---\n\n".join([chunk["text"] for chunk in retrieved_chunks])
    
    system_prompt = "Bạn là một trợ lý AI chuyên về du lịch. Hãy trả lời dựa trên ngữ cảnh."
    
    user_message_content = f"""Ngữ cảnh:{context} Câu hỏi: {user_query}"""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message_content},
            ],
            temperature=0.7, 
            max_tokens=500   
        )
        answer = response.choices[0].message.content
        return answer.strip()
    except Exception as e:
        print(f"Error calling OpenAI API with model {OPENAI_MODEL_NAME}: {e}")
        return "Xin lỗi, đã có lỗi xảy ra khi cố gắng tạo câu trả lời."


if __name__ == '__main__':
    sample_query = "Hà Nội có những địa điểm vui chơi giải trí nào?"
    
    print(f"Retrieving relevant chunks for query: '{sample_query}'")
    relevant_chunks = get_relevant_chunks(sample_query, top_k=20, rerank_top_k=10)

    if relevant_chunks:
        print(f"Found {len(relevant_chunks)} relevant chunks:")
        for i, chunk_info in enumerate(relevant_chunks):
            print(f"--- Chunk {i+1} (Score: {chunk_info['rerank_score']:.4f}) ---")
            print(f"Title: {chunk_info['title']}")
            print(f"Text: {chunk_info['text']}")
            print("-" * 20)
        
        if openai_client:
            print(f"\nGenerating answer for query: '{sample_query}' using OpenAI model: {OPENAI_MODEL_NAME}...")
            answer = generate_answer_with_openai(sample_query, relevant_chunks)
            print(f"\nGenerated Answer:\n{answer}")
        else:
            print("\nOpenAI client not initialized. Skipping answer generation.")
        
    else:
        print("No relevant chunks found. Cannot generate an answer.")

    '''
    sample_query_no_hits = "Thông tin về khủng long bạo chúa ở Hà Nội"
    print(f"\nRetrieving relevant chunks for query: '{sample_query_no_hits}'")
    relevant_chunks_no_hits = get_relevant_chunks(sample_query_no_hits, top_k=2)
    if relevant_chunks_no_hits:
        print(f"Found {len(relevant_chunks_no_hits)} relevant chunks for the second query.")
        if openai_client:
            print(f"\nGenerating answer for query: '{sample_query_no_hits}' using OpenAI model: {OPENAI_MODEL_NAME}...")
            answer_no_hits = generate_answer_with_openai(sample_query_no_hits, relevant_chunks_no_hits)
            print(f"\nGenerated Answer (for potentially no-hit query):\n{answer_no_hits}")
        else:
            print("\nOpenAI client not initialized. Skipping answer generation for the second query.")
    else:
        print("No relevant chunks found for the second query.") 
    '''