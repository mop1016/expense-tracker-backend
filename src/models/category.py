import sqlite3
from datetime import datetime

class UserCategory:
    """用戶分類模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_table()
    
    def create_table(self):
        """創建用戶分類表"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, name)
            )
        ''')
        self.db.commit()
    
    @staticmethod
    def get_user_categories(user_id):
        """獲取用戶的所有分類"""
        import sqlite3
        import os
        
        # 獲取資料庫連接
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database.db")
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        cursor.execute('''
            SELECT id, user_id, name, is_default, created_at
            FROM user_categories 
            WHERE user_id = ? 
            ORDER BY name
        ''', (user_id,))
        
        rows = cursor.fetchall()
        db.close()
        
        categories = []
        for row in rows:
            categories.append({
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'is_default': row[3],
                'created_at': row[4]
            })
        
        return categories
    
    @staticmethod
    def add_user_category(user_id, category_name):
        """為用戶新增分類"""
        import sqlite3
        import os
        
        # 獲取資料庫連接
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        
        # 檢查是否已存在
        cursor.execute('''
            SELECT id FROM user_categories 
            WHERE user_id = ? AND name = ?
        ''', (user_id, category_name))
        
        if cursor.fetchone():
            db.close()
            return None, "分類已存在"
        
        # 新增分類
        try:
            cursor.execute('''
                INSERT INTO user_categories (user_id, name, is_default, created_at)
                VALUES (?, ?, 0, CURRENT_TIMESTAMP)
            ''', (user_id, category_name))
            
            category_id = cursor.lastrowid
            db.commit()
            db.close()
            
            return {
                'id': category_id,
                'user_id': user_id,
                'name': category_name,
                'is_default': False
            }, None
            
        except sqlite3.IntegrityError:
            db.close()
            return None, "分類已存在"
    
    @staticmethod
    def delete_user_category(user_id, category_name):
        """刪除用戶分類（不能刪除預設分類）"""
        import sqlite3
        import os
        
        # 獲取資料庫連接
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        
        # 檢查分類是否存在且是否為預設分類
        cursor.execute('''
            SELECT id, is_default FROM user_categories 
            WHERE user_id = ? AND name = ?
        ''', (user_id, category_name))
        
        row = cursor.fetchone()
        if not row:
            db.close()
            return False, "分類不存在"
        
        if row[1]:  # is_default
            db.close()
            return False, "不能刪除預設分類"
        
        # 刪除分類
        cursor.execute('''
            DELETE FROM user_categories 
            WHERE user_id = ? AND name = ?
        ''', (user_id, category_name))
        
        db.commit()
        db.close()
        
        return True, None

class GroupCategory:
    """群組分類模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_table()
    
    def create_table(self):
        """創建群組分類表"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                is_inherited BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id),
                FOREIGN KEY (created_by) REFERENCES users (id),
                UNIQUE(group_id, name)
            )
        ''')
        self.db.commit()
    
    @staticmethod
    def get_group_categories(group_id):
        """獲取群組的所有分類"""
        import sqlite3
        import os
        
        # 獲取資料庫連接
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database.db")
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        cursor.execute('''
            SELECT id, group_id, name, created_by, is_inherited, created_at
            FROM group_categories 
            WHERE group_id = ? 
            ORDER BY name
        ''', (group_id,))
        
        rows = cursor.fetchall()
        db.close()
        
        categories = []
        for row in rows:
            categories.append({
                'id': row[0],
                'group_id': row[1],
                'name': row[2],
                'created_by': row[3],
                'is_inherited': row[4],
                'created_at': row[5]
            })
        
        return categories
    
    @staticmethod
    def add_group_category(group_id, user_id, category_name):
        """為群組新增分類"""
        import sqlite3
        import os
        
        # 獲取資料庫連接
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database.db")
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        
        # 檢查是否已存在
        cursor.execute('''
            SELECT id FROM group_categories 
            WHERE group_id = ? AND name = ?
        ''', (group_id, category_name))
        
        if cursor.fetchone():
            db.close()
            return None, "分類已存在"
        
        # 新增分類
        try:
            cursor.execute('''
                INSERT INTO group_categories (group_id, name, created_by, is_inherited, created_at)
                VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
            ''', (group_id, category_name, user_id))
            
            category_id = cursor.lastrowid
            db.commit()
            db.close()
            
            return {
                'id': category_id,
                'group_id': group_id,
                'name': category_name,
                'created_by': user_id,
                'is_inherited': False
            }, None
            
        except sqlite3.IntegrityError:
            db.close()
            return None, "分類已存在"

