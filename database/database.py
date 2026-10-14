import os
import hashlib
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["history_ai_assistant"]

users_col = db["users"]
chats_col = db["chats"]
messages_col = db["messages"]
exams_col = db["exams"]
exam_submissions_col = db["exam_submissions"]
quiz_results_col = db["quiz_results"]


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# --- Users ---
def register_user(user_id, email, password, name, role):
    if users_col.find_one({"email": email}):
        return False
    users_col.insert_one({
        "user_id": user_id,
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "role": role
    })
    return True


def verify_login(email, password):
    user = users_col.find_one({"email": email, "password_hash": hash_password(password)})
    if user:
        return user["user_id"], user.get("name", ""), user.get("role", "student")
    return None, None, None


# --- Chats ---
def create_chat(chat_id, user_id, title="Cuộc trò chuyện mới"):
    chats_col.insert_one({"chat_id": chat_id, "user_id": user_id, "title": title})


def update_chat_title(chat_id, title):
    chats_col.update_one({"chat_id": chat_id}, {"$set": {"title": title}})


def add_message(chat_id, role, content):
    messages_col.insert_one({
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })


def get_all_chats(user_id):
    results = chats_col.find({"user_id": user_id}).sort("_id", -1)
    return [(c["chat_id"], c["title"]) for c in results]


def get_messages(chat_id):
    results = messages_col.find({"chat_id": chat_id}).sort("_id", 1)
    return [{"role": m["role"], "content": m["content"]} for m in results]


# --- Exams ---
def create_exam(exam_id, teacher_id, title, questions):
    exams_col.insert_one({
        "exam_id": exam_id,
        "teacher_id": teacher_id,
        "title": title,
        "questions": questions,
        "created_at": datetime.now().isoformat()
    })


def get_all_exams():
    results = exams_col.find().sort("_id", -1)
    return list(results)


def get_exam_by_id(exam_id):
    return exams_col.find_one({"exam_id": exam_id})


def submit_exam(exam_id, student_id, answers, score, total):
    exam_submissions_col.insert_one({
        "exam_id": exam_id,
        "student_id": student_id,
        "answers": answers,
        "score": score,
        "total": total,
        "submitted_at": datetime.now().isoformat()
    })


# --- Quiz results / Knowledge gap ---
def save_quiz_result(user_id, topic, question, is_correct):
    quiz_results_col.insert_one({
        "user_id": user_id,
        "topic": topic,
        "question": question,
        "is_correct": is_correct,
        "timestamp": datetime.now().isoformat()
    })


def get_weak_topics(user_id, min_wrong=2):
    pipeline = [
        {"$match": {"user_id": user_id, "is_correct": False}},
        {"$group": {"_id": "$topic", "wrong_count": {"$sum": 1}}},
        {"$match": {"wrong_count": {"$gte": min_wrong}}},
        {"$sort": {"wrong_count": -1}}
    ]
    results = list(quiz_results_col.aggregate(pipeline))
    return [(r["_id"], r["wrong_count"]) for r in results]

def get_topic_stats(user_id):
    """Tổng số câu và số câu đúng theo từng chủ đề, trên mọi bài đã làm."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$topic",
            "total": {"$sum": 1},
            "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
        }},
        {"$sort": {"total": -1}},
    ]
    return [
        {"topic": r["_id"], "total": r["total"], "correct": r["correct"]}
        for r in quiz_results_col.aggregate(pipeline)
    ]