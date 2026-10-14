import os
import unicodedata
from dotenv import load_dotenv
from google import genai

from core.ytb_process import search_youtube_videos

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

STOP_WORDS = {
    "là", "gì", "của", "và", "các", "những", "về", "có", "không",
    "ai", "một", "này", "đó", "cho", "được", "khi", "như", "để",
    "trong", "với", "đã", "sẽ", "đang", "nào", "sao", "thì", "mà"
}


def normalize_text(text):
    return unicodedata.normalize('NFC', text)


def answer_question(retriever, vector_store, query):
    child_results = vector_store.similarity_search_with_score(query, k=2)

    is_relevant = False
    if child_results:
        top_content = normalize_text(child_results[0][0].page_content.lower())
        query_words = [normalize_text(w) for w in query.lower().split() if len(w) > 2 and w not in STOP_WORDS]
        matched_words = [w for w in query_words if w in top_content]
        is_relevant = len(matched_words) > 0

    if is_relevant:
        parent_docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in parent_docs[:2]])

        prompt = f"""Dựa vào tài liệu sau, trả lời câu hỏi của học sinh một cách rõ ràng, dễ hiểu.

Tài liệu:
{context}

Câu hỏi: {query}
"""
        response = client.models.generate_content(
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