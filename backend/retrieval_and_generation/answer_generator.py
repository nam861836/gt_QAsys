import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from openai import OpenAI

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
        )
        print(f"OpenAI client initialized to use model: {OPENAI_MODEL_NAME}")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        openai_client = None

def generate_answer_with_openai(user_query: str, context: str) -> str:
    """
    Generates an answer using the OpenAI API based on the user query and context.
    """
    if not openai_client:
        return "OpenAI client not initialized. Check OPENAI_API_KEY."

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

def generate_chat_response(user_query: str) -> str:
    """
    Generates a chat response using OpenAI without context.
    """
    if not openai_client:
        return "OpenAI client not initialized. Check OPENAI_API_KEY."

    system_prompt = "Bạn là một trợ lý AI thân thiện và hữu ích."

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=0.7,
            max_tokens=500
        )
        answer = response.choices[0].message.content
        return answer.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Xin lỗi, đã có lỗi xảy ra khi cố gắng tạo câu trả lời." 