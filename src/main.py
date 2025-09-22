from flask import Flask, request, jsonify, session
from flask_cors import CORS
from models.user import User
from models.transaction import Transaction
from models.group import Group
import sqlite3
import os
from datetime import datetime

# 導入路由
from routes.auth import auth_bp
from routes.group import group_bp
from routes.transaction import transaction_bp
from routes.category import category_bp
from routes.user import user_bp
# from routes.invoice import invoice_bp  # 暫時註釋，需要CNS資安認證

app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # 在生產環境中設為 True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24小時
app.config['JSON_AS_ASCII'] = False # 解決中文亂碼問題

# 修復的CORS設定
CORS(app, 
     origins=[
         "https://expense-tracker-frontend-git-tau.vercel.app",  # 您的Vercel域名
         "https://*.vercel.app",  # 允許所有Vercel域名
         "https://expense-tracker-frontend-nepkprh05-mops-projects-fff61921.vercel.app",  # 您的完整Vercel域名
         "http://localhost:3000",  # 本地開發
         "http://localhost:5173"   # Vite開發伺服器
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# 註冊藍圖
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(group_bp, url_prefix='/api')
app.register_blueprint(transaction_bp, url_prefix='/api')
app.register_blueprint(category_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api')
# app.register_blueprint(invoice_bp, url_prefix='/api/invoice')  # 暫時註釋，需要CNS資安認證

# 註冊 API 配置藍圖
from routes.api_config import api_config_bp
app.register_blueprint(api_config_bp, url_prefix='/api/config')

# 註冊 Google OAuth 藍圖
from routes.google_auth import google_auth_bp
app.register_blueprint(google_auth_bp, url_prefix='/api/auth')

# 資料庫路徑
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')

def get_db_connection():
    """獲取資料庫連接"""
    return sqlite3.connect(DATABASE_PATH)

def init_database():
    """初始化資料庫"""
    db = get_db_connection()
    
    # 初始化所有模型
    transaction_model = Transaction(db)
    user_model = User(db)
    group_model = Group(db)
    
    # 初始化發票相關資料表
    from models.invoice import init_invoice_tables
    init_invoice_tables()
    
    # 創建用戶分類表
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, name)
        )
    ''')
    
    # 創建預設用戶（如果不存在）
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # 創建預設用戶
        default_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'full_name': '系統管理員',
                'password': 'admin123'
            },
            {
                'username': 'demo',
                'email': 'demo@example.com', 
                'full_name': '示範用戶',
                'password': 'demo123'
            }
        ]
        
        for user_data in default_users:
            result = user_model.create_user(**user_data)
            if result.get('success') and result.get('user_id'):
                # 為新用戶創建預設分類
                user_id = result['user_id']
                # 為用戶創建預設分類
                create_default_categories_for_user(user_id, db)
            # 創建預設用戶
    
    db.commit()
    db.close()
    # 資料庫初始化完成

def create_default_categories_for_user(user_id, db):
    """為用戶創建預設分類"""
    default_categories = ['餐飲', '交通', '購物', '娛樂', '薪資', '投資', '載具']
    cursor = db.cursor()
    
    for category_name in default_categories:
        try:
            cursor.execute('''
                INSERT INTO user_categories (user_id, name, is_default)
                VALUES (?, ?, 1)
            ''', (user_id, category_name))
        except sqlite3.IntegrityError:
            # 分類已存在，跳過
            pass

def require_login():
    """檢查登入狀態的裝飾器函數"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id

# 導入交易路由
from routes.transaction import transaction_bp

# 註冊藍圖

# 分類管理API
@app.route('/api/categories', methods=['GET'])
def get_user_categories():
    """獲取用戶的分類列表"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT name FROM user_categories 
            WHERE user_id = ? 
            ORDER BY is_default DESC, name ASC
        ''', (user_id,))
        
        categories = [row[0] for row in cursor.fetchall()]
        db.close()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取分類失敗: {str(e)}"
        }), 500

@app.route('/api/categories', methods=['POST'])
def add_user_category():
    """新增用戶分類"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({
                'success': False,
                'message': '分類名稱不能為空'
            }), 400
        
        db = get_db_connection()
        cursor = db.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_categories (user_id, name, is_default)
                VALUES (?, ?, 0)
            ''', (user_id, category_name))
            
            db.commit()
            db.close()
            
            return jsonify({
                'success': True,
                'message': '分類新增成功'
            }), 201
            
        except sqlite3.IntegrityError:
            db.close()
            return jsonify({
                'success': False,
                'message': '分類已存在'
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"新增分類失敗: {str(e)}"
        }), 500

@app.route('/api/categories/<category_name>', methods=['DELETE'])
def delete_user_category(category_name):
    """刪除用戶分類"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # 檢查是否為預設分類
        cursor.execute('''
            SELECT is_default FROM user_categories 
            WHERE user_id = ? AND name = ?
        ''', (user_id, category_name))
        
        result = cursor.fetchone()
        if not result:
            db.close()
            return jsonify({
                'success': False,
                'message': '分類不存在'
            }), 404
        
        if result[0]:  # is_default = 1
            db.close()
            return jsonify({
                'success': False,
                'message': '不能刪除預設分類'
            }), 400
        
        cursor.execute('''
            DELETE FROM user_categories 
            WHERE user_id = ? AND name = ?
        ''', (user_id, category_name))
        
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': '分類刪除成功'
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"刪除分類失敗: {str(e)}"
        }), 500

# 統計API
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """獲取統計數據"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        group_id = request.args.get('group_id')
        
        db = get_db_connection()
        transaction_model = Transaction(db)
        
        if group_id:
            # 檢查群組權限
            cursor = db.cursor()
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, user_id))
            
            if not cursor.fetchone():
                db.close()
                return jsonify({
                    "success": False, 
                    "message": "您不是該群組成員"
                }), 403
            
            stats = transaction_model.get_group_statistics(group_id)
        else:
            stats = transaction_model.get_user_statistics(user_id)
        
        db.close()
        
        return jsonify({
            "success": True,
            "statistics": stats
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取統計數據失敗: {str(e)}"
        }), 500

# 健康檢查
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }), 200

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "message": "API 端點不存在"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "message": "伺服器內部錯誤"
    }), 500

if __name__ == '__main__':
    # 初始化資料庫
    init_database()
    
    # 獲取端口（雲端平台會提供PORT環境變數）
    import os
    port = int(os.environ.get('PORT', 8080))
    
    # 啟動應用程式
    app.run(host='0.0.0.0', port=port, debug=False)
