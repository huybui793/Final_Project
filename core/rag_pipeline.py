
import re
from langchain_google_genai import ChatGoogleGenerativeAI

from core.ytb_process import search_youtube_videos


# ============================================================
# CẤU HÌNH
# ============================================================

MODEL_NAME = "gemini-2.5-flash"

# Dùng ngưỡng ban đầu dựa trên log Chroma hiện tại.
# Với distance score, giá trị càng nhỏ thường càng gần.
MAX_DISTANCE = 0.75

# Các từ phổ biến không đủ để xác định chủ đề của câu hỏi.
STOP_WORDS = {
    "và", "là", "của", "có", "cho", "trong", "một",
    "những", "các", "được", "với", "từ", "đến", "khi",
    "thì", "mà", "này", "đó", "theo", "vì", "do",
    "về", "tại", "sau", "trước", "nào", "như", "sao",
    "thế", "nào", "cách", "viết", "làm", "sử", "dụng",
    "ứng", "bằng", "tài", "liệu", "năm", "không", "phải",
    "hay", "hoặc", "để", "ra", "đang", "đã", "sẽ",
    "bao", "nhiêu", "ai", "gì", "the", "and", "how",
    "what", "is", "are", "use", "using", "write", "make",
}


# ============================================================
# TIỆN ÍCH XỬ LÝ TỪ KHÓA
# ============================================================

def tokenize(text):
    """Tách từ, giữ nguyên dấu tiếng Việt."""
    return set(re.findall(r"[^\W_]+", str(text).lower()))


def check_relevance(vector_store, query):
    """
    Kiểm tra câu hỏi có liên quan đến tài liệu trong vector store không.

    Kết hợp:
    1. Distance score của kết quả tìm kiếm.
    2. Mức độ trùng khớp từ khóa đặc trưng.

    Trả về True nếu câu hỏi có đủ dấu hiệu liên quan.
    """
    try:
        results = vector_store.similarity_search_with_score(
            query,
            k=2,
        )
    except Exception as exc:
        print(f"[RELEVANCE] Lỗi tìm kiếm vector: {exc}")
        return False

    if not results:
        print("[RELEVANCE] Không tìm thấy tài liệu.")
        return False

    query_words = tokenize(query)
    specific_words = query_words - STOP_WORDS

    # Không có từ khóa đặc trưng thì không tự động đưa vào RAG.
    if not specific_words:
        print("[RELEVANCE] Không có từ khóa đặc trưng.")
        return False

    document_text = " ".join(
        doc.page_content
        for doc, score in results
        if getattr(doc, "page_content", None)
    )

    document_words = tokenize(document_text)
    matched_words = specific_words & document_words

    # similarity_search_with_score thường trả distance score.
    # Với cấu hình hiện tại, distance càng thấp càng gần.
    best_distance = min(float(score) for doc, score in results)

    is_relevant = (
        best_distance <= MAX_DISTANCE
        and len(matched_words) >= 2
    )

    print("\n========== DEBUG RELEVANCE ==========")
    print("Query:", query)
    print("Specific words:", sorted(specific_words))
    print("Matched words:", sorted(matched_words))
    print("Best distance:", round(best_distance, 4))
    print("Relevant:", is_relevant)
    print("=====================================\n")

    return is_relevant


# ============================================================
# YOUTUBE FALLBACK
# ============================================================

def youtube_fallback(query):
    """Tìm video YouTube khi câu hỏi không thuộc tài liệu."""
    try:
        videos = search_youtube_videos(query)

        if videos is None:
            videos = []

        return {
            "type": "youtube_fallback",
            "message": (
                "Câu hỏi chưa được xác định là có trong tài liệu. "
                "Dưới đây là các video YouTube có thể giúp bạn tìm hiểu thêm."
                if videos
                else
                "Không tìm thấy video phù hợp. "
                "Bạn có thể thử diễn đạt câu hỏi theo cách khác."
            ),
            "videos": videos,
        }

    except Exception as exc:
        print(f"[YOUTUBE] Lỗi tìm kiếm video: {exc}")

        return {
            "type": "youtube_fallback",
            "message": (
                "Câu hỏi nằm ngoài phạm vi tài liệu, nhưng hiện tại "
                "không thể tìm video YouTube. Vui lòng thử lại sau."
            ),
            "videos": [],
        }


# ============================================================
# SINH CÂU TRẢ LỜI TỪ TÀI LIỆU
# ============================================================

def generate_rag_answer(retriever, query):
    """Truy xuất tài liệu cha và dùng Gemini tạo câu trả lời."""
    documents = retriever.invoke(query)

    if not documents:
        return {
            "type": "rag_answer",
            "answer": (
                "Chưa tìm thấy đoạn tài liệu đủ phù hợp để trả lời "
                "câu hỏi này. Bạn hãy thử diễn đạt cụ thể hơn."
            ),
            "source": "",
        }

    # Giới hạn số tài liệu đưa vào prompt.
    selected_documents = documents[:3]

    context_parts = []
    sources = []

    for index, doc in enumerate(selected_documents, start=1):
        content = getattr(doc, "page_content", "")

        if content:
            context_parts.append(
                f"[Tài liệu {index}]\n{content}"
            )

        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("source") or metadata.get("file_path")

        if source and source not in sources:
            sources.append(source)

    context = "\n\n".join(context_parts)

    if not context.strip():
        return {
            "type": "rag_answer",
            "answer": "Không đọc được nội dung từ tài liệu truy xuất.",
            "source": "",
        }

    prompt = f"""
Bạn là trợ lý học tập môn Lịch sử.

Hãy trả lời câu hỏi dựa trên tài liệu được cung cấp.

Quy tắc:
- Ưu tiên thông tin có trong tài liệu.
- Không tự bịa ra ngày tháng, sự kiện hoặc dữ kiện.
- Nếu tài liệu không đủ thông tin để trả lời, hãy nói rõ điều đó.
- Trình bày bằng tiếng Việt, rõ ràng, dễ hiểu.
- Có thể dùng các gạch đầu dòng khi phù hợp.

NỘI DUNG TÀI LIỆU:
{context}

CÂU HỎI:
{query}

CÂU TRẢ LỜI:
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            temperature=0.2,
        )

        response = llm.invoke(prompt)
        answer = response.content

        # Một số phiên bản có thể trả về nội dung dạng danh sách.
        if isinstance(answer, list):
            answer = "\n".join(
                item.get("text", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in answer
            )

        return {
            "type": "rag_answer",
            "answer": str(answer),
            "source": ", ".join(sources),
        }

    except Exception as exc:
        print(f"[RAG] Lỗi khi gọi Gemini: {exc}")

        return {
            "type": "rag_answer",
            "answer": (
                "Đã tìm thấy tài liệu liên quan nhưng chưa thể tạo "
                "câu trả lời. Vui lòng thử lại sau."
            ),
            "source": ", ".join(sources),
            "error": str(exc),
        }


# ============================================================
# HÀM CHÍNH ĐƯỢC GỌI TỪ STREAMLIT VÀ TEST
# ============================================================

def answer_question(retriever, vector_store, query):
    """
    Luồng xử lý:
    - Câu hỏi liên quan tài liệu -> RAG + Gemini.
    - Câu hỏi ngoài tài liệu -> YouTube fallback.
    """
    query = str(query).strip()

    if not query:
        return {
            "type": "rag_answer",
            "answer": "Bạn hãy nhập câu hỏi trước nhé.",
            "source": "",
        }

    print("\n========== DEBUG RAG ==========")
    print("DEBUG query:", query)

    is_relevant = check_relevance(vector_store, query)

    print("DEBUG is_relevant:", is_relevant)
    print("================================\n")

    if is_relevant:
        result = generate_rag_answer(retriever, query)
        return result

    return youtube_fallback(query)
