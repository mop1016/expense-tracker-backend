from flask import Blueprint, request, jsonify, session
from models.group import Group
import sqlite3
import os

group_bp = Blueprint('group', __name__)

def get_db_connection():
    """獲取資料庫連接"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
    return sqlite3.connect(db_path)

def require_login():
    """檢查登入狀態"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id

@group_bp.route('/groups', methods=['GET'])
def get_groups():
    """獲取用戶的群組列表"""
    try:
        user_id = require_login()
        
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        groups = group_model.get_user_groups(user_id)
        
        db.close()
        
        result = {
            "success": True,
            "groups": groups or []
        }
        
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取群組列表失敗: {str(e)}"
        }), 500

@group_bp.route('/groups', methods=['POST'])
def create_group():
    """創建群組"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        member_names = data.get('member_names', '').strip()
        
        if not name:
            return jsonify({
                "success": False, 
                "message": "群組名稱不能為空"
            }), 400
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.create_group(
            name=name,
            description=description,
            created_by=user_id,
            member_names=member_names if member_names else None
        )
        
        db.close()
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"創建群組失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """獲取群組詳細信息"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        # 檢查用戶是否是群組成員
        cursor = db.cursor()
        cursor.execute('''
            SELECT role FROM group_members 
            WHERE group_id = ? AND user_id = ? AND status = 'active'
        ''', (group_id, user_id))
        
        member = cursor.fetchone()
        if not member:
            db.close()
            return jsonify({
                "success": False, 
                "message": "您不是該群組成員"
            }), 403
        
        group = group_model.get_group_by_id(group_id)
        
        db.close()
        
        if group:
            return jsonify({
                "success": True,
                "group": group
            }), 200
        else:
            return jsonify({
                "success": False, 
                "message": "群組不存在"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取群組信息失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>/invite', methods=['POST'])
def invite_to_group(group_id):
    """邀請用戶加入群組"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        invitee_id = data.get('invitee_id')
        message = data.get('message', '')
        
        if not invitee_id:
            return jsonify({
                "success": False, 
                "message": "請指定要邀請的用戶"
            }), 400
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.invite_user_to_group(
            group_id=group_id,
            inviter_id=user_id,
            invitee_id=invitee_id,
            message=message
        )
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"邀請用戶失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>/members', methods=['GET'])
def get_group_members(group_id):
    """獲取群組成員列表"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.get_group_members(group_id, user_id)
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取群組成員失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """刪除群組"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.delete_group(group_id, user_id)
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"刪除群組失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>/members/<int:member_id>', methods=['DELETE'])
def remove_member(group_id, member_id):
    """移除群組成員"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.remove_member(
            group_id=group_id,
            admin_id=user_id,
            member_id=member_id
        )
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"移除成員失敗: {str(e)}"
        }), 500

@group_bp.route('/groups/<int:group_id>/leave', methods=['POST'])
def leave_group(group_id):
    """離開群組"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.leave_group(group_id, user_id)
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"離開群組失敗: {str(e)}"
        }), 500

@group_bp.route('/invitations', methods=['GET'])
def get_invitations():
    """獲取用戶的群組邀請"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        db = get_db_connection()
        group_model = Group(db)
        
        invitations = group_model.get_user_invitations(user_id)
        
        db.close()
        
        return jsonify({
            "success": True,
            "invitations": invitations
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"獲取邀請失敗: {str(e)}"
        }), 500

@group_bp.route('/invitations/<int:invitation_id>/respond', methods=['POST'])
def respond_invitation(invitation_id):
    """回應群組邀請"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        accept = data.get('accept', False)
        
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.respond_to_invitation(invitation_id, user_id, accept)
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"回應邀請失敗: {str(e)}"
        }), 500

# 為了向後兼容，保留舊的API端點
@group_bp.route('/groups/<int:group_id>/members', methods=['POST'])
def add_member_legacy(group_id):
    """添加群組成員（舊版API，用於向後兼容）"""
    try:
        user_id = require_login()
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "請先登入"
            }), 401
        
        data = request.get_json()
        member_user_id = data.get('user_id')
        
        if not member_user_id:
            return jsonify({
                "success": False, 
                "message": "請指定要添加的用戶ID"
            }), 400
        
        # 直接邀請用戶
        db = get_db_connection()
        group_model = Group(db)
        
        result = group_model.invite_user_to_group(
            group_id=group_id,
            inviter_id=user_id,
            invitee_id=member_user_id
        )
        
        db.close()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"添加成員失敗: {str(e)}"
        }), 500

