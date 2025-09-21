from flask import Blueprint, request, jsonify, session
from datetime import datetime
import sqlite3
import os

transaction_bp = Blueprint('transaction', __name__)

def get_db_connection():
    """獲取資料庫連接"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
    return sqlite3.connect(db_path)

def require_login():
    """檢查登入狀態的統一函數"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


@transaction_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """獲取交易記錄"""
    # 使用統一的登入檢查函數
    user_id = require_login()
    
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    group_id = request.args.get("group_id")
    
    try:
        # 使用原生SQLite連接
        db = get_db_connection()
        cursor = db.cursor()
        
        # 如果指定了group_id，則獲取該群組所有成員的交易
        if group_id:
            try:
                group_id = int(group_id)
                # 獲取群組所有成員的ID
                cursor.execute('SELECT user_id FROM group_members WHERE group_id = ?', (group_id,))
                member_data = cursor.fetchall()
                member_ids = [row[0] for row in member_data]
                
                if not member_ids:
                    db.close()
                    return jsonify({
                        'success': True,
                        'transactions': [],
                        'total': 0,
                        'pages': 0,
                        'current_page': page
                    })
                
                # 查詢所有成員的交易 - 計算總數
                placeholders = ','.join(['?' for _ in member_ids])
                cursor.execute(f'SELECT COUNT(*) FROM transactions WHERE user_id IN ({placeholders})', member_ids)
                total = cursor.fetchone()[0]
                
                # 查詢分頁數據，加入用戶名稱
                cursor.execute(f'''
                    SELECT t.*, u.username, u.full_name 
                    FROM transactions t
                    LEFT JOIN users u ON t.user_id = u.id
                    WHERE t.user_id IN ({placeholders})
                    ORDER BY t.date DESC, t.id DESC
                    LIMIT ? OFFSET ?
                ''', member_ids + [per_page, (page - 1) * per_page])
                
            except ValueError:
                db.close()
                return jsonify({
                    "success": False, 
                    "message": "無效的群組ID"
                }), 400
        else:
            # 如果沒有group_id，則只獲取當前用戶的個人交易
            cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
            total = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT t.*, u.username, u.full_name 
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.user_id = ?
                ORDER BY t.date DESC, t.id DESC
                LIMIT ? OFFSET ?
            ''', (user_id, per_page, (page - 1) * per_page))
        
        transactions_data = cursor.fetchall()
        
        transactions = []
        
        for trans_data in transactions_data:
            transactions.append({
                'id': trans_data[0],
                'user_id': trans_data[1],
                'description': trans_data[2],
                'amount': trans_data[3],
                'category': trans_data[4],
                'date': trans_data[5],
                'type': trans_data[6],
                'created_at': trans_data[7],
                'updated_at': trans_data[8] if len(trans_data) > 8 else None,
                'username': trans_data[9] if len(trans_data) > 9 else None,
                'full_name': trans_data[10] if len(trans_data) > 10 else None,
                'user_name': trans_data[10] if len(trans_data) > 10 else trans_data[9] if len(trans_data) > 9 else None
            })
        
        db.close()
        
        pages = (total + per_page - 1) // per_page
        
        result = {
            'success': True,
            'transactions': transactions,
            'total': total,
            'pages': pages,
            'current_page': page
        }
        
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'載入交易失敗: {str(e)}'
        }), 500

@transaction_bp.route('/transactions', methods=['POST'])
def create_transaction():
    """新增交易記錄"""
    # 從會話中獲取當前用戶ID
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    data = request.get_json()

    required_fields = ['amount', 'category', 'description', 'date']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        # 根據金額自動判斷交易類型
        amount = float(data['amount'])
        transaction_type = data.get('type', 'income' if amount > 0 else 'expense')
        
        # 使用原生SQLite連接
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, category, description, date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (user_id, transaction_type, amount, data['category'], data['description'], data['date']))
        
        transaction_id = cursor.lastrowid
        db.commit()
        db.close()
        
        return jsonify({
            'message': '交易記錄新增成功',
            'success': True,
            'transaction_id': transaction_id
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'錯誤: {str(e)}', 'success': False}), 500

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """更新交易記錄"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "請先登入"}), 401
    
    data = request.get_json()
    
    try:
        # 使用原生SQLite連接
        db = get_db_connection()
        cursor = db.cursor()
        
        # 檢查交易是否存在且屬於當前用戶
        cursor.execute('SELECT * FROM transactions WHERE id = ? AND user_id = ?', (transaction_id, user_id))
        transaction = cursor.fetchone()
        
        if not transaction:
            db.close()
            return jsonify({'error': '交易記錄不存在'}), 404
        
        # 準備更新數據
        update_fields = []
        update_values = []
        
        if 'type' in data:
            update_fields.append('type = ?')
            update_values.append(data['type'])
        
        if 'amount' in data:
            update_fields.append('amount = ?')
            update_values.append(float(data['amount']))
        
        if 'category' in data:
            update_fields.append('category = ?')
            update_values.append(data['category'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            update_values.append(data['description'])
        
        if 'date' in data:
            update_fields.append('date = ?')
            update_values.append(data['date'])
        
        update_fields.append('updated_at = datetime("now")')
        update_values.append(transaction_id)
        
        # 執行更新
        update_sql = f'UPDATE transactions SET {", ".join(update_fields)} WHERE id = ?'
        cursor.execute(update_sql, update_values)
        
        db.commit()
        db.close()
        
        return jsonify({
            'message': '交易記錄更新成功',
            'success': True
        })
        
    except Exception as e:
        return jsonify({'message': f'錯誤: {str(e)}', 'success': False}), 500

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """刪除交易記錄"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "請先登入"}), 401
    
    try:
        # 使用原生SQLite連接
        db = get_db_connection()
        cursor = db.cursor()
        
        # 檢查交易是否存在且屬於當前用戶
        cursor.execute('SELECT id FROM transactions WHERE id = ? AND user_id = ?', (transaction_id, user_id))
        transaction = cursor.fetchone()
        
        if not transaction:
            db.close()
            return jsonify({'error': '交易記錄不存在'}), 404
        
        # 刪除交易
        cursor.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (transaction_id, user_id))
        
        db.commit()
        db.close()
        
        return jsonify({'message': '交易記錄刪除成功', 'success': True})
        
    except Exception as e:
        return jsonify({'message': f'錯誤: {str(e)}', 'success': False}), 500

@transaction_bp.route('/groups', methods=['GET'])
def get_groups():
    """獲取群組列表"""
    # 使用統一的登入檢查函數
    user_id = require_login()
    
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "請先登入"
        }), 401
    
    try:
        # 使用原生SQLite連接
        db = get_db_connection()
        cursor = db.cursor()
        
        # 獲取用戶參與的所有群組
        cursor.execute('''
            SELECT g.id, g.name, g.description, g.created_by, g.created_at
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
        ''', (user_id,))
        
        groups_data = cursor.fetchall()
        
        groups = []
        
        for group_data in groups_data:
            group_info = {
                'id': group_data[0],
                'name': group_data[1],
                'description': group_data[2] or '',
                'created_by': group_data[3],
                'created_at': group_data[4]
            }
            groups.append(group_info)
        
        db.close()
        
        result = {
            'success': True,
            'groups': groups
        }
        
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'載入群組失敗: {str(e)}'
        }), 500

@transaction_bp.route('/groups', methods=['POST'])
def create_group():
    """建立群組"""
    data = request.get_json()
    
    try:
        group = Group(
            name=data['name'],
            description=data.get('description', ''),
            created_by=data.get('created_by', 1)  # 暫時使用固定用戶ID
        )
        
        db.session.add(group)
        db.session.flush()  # 獲取群組ID
        
        # 將建立者加入群組
        member = GroupMember(
            group_id=group.id,
            user_id=group.created_by,
            role='admin'
        )
        
        db.session.add(member)
        
        # 如果前端傳遞了成員列表，則將這些成員加入群組
        if 'member_ids' in data and isinstance(data['member_ids'], list):
            for user_id in data['member_ids']:
                # 避免重複添加創建者
                if user_id != group.created_by:
                    new_member = GroupMember(
                        group_id=group.id,
                        user_id=user_id,
                        role='member'
                    )
                    db.session.add(new_member)
        
        db.session.commit()
        
        return jsonify({
            'message': '群組建立成功',
            'group': group.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_bp.route('/groups/<int:group_id>/members', methods=['POST'])
def add_group_member(group_id):
    """新增群組成員"""
    data = request.get_json()
    
    try:
        member = GroupMember(
            group_id=group_id,
            user_id=data['user_id'],
            role=data.get('role', 'member')
        )
        
        db.session.add(member)
        
        # 如果前端傳遞了成員列表，則將這些成員加入群組
        if 'member_ids' in data and isinstance(data['member_ids'], list):
            for user_id in data['member_ids']:
                # 避免重複添加創建者
                if user_id != group.created_by:
                    new_member = GroupMember(
                        group_id=group.id,
                        user_id=user_id,
                        role='member'
                    )
                    db.session.add(new_member)
        
        db.session.commit()
        
        return jsonify({
            'message': '成員新增成功',
            'member': member.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """獲取統計資料"""
    user_id = request.args.get('user_id', 1)  # 暫時使用固定用戶ID
    
    # 計算總收入和總支出
    group_id = request.args.get("group_id")

    income_query = db.session.query(db.func.sum(Transaction.amount))\
                            .filter(Transaction.user_id == user_id, Transaction.type == 'income')
    expense_query = db.session.query(db.func.sum(Transaction.amount))\
                             .filter(Transaction.user_id == user_id, Transaction.type == 'expense')
    category_expense_query = db.session.query(
        Transaction.category,
        db.func.sum(Transaction.amount).label('total')
    ).filter(Transaction.user_id == user_id, Transaction.type == 'expense')\
     .group_by(Transaction.category)

    if group_id:
        income_query = income_query.filter(Transaction.group_id == group_id)
        expense_query = expense_query.filter(Transaction.group_id == group_id)
        category_expense_query = category_expense_query.filter(Transaction.group_id == group_id)

    total_income = income_query.scalar() or 0
    total_expense = expense_query.scalar() or 0
    balance = total_income - total_expense
    
    # 按分類統計支出
    expense_by_category = category_expense_query.all()
    
    return jsonify({
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'expense_by_category': [
            {'category': cat, 'amount': float(amount)} 
            for cat, amount in expense_by_category
        ]
    })

@transaction_bp.route('/budgets', methods=['GET'])
def get_budgets():
    """獲取預算列表"""
    user_id = request.args.get('user_id', 1)  # 暫時使用固定用戶ID
    
    budgets = Budget.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'budgets': [budget.to_dict() for budget in budgets]
    })

@transaction_bp.route('/budgets', methods=['POST'])
def create_budget():
    """建立預算"""
    data = request.get_json()
    
    try:
        budget = Budget(
            user_id=data.get('user_id', 1),  # 暫時使用固定用戶ID
            category=data['category'],
            amount=float(data['amount']),
            period=data['period'],
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        )
        
        db.session.add(budget)
        db.session.commit()
        
        return jsonify({
            'message': '預算建立成功',
            'budget': budget.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400



@transaction_bp.route("/groups/<int:group_id>/members/<int:user_id>", methods=["DELETE"])
def remove_group_member(group_id, user_id):
    """移除群組成員"""
    member = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first_or_404()
    try:
        db.session.delete(member)
        db.session.commit()
        return jsonify({"message": "成員移除成功"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


