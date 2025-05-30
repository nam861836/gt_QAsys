import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document as LangchainDocument
from tqdm import tqdm
import random
from openai import OpenAI
import os
from dotenv import load_dotenv

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True,
    separators=["\n\n", "\n", ". ", "! ", "? "]
)

# Load environment variables
load_dotenv()

docs_processed = []

with open("./data/traveloka_articles.json", "r", encoding="utf-8") as f:
    articles = json.load(f)

# Create Langchain documents from articles
langchain_docs = []
for article in tqdm(articles, desc="Creating documents"):
    content = " ".join(article.get('content', []))
    if content:  # Only process if there's content
        langchain_docs.append(
            LangchainDocument(
                page_content=content,
                metadata={
                    "source": article.get('title', 'Unknown'),
                    "url": article.get('url', ''),
                    "date": article.get('date', '')
                }
            )
        )

print("Splitting documents into chunks...")
for doc in tqdm(langchain_docs, desc="Splitting documents"):
    docs_processed.extend(text_splitter.split_documents([doc]))

print(f"Total number of chunks created: {len(docs_processed)}")

# Print first few chunks
print("\nFirst 3 chunks:")
for i, chunk in enumerate(docs_processed[:3]):
    print(f"\nChunk {i+1}:")
    print("-" * 50)
    print("Content:", chunk.page_content[:200] + "..." if len(chunk.page_content) > 200 else chunk.page_content)
    print("Metadata:", chunk.metadata)
    print("-" * 50)


QA_generation_prompt = """
Nhiệm vụ của bạn là viết một câu hỏi dạng factoid (thông tin thực tế) và một câu trả lời dựa trên một đoạn văn bản cho trước.
Câu hỏi factoid của bạn nên có thể được trả lời bằng một thông tin thực tế cụ thể, ngắn gọn từ đoạn văn bản.
Câu hỏi factoid của bạn nên được viết theo phong cách giống như các câu hỏi mà người dùng có thể nhập vào công cụ tìm kiếm.
Điều này có nghĩa là câu hỏi factoid của bạn KHÔNG ĐƯỢC đề cập đến những cụm như "theo đoạn văn" hay "ngữ cảnh".

Hãy cung cấp câu trả lời của bạn theo định dạng sau:

Output:::
Factoid question: (câu hỏi factoid của bạn)
Answer: (câu trả lời của bạn cho câu hỏi factoid)

Dưới đây là ngữ cảnh.

Context: {context}\n
Output:::
"""

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_qa_pair(context):
    """Generate a QA pair using OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # You can change this to other models if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates question-answer pairs from given text."},
                {"role": "user", "content": QA_generation_prompt.format(context=context)}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating QA pair: {e}")
        return None

# Generate QA pairs
N_GENERATIONS = 100  # Number of QA pairs to generate
print(f"Generating {N_GENERATIONS} QA pairs...")

outputs = []
for sampled_context in tqdm(random.sample(docs_processed, N_GENERATIONS)):
    # Generate QA pair
    output_QA_couple = generate_qa_pair(sampled_context.page_content)
    if output_QA_couple:
        try:
            # Extract question and answer from the response
            question = output_QA_couple.split("Factoid question: ")[-1].split("Answer: ")[0].strip()
            answer = output_QA_couple.split("Answer: ")[-1].strip()
            
            # Validate answer length
            if len(answer) < 300:
                outputs.append({
                    "context": sampled_context.page_content,
                    "question": question,
                    "answer": answer
                })
        except Exception as e:
            print(f"Error processing QA pair: {e}")
            continue

# Save the generated QA pairs to a JSON file
print(f"\nSuccessfully generated {len(outputs)} QA pairs")
with open("./data/generated_qa_pairs.json", "w", encoding="utf-8") as f:
    json.dump(outputs, f, ensure_ascii=False, indent=2)

# Print first few generated QA pairs
print("\nFirst 3 generated QA pairs:")
for i, qa_pair in enumerate(outputs[:3]):
    print(f"\nQA Pair {i+1}:")
    print("-" * 50)
    print("Question:", qa_pair["question"])
    print("Answer:", qa_pair["answer"])
    print("-" * 50)

