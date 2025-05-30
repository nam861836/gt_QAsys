import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document as LangchainDocument
from tqdm import tqdm
import random
from openai import OpenAI
import os
from dotenv import load_dotenv

question_groundedness_critique_prompt = """
Bạn sẽ được cung cấp một ngữ cảnh và một câu hỏi.  
Nhiệm vụ của bạn là đưa ra một 'điểm tổng' đánh giá mức độ mà câu hỏi có thể được trả lời một cách rõ ràng và không mơ hồ dựa trên ngữ cảnh đã cho.  
Hãy đưa ra câu trả lời của bạn theo thang điểm từ 1 đến 5, trong đó 1 có nghĩa là câu hỏi hoàn toàn không thể trả lời được dựa vào ngữ cảnh, và 5 có nghĩa là câu hỏi có thể được trả lời rõ ràng và không mơ hồ với ngữ cảnh đó.

Hãy cung cấp câu trả lời của bạn theo định dạng sau:

Answer:::  
Đánh giá: (lý do cho điểm số bạn đưa ra, dưới dạng văn bản)  
Điểm tổng: (số điểm bạn đưa ra, từ 1 đến 5)

BẠN BẮT BUỘC phải cung cấp giá trị cho cả 'Đánh giá:' và 'Điểm tổng:' trong câu trả lời của mình.

Dưới đây là câu hỏi và ngữ cảnh.

Câu hỏi: {question}\n  
Ngữ cảnh: {context}\n  
Answer::: """

question_relevance_critique_prompt = """
Bạn sẽ được cung cấp một câu hỏi.  
Nhiệm vụ của bạn là đưa ra một 'điểm tổng' thể hiện mức độ hữu ích của câu hỏi này đối với người dùng đang muốn tra cứu thông tin về du lịch.  
Hãy đưa ra câu trả lời của bạn theo thang điểm từ 1 đến 5, trong đó 1 có nghĩa là câu hỏi hoàn toàn không hữu ích, và 5 có nghĩa là câu hỏi cực kỳ hữu ích.

Hãy cung cấp câu trả lời của bạn theo định dạng sau:

Answer:::  
Đánh giá: (lý do cho điểm số bạn đưa ra, dưới dạng văn bản)  
Điểm tổng: (số điểm bạn đưa ra, từ 1 đến 5)

BẠN BẮT BUỘC phải cung cấp giá trị cho cả 'Đánh giá:' và 'Điểm tổng:' trong câu trả lời của mình.

Dưới đây là câu hỏi.

Câu hỏi: {question}\n  
Answer::: """

question_standalone_critique_prompt = """
Bạn sẽ được cung cấp một câu hỏi.  
Nhiệm vụ của bạn là đưa ra một 'điểm tổng' thể hiện mức độ độc lập về ngữ cảnh của câu hỏi này.  
Hãy đưa ra câu trả lời của bạn theo thang điểm từ 1 đến 5, trong đó 1 có nghĩa là câu hỏi phụ thuộc vào thông tin bổ sung để có thể hiểu được, và 5 có nghĩa là câu hỏi hoàn toàn có thể hiểu được ngay cả khi đứng một mình.  
Ví dụ, nếu câu hỏi đề cập đến một bối cảnh cụ thể như "trong ngữ cảnh" hoặc "trong tài liệu", thì điểm phải là 1.  
Các câu hỏi có thể chứa các thuật ngữ kỹ thuật khó hiểu hoặc viết tắt như Gradio, Hub, Hugging Face hay Space và vẫn có thể được chấm 5 điểm: miễn là chúng rõ ràng với một người vận hành có quyền truy cập vào tài liệu.

Ví dụ, "What is the name of the checkpoint from which the ViT model is imported?" nên được chấm 1 điểm, vì câu hỏi có ngụ ý đến một ngữ cảnh, do đó không hoàn toàn độc lập.

Hãy cung cấp câu trả lời của bạn theo định dạng sau:

Answer:::  
Đánh giá: (lý do cho điểm số bạn đưa ra, dưới dạng văn bản)  
Điểm tổng: (số điểm bạn đưa ra, từ 1 đến 5)

BẠN BẮT BUỘC phải cung cấp giá trị cho cả 'Đánh giá:' và 'Điểm tổng:' trong câu trả lời của mình.

Dưới đây là câu hỏi.

Câu hỏi: {question}\n  
Answer::: """

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_evaluation(prompt):
    """Get evaluation from OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that evaluates questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting evaluation: {e}")
        return None

# Load the generated QA pairs
print("Loading generated QA pairs...")
with open("./data/generated_qa_pairs.json", "r", encoding="utf-8") as f:
    outputs = json.load(f)

# Evaluate QA pairs
print("\nGenerating critique for each QA pair...")
for output in tqdm(outputs):
    evaluations = {
        "groundedness": get_evaluation(
            question_groundedness_critique_prompt.format(
                context=output["context"], 
                question=output["question"]
            )
        ),
        "relevance": get_evaluation(
            question_relevance_critique_prompt.format(
                question=output["question"]
            )
        ),
        "standalone": get_evaluation(
            question_standalone_critique_prompt.format(
                question=output["question"]
            )
        ),
    }
    
    try:
        for criterion, evaluation in evaluations.items():
            if evaluation:
                score = int(evaluation.split("Điểm tổng: ")[-1].strip())
                eval_text = evaluation.split("Điểm tổng: ")[0].split("Đánh giá: ")[1].strip()
                output.update({
                    f"{criterion}_score": score,
                    f"{criterion}_eval": eval_text,
                })
    except Exception as e:
        print(f"Error processing evaluation: {e}")
        continue

# Save the evaluated QA pairs to a JSON file
print(f"\nSaving evaluated QA pairs...")
with open("./data/evaluated_qa_pairs.json", "w", encoding="utf-8") as f:
    json.dump(outputs, f, ensure_ascii=False, indent=2)

# Print evaluation summary
print("\nEvaluation Summary:")
for criterion in ["groundedness", "relevance", "standalone"]:
    scores = [output.get(f"{criterion}_score", 0) for output in outputs if f"{criterion}_score" in output]
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"{criterion.capitalize()}: Average score = {avg_score:.2f} (n={len(scores)})")
