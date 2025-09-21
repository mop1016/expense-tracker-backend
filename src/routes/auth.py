from flask import Blueprint, request, jsonify, session
from models.user import User
import sqlite3
import os

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    """獲取資料庫連接"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
    return sqlite3.connect(db_path)

@auth_bp.route('/register', methods=['POST'])
def register():
    """用戶註冊"""
    try:
        data = request.get_json()
        
        # 驗證必填欄位
        required_fields = ['username', 'email', 'full_name', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False, 
                    "message": f"缺少必填欄位: {field}"
                }), 400
        
        # 創建用戶
        db = get_db_connection()
        user_model = User(db)
        
        result = user_model.create_user(
            username=data['username'],
            email=data['email'],
            full_name=data['full_name'],
            password=data['password'],
            phone=data.get('phone')
        )
        
        # 如果用戶創建成功，為其創建預設分類
        if result['success'] and result.get('user_id'):
            try:
                # 為新用戶創建預設分類
                user_id = result['user_id']
                default_categories = ['餐飲', '交通', '購物', '娛樂', '薪資', '投資']
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
                
                db.commit()
            except Exception as e:
                import traceback
                traceback.print_exc()
        
        db.close()
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"註冊失敗: {str(e)}"
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用戶登入"""
    try:
        data = request.get_json()
        
        username_or_email = data.get('username_or_email')
        password = data.get('password')
        
        if not username_or_email or not password:
            return jsonify({
                "success": False, 
                "message": "請提供用戶名/郵箱和密碼"
            }), 400
        
        # 驗證用戶
        db = get_db_connection()
        user_model = User(db)
        
        result = user_model.authenticate_user(username_or_email, password)
        
        db.close()
        
        if result['success']:
            # 設置會話
            session['user_id'] = result['user']['id']
            session['username'] = result['user']['username']
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"登入失敗: {str(e)}"
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用戶登出"""
    try:
        session.clear()
        return jsonify({
            "success": True, 
            "message": "登出成功"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"登出失敗: {str(e)}"
        }), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """獲取當前用戶資料"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        user_model = User(db)
        
        user = user_model.get_user_by_id(user_id)
        db.close()
        
        if user:
            return jsonify({
                "success": True, 
                "user": user
            }), 200
        else:
            return jsonify({
                "success": False, 
                "message": "用戶不存在"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取用戶資料失敗: {str(e)}"
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """更新用戶資料"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        
        db = get_db_connection()
        user_model = User(db)
        
        result = user_model.update_user_profile(
            user_id=user_id,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            avatar_url=data.get('avatar_url'),
            bio=data.get('bio')
        )
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"更新用戶資料失敗: {str(e)}"
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """修改密碼"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({
                "success": False, 
                "message": "請提供舊密碼和新密碼"
            }), 400
        
        db = get_db_connection()
        user_model = User(db)
        
        result = user_model.change_password(user_id, old_password, new_password)
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"修改密碼失敗: {str(e)}"
        }), 500

@auth_bp.route('/search-users', methods=['GET'])
def search_users():
    """搜索用戶（用於邀請加入群組）"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({
                "success": False, 
                "message": "搜索關鍵字至少需要2個字符"
            }), 400
        
        db = get_db_connection()
        user_model = User(db)
        
        users = user_model.search_users_by_name(query, limit=10)
        
        db.close()
        
        return jsonify({
            "success": True, 
            "users": users
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"搜索用戶失敗: {str(e)}"
        }), 500

@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """檢查登入狀態"""
    try:
        user_id = session.get('user_id')
        if user_id:
            db = get_db_connection()
            user_model = User(db)
            user = user_model.get_user_by_id(user_id)
            db.close()
            
            if user:
                return jsonify({
                    "success": True, 
                    "logged_in": True,
                    "user": user
                }), 200
        
        return jsonify({
            "success": True, 
            "logged_in": False
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"檢查登入狀態失敗: {str(e)}"
        }), 500

