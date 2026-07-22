# # Cơ sở dữ liệu tài khoản cục bộ
# USERS = {'admin': 'password123', 'anonymous': ''}

# def authenticate(username, password) -> bool:
#     # Hàm xác thực tài khoản USER/PASS
#     return USERS.get(username) == password

import json #import thư viện json để đọc file json
from pathlib import Path #import thư viện pathlib để thao tác với đường dẫn

USERS_FILES = [
    Path(__file__).parent / "user.json",
]


def load_user() -> dict[str, str]:
    """Load users from either `user.json` or `users.json` and return a mapping username->password.

    Supported JSON formats:
    - { "user": "password", ... }
    - { "user": { "password": "..." }, ... }
    """
    for p in USERS_FILES:
        try:
            with p.open(mode="r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as error:
            print(f"Error: Invalid {p.name} -> {error}")
            return {}

        if not isinstance(data, dict):
            print(f"Error: {p.name} must contain a JSON object")
            return {}

        # Normalize formats
        normalized: dict[str, str] = {}
        for user, val in data.items():
            if isinstance(val, str):
                normalized[user] = val
            elif isinstance(val, dict) and "password" in val:
                normalized[user] = val.get("password") or ""
            else:
                # Unknown entry format, skip
                continue

        return normalized

    # No file found
    print(f"Database not found: tried {[p.name for p in USERS_FILES]}")
    return {}


def authenticate(username: str, password: str) -> bool:
    users = load_user()
    if username is None:
        return False
    return users.get(username) == password


