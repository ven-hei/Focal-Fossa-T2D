import sqlite3

# Kết nối đến SQLite
conn = sqlite3.connect('Database/database.db')
cursor = conn.cursor()

# Xóa bảng cũ (nếu có) và tạo lại với các cột mới
cursor.execute("DROP TABLE IF EXISTS users")

cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    age INTEGER,
    height REAL,
    weight REAL
)
''')

# Chèn dữ liệu mẫu với các trường mới
users_data = [
    ("Nguyễn Văn A", "a@example.com", "0987654321", 25, 170, 65),
    ("Trần Thị B", "b@example.com", "0912345678", 30, 160, 55),
    ("Lê Văn C", "c@example.com", "0901122334", 28, 175, 70),
    ("Hoàng Văn D", "d@example.com", "0934567890", 35, 180, 80),
    ("Phạm Thị E", "e@example.com", "0976543210", 22, 165, 50)
]

cursor.executemany("INSERT INTO users (name, email, phone, age, height, weight) VALUES (?, ?, ?, ?, ?, ?)", users_data)
conn.commit()
conn.close()

print("Database đã được cập nhật với các trường mới và dữ liệu mẫu.")
