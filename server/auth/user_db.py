# Cơ sở dữ liệu tài khoản cục bộ
USERS = {'admin': 'password123', 'anonymous': ''}

def authenticate(username, password) -> bool:
    # Hàm xác thực tài khoản USER/PASS
    return USERS.get(username) == password
