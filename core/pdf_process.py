import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

def add_documents_to_store(vector_store, chunks, batch_size=20, delay=5):
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vector_store.add_documents(batch)
        if i + batch_size < len(chunks):  # nếu còn batch tiếp theo
            time.sleep(delay)  # nghỉ trước khi gửi tiếp, tránh vượt hạn mức

def load_and_split_pdf(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    
    return chunks

def create_vector_store(persist_directory="chroma_db"):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    vector_store = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vector_store

def add_documents_to_store(vector_store, chunks):
    vector_store.add_documents(chunks)