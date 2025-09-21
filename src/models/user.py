import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

class User:
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_table()
    
    def create_table(self):
        """創建用戶表"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                avatar_url VARCHAR(255),
                is_active BOOLEAN DEFAULT 1,
                email_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                settings TEXT DEFAULT '{}',
                bio TEXT
            )
        ''')
        self.db.commit()
    
    def validate_email(self, email):
        """驗證電子郵件格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password):
        """驗證密碼強度"""
        if len(password) < 6:
            return False, "密碼長度至少需要6個字符"
        if not re.search(r'[A-Za-z]', password):
            return False, "密碼需要包含字母"
        if not re.search(r'[0-9]', password):
            return False, "密碼需要包含數字"
        return True, "密碼符合要求"
    
    def create_user(self, username, email, full_name, password, phone=None):
        """創建新用戶"""
        try:
            # 驗證輸入
            if not username or len(username) < 3:
                return {"success": False, "message": "用戶名至少需要3個字符"}
            
            if not self.validate_email(email):
                return {"success": False, "message": "電子郵件格式不正確"}
            
            if not full_name or len(full_name) < 2:
                return {"success": False, "message": "姓名至少需要2個字符"}
            
            is_valid, message = self.validate_password(password)
            if not is_valid:
                return {"success": False, "message": message}
            
            # 檢查用戶名和郵箱是否已存在
            cursor = self.db.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                return {"success": False, "message": "用戶名或電子郵件已存在"}
            
            # 創建用戶
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, email, full_name, password_hash, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, full_name, password_hash, phone, datetime.now(), datetime.now()))
            
            user_id = cursor.lastrowid
            self.db.commit()
            
            return {
                "success": True, 
                "message": "用戶創建成功",
                "user_id": user_id,
                "user": self.get_user_by_id(user_id)
            }
            
        except Exception as e:
            return {"success": False, "message": f"創建用戶失敗: {str(e)}"}
    
    def authenticate_user(self, username_or_email, password):
        """用戶登入驗證"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, password_hash, is_active
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username_or_email, username_or_email))
            
            user = cursor.fetchone()
            if not user:
                return {"success": False, "message": "用戶不存在或已被停用"}
            
            if not check_password_hash(user[4], password):
                return {"success": False, "message": "密碼錯誤"}
            
            # 更新最後登入時間
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                         (datetime.now(), user[0]))
            self.db.commit()
            
            return {
                "success": True,
                "message": "登入成功",
                "user": {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "full_name": user[3],
                    "is_active": user[5]
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"登入失敗: {str(e)}"}
    
    def get_user_by_id(self, user_id):
        """根據ID獲取用戶信息"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, phone, avatar_url, 
                       is_active, email_verified, created_at, last_login, bio
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return None
            
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "full_name": user[3],
                "phone": user[4],
                "avatar_url": user[5],
                "is_active": user[6],
                "email_verified": user[7],
                "created_at": user[8],
                "last_login": user[9],
                "bio": user[10]
            }
            
        except Exception as e:
            # 獲取用戶信息失敗
            return None
    
    def get_user_by_username(self, username):
        """根據用戶名獲取用戶信息"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, phone, avatar_url, 
                       is_active, email_verified, created_at, last_login, bio
                FROM users WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            if not user:
                return None
            
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "full_name": user[3],
                "phone": user[4],
                "avatar_url": user[5],
                "is_active": user[6],
                "email_verified": user[7],
                "created_at": user[8],
                "last_login": user[9],
                "bio": user[10]
            }
            
        except Exception as e:
            # 獲取用戶信息失敗
            return None
    
    def search_users_by_name(self, name_query, limit=10):
        """根據姓名搜索用戶"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT id, username, full_name, email, avatar_url
                FROM users 
                WHERE full_name LIKE ? AND is_active = 1
                ORDER BY full_name
                LIMIT ?
            ''', (f'%{name_query}%', limit))
            
            users = cursor.fetchall()
            return [
                {
                    "id": user[0],
                    "username": user[1],
                    "full_name": user[2],
                    "email": user[3],
                    "avatar_url": user[4]
                }
                for user in users
            ]
            
        except Exception as e:
            # 搜索用戶失敗
            return []
    
    def update_user_profile(self, user_id, **kwargs):
        """更新用戶資料"""
        try:
            allowed_fields = ['full_name', 'phone', 'avatar_url', 'bio']
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return {"success": False, "message": "沒有可更新的欄位"}
            
            values.append(datetime.now())
            values.append(user_id)
            
            cursor = self.db.cursor()
            cursor.execute(f'''
                UPDATE users 
                SET {', '.join(update_fields)}, updated_at = ?
                WHERE id = ?
            ''', values)
            
            self.db.commit()
            
            if cursor.rowcount > 0:
                return {
                    "success": True, 
                    "message": "用戶資料更新成功",
                    "user": self.get_user_by_id(user_id)
                }
            else:
                return {"success": False, "message": "用戶不存在"}
                
        except Exception as e:
            return {"success": False, "message": f"更新用戶資料失敗: {str(e)}"}
    
    def change_password(self, user_id, old_password, new_password):
        """修改密碼"""
        try:
            # 驗證舊密碼
            cursor = self.db.cursor()
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user or not check_password_hash(user[0], old_password):
                return {"success": False, "message": "舊密碼錯誤"}
            
            # 驗證新密碼
            is_valid, message = self.validate_password(new_password)
            if not is_valid:
                return {"success": False, "message": message}
            
            # 更新密碼
            new_password_hash = generate_password_hash(new_password)
            cursor.execute('''
                UPDATE users 
                SET password_hash = ?, updated_at = ?
                WHERE id = ?
            ''', (new_password_hash, datetime.now(), user_id))
            
            self.db.commit()
            
            return {"success": True, "message": "密碼修改成功"}
            
        except Exception as e:
            return {"success": False, "message": f"修改密碼失敗: {str(e)}"}
    
    def get_all_users(self, page=1, per_page=20):
        """獲取所有用戶列表（分頁）"""
        try:
            offset = (page - 1) * per_page
            cursor = self.db.cursor()
            
            # 獲取總數
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            total = cursor.fetchone()[0]
            
            # 獲取用戶列表
            cursor.execute('''
                SELECT id, username, full_name, email, created_at, last_login
                FROM users 
                WHERE is_active = 1
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            users = cursor.fetchall()
            
            return {
                "users": [
                    {
                        "id": user[0],
                        "username": user[1],
                        "full_name": user[2],
                        "email": user[3],
                        "created_at": user[4],
                        "last_login": user[5]
                    }
                    for user in users
                ],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            # 獲取用戶列表失敗
            return {"users": [], "total": 0, "page": 1, "per_page": per_page, "pages": 0}

