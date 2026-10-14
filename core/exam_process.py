import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def is_history_document(text_sample):
    prompt = f"""Đoạn văn bản sau có thuộc lĩnh vực Lịch sử không (sự kiện lịch sử, nhân vật lịch sử, giai đoạn lịch sử...)?

Đoạn văn bản:
{text_sample[:2000]}

Trả lời CHÍNH XÁC một từ duy nhất: "YES" nếu là tài liệu Lịch sử, "NO" nếu không phải.
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return "YES" in response.text.strip().upper()


def generate_exam_questions(context, num_questions=5):
    prompt = f"""Dựa vào đoạn tài liệu sau, hãy tạo {num_questions} câu hỏi trắc nghiệm cho bài kiểm tra.

Tài liệu:
{context}

Hãy chia các câu hỏi vào 2-3 chủ đề chính. Các câu cùng nhóm phải dùng ĐÚNG CÙNG MỘT tên chủ đề (viết giống hệt nhau từng ký tự).
Trả về CHÍNH XÁC theo định dạng JSON, không thêm text nào khác ngoài JSON:
[
  {{
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_answer": "A",
    "topic": "Tên chủ đề ngắn gọn"
  }}
]
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())