import os
from dotenv import load_dotenv
from google import genai                                          # ← SỬA 1: đổi dòng import

from pdf_process import load_and_split_pdf, create_vector_store
from ytb_process import search_youtube_videos

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))         # ← SỬA 2: đổi cách khởi tạo

NGUONG_LIEN_QUAN = 0.8

def answer_question(vector_store, query):
    results = vector_store.similarity_search_with_score(query, k=2)
    
    if results and results[0][1] < NGUONG_LIEN_QUAN:
        context = "\n\n".join([doc.page_content for doc, score in results])
        
        prompt = f"""Dựa vào tài liệu sau, trả lời câu hỏi của học sinh một cách rõ ràng, dễ hiểu.

Tài liệu:
{context}

Câu hỏi: {query}
"""
        response = client.models.generate_content(                 # ← SỬA 3: đổi cách gọi generate_content
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return {
            "type": "rag_answer",
            "answer": response.text,
            "source": "Dựa trên tài liệu bạn đã upload"
        }
    
    else:
        videos = search_youtube_videos(query)
        
        return {
            "type": "youtube_fallback",
            "message": "Mình chưa có tài liệu về chủ đề này. Đây là vài video bài giảng có thể giúp bạn:",
            "videos": videos
        }


if __name__ == "__main__":
    chunks = load_and_split_pdf("test.pdf")
    vector_store = create_vector_store(chunks)
    
    result1 = answer_question(vector_store, "Object detection là gì?")
    print(result1)
    
    result2 = answer_question(vector_store, "Cách mạng tháng Tám diễn ra khi nào?")
    print(result2)