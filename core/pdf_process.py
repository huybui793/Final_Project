import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, create_kv_docstore

load_dotenv()


def load_and_split_pdf(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    return documents


def create_vector_store(persist_directory="chroma_db"):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    vector_store = Chroma(
        collection_name="parent_child_chunks",
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vector_store


def create_retriever(vector_store, store_directory="parent_docs_store"):
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

    fs = LocalFileStore(store_directory)
    store = create_kv_docstore(fs)

    retriever = ParentDocumentRetriever(
        vectorstore=vector_store,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    return retriever


def add_documents_to_retriever(retriever, documents, batch_size=3, delay=20, max_retries=5):
    total = len(documents)
    for i in range(0, total, batch_size):
        batch = documents[i:i + batch_size]

        retry_count = 0
        while retry_count < max_retries:
            try:
                retriever.add_documents(batch)
                print(f"Đã xử lý {min(i + batch_size, total)}/{total} trang")
                break
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    retry_count += 1
                    wait_time = 30 * retry_count
                    print(f"Vượt quota, đợi {wait_time}s rồi thử lại (lần {retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise

        if retry_count >= max_retries:
            raise Exception(f"Không thể xử lý batch sau {max_retries} lần thử, vượt quota liên tục.")

        if i + batch_size < total:
            time.sleep(delay)