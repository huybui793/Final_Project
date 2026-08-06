from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_and_split_pdf(file_path):
    # Bước 1: Đọc nội dung từ file PDF
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Bước 2: Chia nhỏ văn bản thành từng đoạn (chunk)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # mỗi đoạn khoảng 500 ký tự
        chunk_overlap=50     # 2 đoạn liền kề overlap 50 ký tự (tránh cắt đứt ý)
    )
    chunks = text_splitter.split_documents(documents)
    
    return chunks

if __name__ == "__main__":
    chunks = load_and_split_pdf("test.pdf")  # đổi thành đường dẫn file PDF của bạn
    print(f"Số lượng đoạn (chunks): {len(chunks)}")
    print("--- Đoạn đầu tiên ---")
    print(chunks[0].page_content)