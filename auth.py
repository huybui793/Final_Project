import re

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Mật khẩu phải có ít nhất 8 ký tự")
    if not re.search(r'[A-Z]', password):
        errors.append("Mật khẩu phải có ít nhất 1 chữ hoa")
    if not re.search(r'[a-z]', password):
        errors.append("Mật khẩu phải có ít nhất 1 chữ thường")
    if not re.search(r'[0-9]', password):
        errors.append("Mật khẩu phải có ít nhất 1 chữ số")
    return len(errors) == 0, errors