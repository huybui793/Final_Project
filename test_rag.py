
import shutil
from pathlib import Path

from core.pdf_process import (
    load_and_split_pdf,
    create_vector_store,
    create_retriever,
    add_documents_to_retriever,
)
from core.rag_pipeline import answer_question


# =========================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN TEST
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# Đường dẫn PDF dùng để kiểm thử.
# Nếu PDF của bạn nằm ở vị trí khác, hãy sửa biến này.
PDF_PATH = Path(r"D:\Repo\FinalProject\data\test_data.pdf")

# Database chỉ dành riêng cho kiểm thử.
CHROMA_TEST_DIR = BASE_DIR / "chroma_test_db"
PARENT_TEST_DIR = BASE_DIR / "parent_docs_test_store"


# =========================================================
# 2. HÀM IN TIÊU ĐỀ
# =========================================================

def print_section(title):
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)


# =========================================================
# 3. XÓA DỮ LIỆU TEST CŨ
# =========================================================

def clean_test_database():
    print_section("[1] DỌN DỮ LIỆU TEST CŨ")

    test_folders = [
        CHROMA_TEST_DIR,
        PARENT_TEST_DIR,
    ]

    for folder in test_folders:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"Đã xóa: {folder.name}")
        else:
            print(f"Chưa tồn tại: {folder.name}")

    print("Hoàn tất dọn dữ liệu test.")


# =========================================================
# 4. ĐỌC PDF
# =========================================================

def load_pdf():
    print_section("[2] ĐỌC TÀI LIỆU PDF")

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy PDF: {PDF_PATH}\n"
            "Hãy sửa biến PDF_PATH cho đúng vị trí file PDF."
        )

    print(f"File PDF: {PDF_PATH.name}")

    documents = load_and_split_pdf(str(PDF_PATH))

    if not documents:
        raise ValueError(
            "Không đọc được nội dung từ PDF. "
            "Hãy kiểm tra file PDF."
        )

    print(f"Số trang/đoạn đọc được: {len(documents)}")

    return documents


# =========================================================
# 5. KHỞI TẠO CHROMA VÀ RETRIEVER
# =========================================================

def initialize_rag(documents):
    vector_store = create_vector_store(
        persist_directory=str(CHROMA_TEST_DIR)
    )

    retriever = create_retriever(
        vector_store,
        store_directory=str(PARENT_TEST_DIR),
    )

    add_documents_to_retriever(retriever, documents)

    return vector_store, retriever


# =========================================================
# 6. KIỂM TRA TRUY XUẤT VECTOR STORE
# =========================================================

def test_retrieval(vector_store, query):
    print_section("[4] KIỂM TRA TRUY XUẤT")

    print("Câu hỏi:", query)

    results = vector_store.similarity_search_with_score(
        query,
        k=2,
    )

    print(f"\nSố kết quả tìm kiếm: {len(results)}")

    for index, (doc, score) in enumerate(results, start=1):
        print(f"\n--- Kết quả {index} | score={score:.4f} ---")
        print(doc.page_content[:600])

    if not results:
        print("CẢNH BÁO: Không tìm thấy kết quả.")

    return results


# =========================================================
# 7. KIỂM TRA RETRIEVER LẤY TÀI LIỆU CHA
# =========================================================

def test_parent_retriever(retriever, query):
    print_section("[5] KIỂM TRA TÀI LIỆU CHA")

    parent_docs = retriever.invoke(query)

    print(f"Số tài liệu cha truy xuất được: {len(parent_docs)}")

    for index, doc in enumerate(parent_docs[:3], start=1):
        print(f"\n--- Tài liệu cha {index} ---")
        print(doc.page_content[:1000])

    return parent_docs


# =========================================================
# 8. KIỂM TRA TOÀN BỘ LUỒNG RAG
# =========================================================

def test_full_rag(retriever, vector_store, query):
    print_section("[6] KIỂM TRA TOÀN BỘ HÀM RAG")

    print("Câu hỏi:", query)

    result = answer_question(
        retriever,
        vector_store,
        query,
    )

    result_type = result.get("type")

    print("\nLoại kết quả:", result_type)
    print("Câu trả lời:", result.get("answer"))
    print("Thông báo:", result.get("message"))

    # Nếu câu hỏi đi vào nhánh YouTube,
    # kiểm tra xem có video được trả về không.
    if result_type == "youtube_fallback":
        videos = result.get("videos") or []

        print(f"\nSố video tìm được: {len(videos)}")

        for index, video in enumerate(videos, start=1):
            print(f"\n--- Video {index} ---")
            print(video)

        if videos:
            print("\nKẾT QUẢ YOUTUBE: Có dữ liệu video.")
        else:
            print(
                "\nCẢNH BÁO: Không có video. "
                "Hãy kiểm tra core/ytb_process.py "
                "và cấu hình API tìm kiếm."
            )

    return result


# =========================================================
# 9. CHẠY KIỂM THỬ
# =========================================================

def main():
    try:
        # Xóa dữ liệu test cũ.
        clean_test_database()

        # Đọc PDF.
        documents = load_pdf()

        # Khởi tạo Chroma và Retriever.
        vector_store, retriever = initialize_rag(documents)

        # Câu hỏi có trong tài liệu.
        relevant_query = (
            "Theo tài liệu, vì sao thắng lợi "
            "Cách mạng Tháng Tám năm 1945 "
            "không phải là sự ngẫu nhiên?"
        )

        # Câu hỏi không có trong tài liệu.
        unrelated_query = (
            "Cách viết ứng dụng React "
            "bằng JavaScript như thế nào?"
        )

        # Test 1: Kiểm tra truy xuất và RAG.
        test_retrieval(
            vector_store,
            relevant_query,
        )

        test_parent_retriever(
            retriever,
            relevant_query,
        )

        relevant_result = test_full_rag(
            retriever,
            vector_store,
            relevant_query,
        )

        # Test 2: Kiểm tra câu hỏi ngoài phạm vi tài liệu.
        test_retrieval(
            vector_store,
            unrelated_query,
        )

        unrelated_result = test_full_rag(
            retriever,
            vector_store,
            unrelated_query,
        )

        # Tổng kết.
        print_section("[7] TỔNG KẾT KIỂM THỬ")

        relevant_pass = (
            relevant_result.get("type") == "rag_answer"
        )

        unrelated_pass = (
            unrelated_result.get("type") == "youtube_fallback"
        )

        print(
            "Câu hỏi liên quan tài liệu:",
            "PASS" if relevant_pass else "FAIL",
        )

        print(
            "Câu hỏi ngoài tài liệu:",
            "PASS" if unrelated_pass else "FAIL",
        )

        if relevant_pass and unrelated_pass:
            print("\nĐÃ VƯỢT QUA 2 KIỂM THỬ PHÂN LUỒNG CƠ BẢN.")
        else:
            print(
                "\nCÓ KIỂM THỬ CHƯA ĐẠT. "
                "Hãy xem các thông báo DEBUG phía trên."
            )

    except Exception as error:
        print_section("LỖI KHI KIỂM THỬ")
        print(f"{type(error).__name__}: {error}")
        raise


if __name__ == "__main__":
    main()
