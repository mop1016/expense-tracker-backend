from flask import Blueprint, request, jsonify, session
from models.category import UserCategory, GroupCategory

category_bp = Blueprint('category', __name__)


@category_bp.route('/categories', methods=['GET'])
def get_user_categories():
    """獲取用戶的分類列表"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    categories = UserCategory.get_user_categories(user_id)
    
    return jsonify({
        'success': True,
        'categories': [cat['name'] for cat in categories]
    })

@category_bp.route('/categories', methods=['POST'])
def create_user_category():
    """新增用戶分類"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({
                'success': False,
                'message': '分類名稱不能為空'
            }), 400
        
        category, error = UserCategory.add_user_category(user_id, category_name)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': '分類新增成功',
            'category': category
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'錯誤: {str(e)}'
        }), 500

@category_bp.route('/categories/<category_name>', methods=['DELETE'])
def delete_user_category(category_name):
    """刪除用戶分類"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    success, error = UserCategory.delete_user_category(user_id, category_name)
    
    if not success:
        return jsonify({
            'success': False,
            'message': error
        }), 400
    
    return jsonify({
        'success': True,
        'message': '分類刪除成功'
    })

@category_bp.route('/groups/<int:group_id>/categories', methods=['GET'])
def get_group_categories(group_id):
    """獲取群組的分類列表"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    # TODO: 檢查用戶是否為群組成員
    
    categories = GroupCategory.get_group_categories(group_id)
    
    return jsonify({
        'success': True,
        'categories': [cat['name'] for cat in categories]
    })

@category_bp.route('/groups/<int:group_id>/categories', methods=['POST'])
def add_group_category(group_id):
    """為群組新增分類"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    # TODO: 檢查用戶是否為群組成員
    
    data = request.get_json()
    category_name = data.get('name', '').strip()
    
    if not category_name:
        return jsonify({
            'success': False,
            'message': '分類名稱不能為空'
        }), 400
    
    category, error = GroupCategory.add_group_category(group_id, user_id, category_name)
    
    if error:
        return jsonify({
            'success': False,
            'message': error
        }), 400
    
    return jsonify({
        'success': True,
        'message': '群組分類新增成功',
        'category': category
    }), 201

