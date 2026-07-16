import bcrypt


def hash_password(password: str) -> str:
    """Хэширование пароля с солью bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
