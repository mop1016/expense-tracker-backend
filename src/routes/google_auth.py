from flask import Blueprint, request, jsonify, session
from google.oauth2 import id_token
from google.auth.transport import requests
import sqlite3
import os
from datetime import datetime

google_auth_bp = Blueprint('google_auth', __name__)

# Google OAuth 配置
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"  # 需要從Google Console獲取

def get_db_connection():
    """獲取資料庫連接"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
    return sqlite3.connect(db_path)

def create_or_get_google_user(google_user_info):
    """創建或獲取Google用戶"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        email = google_user_info['email']
        name = google_user_info['name']
        google_id = google_user_info['sub']
        picture = google_user_info.get('picture', '')
        
        # 檢查用戶是否已存在
        cursor.execute('SELECT id, username, email, full_name FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # 更新最後登入時間
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                         (datetime.now(), existing_user[0]))
            db.commit()
            db.close()
            
            return {
                "success": True,
                "user": {
                    "id": existing_user[0],
                    "username": existing_user[1],
                    "email": existing_user[2],
                    "full_name": existing_user[3],
                    "is_google_user": True
                }
            }
        else:
            # 創建新的Google用戶
            username = email.split('@')[0]  # 使用email前綴作為用戶名
            
            # 確保用戶名唯一
            counter = 1
            original_username = username
            while True:
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                if not cursor.fetchone():
                    break
                username = f"{original_username}{counter}"
                counter += 1
            
            # 插入新用戶
            cursor.execute('''
                INSERT INTO users (username, email, full_name, password_hash, avatar_url, is_active, email_verified, created_at, updated_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, name, 'GOOGLE_AUTH', picture, 1, 1, datetime.now(), datetime.now(), datetime.now()))
            
            user_id = cursor.lastrowid
            
            # 為新用戶創建預設分類
            default_categories = ['餐飲', '交通', '購物', '娛樂', '薪資', '投資', '載具']
            for category_name in default_categories:
                try:
                    cursor.execute('''
                        INSERT INTO user_categories (user_id, name, is_default)
                        VALUES (?, ?, 1)
                    ''', (user_id, category_name))
                except sqlite3.IntegrityError:
                    pass
            
            db.commit()
            db.close()
            
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": name,
                    "is_google_user": True
                }
            }
            
    except Exception as e:
        return {"success": False, "message": f"創建用戶失敗: {str(e)}"}

@google_auth_bp.route('/google-login', methods=['POST'])
def google_login():
    """Google OAuth登入"""
    try:
        data = request.get_json()
        token = data.get('credential')
        
        if not token:
            return jsonify({
                "success": False,
                "message": "缺少Google認證令牌"
            }), 400
        
        # 驗證Google ID Token
        try:
            # 在生產環境中，您需要設置正確的GOOGLE_CLIENT_ID
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            
            # 檢查發行者
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('錯誤的發行者')
                
        except ValueError as e:
            return jsonify({
                "success": False,
                "message": f"無效的Google令牌: {str(e)}"
            }), 401
        
        # 創建或獲取用戶
        result = create_or_get_google_user(idinfo)
        
        if result['success']:
            # 設置會話
            user = result['user']
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_google_user'] = True
            
            return jsonify({
                "success": True,
                "message": "Google登入成功",
                "user": user
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Google登入失敗: {str(e)}"
        }), 500

@google_auth_bp.route('/google-config', methods=['GET'])
def get_google_config():
    """獲取Google OAuth配置"""
    return jsonify({
        "success": True,
        "client_id": GOOGLE_CLIENT_ID,
        "enabled": GOOGLE_CLIENT_ID != "YOUR_GOOGLE_CLIENT_ID"
    }), 200
