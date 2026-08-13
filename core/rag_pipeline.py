import os
from dotenv import load_dotenv
from google import genai

from core.ytb_process import search_youtube_videos

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"timeout": 30000}
)

# Chroma distance: smaller = more similar.
NGUONG_LIEN_QUAN = 0.72


def _youtube_fallback(query):
    try:
        videos = search_youtube_videos(query)

        return {
            "type": "youtube_fallback",
            "message": (
                "Mình chưa tìm thấy thông tin phù hợp trong tài liệu "
                "hoặc Gemini hiện không khả dụng. "
                "Dưới đây là một số video YouTube có thể giúp bạn:"
            ),
            "videos": videos,
        }

    except Exception as e:
        return {
            "type": "error",
            "message": (
                "Gemini hiện không khả dụng và cũng không thể tải "
                "video YouTube. Vui lòng thử lại sau."
            ),
            "error": str(e),
        }


def answer_question(vector_store, query):
    try:
        results = vector_store.similarity_search_with_score(
            query,
            k=2
        )

    except Exception as e:
        return {
            "type": "error",
            "message": (
                " Không thể tìm kiếm trong tài liệu hiện tại. "
                "Vui lòng thử lại sau."
            ),
            "error": str(e),
        }

    if not results:
        print(" KHÔNG TÌM THẤY TÀI LIỆU")
        return _youtube_fallback(query)

    # Chroma distance: smaller = more similar
    best_score = results[0][1]

    print("QUERY:", query)
    print("BEST SCORE:", best_score)
    print(
        "TOP DOCUMENT:",
        results[0][0].page_content[:200]
    )


    if best_score >= NGUONG_LIEN_QUAN:

        print("⚠️ CÂU HỎI KHÔNG LIÊN QUAN ĐẾN TÀI LIỆU")
        print("🎥 CHUYỂN SANG YOUTUBE")

        return _youtube_fallback(query)


    context = "\n\n".join(
        doc.page_content
        for doc, score in results
    )

    prompt = f"""
Dựa vào tài liệu sau, hãy trả lời câu hỏi của học sinh
một cách rõ ràng, dễ hiểu.

Chỉ sử dụng thông tin có trong tài liệu.
Nếu tài liệu không cung cấp đủ thông tin để trả lời,
hãy nói rõ rằng tài liệu không có đủ thông tin.

TÀI LIỆU:
{context}

CÂU HỎI:
{query}
"""

    print(" ĐÃ TÌM THẤY TÀI LIỆU")
    print(" ĐANG GỌI GEMINI...")

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        print(" GEMINI TRẢ LỜI THÀNH CÔNG")

        return {
            "type": "rag_answer",
            "answer": response.text,
            "source": "Dựa trên tài liệu bạn đã upload",
        }

    except Exception as e:

        print(" GEMINI LỖI:", type(e).__name__)
        print(" CHI TIẾT:", e)
        print(" CHUYỂN SANG YOUTUBE")

        return _youtube_fallback(query)