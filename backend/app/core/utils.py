import hashlib

def normalize_email(email: str) -> str:
    return email.strip().lower()

def hash_str(str) -> str:
    return hashlib.sha256(str.encode()).hexdigest()
    