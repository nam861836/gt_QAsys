import streamlit as st
import time
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")


# Initialize models and clients
@st.cache_resource
def initialize_models():
    # Initialize Vietnamese bi-encoder model
    retrieval_model = SentenceTransformer('bkai-foundation-models/vietnamese-bi-encoder')
    
    # Initialize Qdrant client
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY", "")
    )
    
    # Initialize OpenAI client
    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    return retrieval_model, qdrant_client, openai_client

# RAG functions
def get_relevant_chunks(query: str, retrieval_model, qdrant_client, top_k: int = 3):
    """Retrieve relevant chunks from Qdrant."""
    query_embedding = retrieval_model.encode(query)
    
    search_results = qdrant_client.search(
        collection_name="articles",
        query_vector=query_embedding.tolist(),
        limit=top_k,
        with_payload=True
    )
    
    retrieved_chunks = []
    for hit in search_results:
        payload = hit.payload if hit.payload else {}
        chunk_text = payload.get("text", "")
        if chunk_text:
            retrieved_chunks.append({
                "text": chunk_text,
                "title": payload.get("title", ""),
                "url": payload.get("url", ""),
                "score": hit.score
            })
    return retrieved_chunks

def generate_answer(query: str, retrieved_chunks: list, openai_client):
    """Generate answer using OpenAI."""
    context = "\n\n---\n\n".join([chunk["text"] for chunk in retrieved_chunks])
    
    system_prompt = "Bạn là một trợ lý AI chuyên về du lịch. Hãy trả lời dựa trên ngữ cảnh."
    user_message_content = f"""Ngữ cảnh:{context} Câu hỏi: {query}"""
    
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
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error calling OpenAI API: {e}")
        return "Xin lỗi, đã có lỗi xảy ra khi cố gắng tạo câu trả lời."

def get_response(query: str, retrieval_model, qdrant_client, openai_client):
    """Get response from RAG system."""
    retrieved_chunks = get_relevant_chunks(query, retrieval_model, qdrant_client)
    if not retrieved_chunks:
        return "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn."
    
    return generate_answer(query, retrieved_chunks, openai_client)

# Streamlit UI
def main():
    st.set_page_config(
        page_title="RAG Chat Demo",
        page_icon="🤖",
        layout="wide"
    )

    # Title and description
    st.title("🤖 RAG Chat Demo")
    st.markdown("""
    This demo shows how the RAG (Retrieval-Augmented Generation) system works.
    Ask questions about travel, and the system will retrieve relevant information and generate answers.
    """)

    # Initialize models
    try:
        retrieval_model, qdrant_client, openai_client = initialize_models()
    except Exception as e:
        st.error(f"Error initializing models: {e}")
        st.stop()

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about travel..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Show assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Simulate thinking
            with st.spinner("Thinking..."):
                # Get response from RAG system
                response = get_response(prompt, retrieval_model, qdrant_client, openai_client)
                
                # Simulate typing effect
                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Add sidebar with information
    with st.sidebar:
        st.title("About")
        st.markdown("""
        This demo uses:
        - Sentence Transformers for retrieval
        - Qdrant for vector storage
        - OpenAI for generation
        """)
        
        st.title("How it works")
        st.markdown("""
        1. Your question is processed by the retrieval model
        2. Relevant information is retrieved from the database
        3. The context and question are sent to OpenAI
        4. A response is generated based on the retrieved information
        """)

if __name__ == "__main__":
    main() 