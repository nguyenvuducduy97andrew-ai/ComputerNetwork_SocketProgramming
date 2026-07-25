import json #import thư viện json để đọc file json
from pathlib import Path #import thư viện pathlib để thao tác với đường dẫn

USER_FILE = Path(__file__).resolve().parent / "user.json"

def load_user() -> dict:
    with USER_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)

def user_exists(username: str) -> bool:
    print(f"[user_db] JSON path: {USER_FILE}")
    print(f"[user_db] File exists: {USER_FILE.exists()}")

    users = load_user()

    print(f"[user_db] Loaded users: {list(users.keys())}")
    print(f"[user_db] Checking username: {username!r}")

    return username in users

def authenticate(username: str, password: str) -> bool:
    if username is None or password is None:
        return False
    users = load_user()
    if username not in users:
        return False
    return users[username].get("password") == password





