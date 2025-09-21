from datetime import datetime, timedelta
import calendar

class Transaction:
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_table()
    
    def create_table(self):
        """創建交易表"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (group_id) REFERENCES groups (id)
            )
        ''')
        self.db.commit()
    
    def create_transaction(self, user_id, description, amount, category, date=None, group_id=None):
        """創建交易記錄"""
        try:
            if not description or not amount or not category:
                return {"success": False, "message": "描述、金額和分類都是必填的"}
            
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            transaction_type = 'income' if float(amount) > 0 else 'expense'
            
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, group_id, description, amount, category, date, type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, group_id, description, float(amount), category, date, transaction_type, datetime.now(), datetime.now()))
            
            transaction_id = cursor.lastrowid
            self.db.commit()
            
            # 獲取創建的交易記錄
            created_transaction = self.get_transaction_by_id(transaction_id)
            
            return {
                "success": True, 
                "message": "交易記錄創建成功",
                "transaction": created_transaction
            }
            
        except Exception as e:
            return {"success": False, "message": f"創建交易記錄失敗: {str(e)}"}
    
    def get_transaction_by_id(self, transaction_id):
        """根據ID獲取交易記錄"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT t.id, t.user_id, t.group_id, t.description, t.amount, t.category, 
                       t.date, t.type, t.created_at, t.updated_at,
                       u.full_name as user_name, u.username,
                       g.name as group_name
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN groups g ON t.group_id = g.id
                WHERE t.id = ?
            ''', (transaction_id,))
            
            transaction = cursor.fetchone()
            if not transaction:
                return None
            
            return {
                "id": transaction[0],
                "user_id": transaction[1],
                "group_id": transaction[2],
                "描述": transaction[3],  # 保持中文欄位名稱以兼容前端
                "金額": transaction[4],
                "category": transaction[5],
                "日期": transaction[6],
                "type": transaction[7],
                "created_at": transaction[8],
                "updated_at": transaction[9],
                "user_name": transaction[10],
                "username": transaction[11],
                "group_name": transaction[12] or "個人"
            }
            
        except Exception as e:
            return None
    
    def get_user_transactions(self, user_id, page=1, per_page=20):
        """獲取用戶的交易記錄"""
        try:
            offset = (page - 1) * per_page
            cursor = self.db.cursor()
            
            # 獲取總數
            cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
            total = cursor.fetchone()[0]
            
            # 獲取交易記錄
            cursor.execute('''
                SELECT t.id, t.user_id, t.group_id, t.description, t.amount, t.category, 
                       t.date, t.type, t.created_at, t.updated_at,
                       u.full_name as user_name, u.username,
                       g.name as group_name
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN groups g ON t.group_id = g.id
                WHERE t.user_id = ?
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, per_page, offset))
            
            transactions = cursor.fetchall()
            
            return {
                "transactions": [
                    {
                        "id": t[0],
                        "user_id": t[1],
                        "group_id": t[2],
                        "描述": t[3],  # 保持中文欄位名稱
                        "金額": t[4],
                        "category": t[5],
                        "日期": t[6],
                        "type": t[7],
                        "created_at": t[8],
                        "updated_at": t[9],
                        "user_name": t[10],
                        "username": t[11],
                        "group_name": t[12] or "個人"
                    }
                    for t in transactions
                ],
                "total": total,
                "current_page": page,
                "pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            return {"transactions": [], "total": 0, "current_page": 1, "pages": 0}
    
    def get_group_transactions(self, group_id, page=1, per_page=20):
        """獲取群組的交易記錄"""
        try:
            offset = (page - 1) * per_page
            cursor = self.db.cursor()
            
            # 獲取總數
            cursor.execute('SELECT COUNT(*) FROM transactions WHERE group_id = ?', (group_id,))
            total = cursor.fetchone()[0]
            
            # 獲取交易記錄
            cursor.execute('''
                SELECT t.id, t.user_id, t.group_id, t.description, t.amount, t.category, 
                       t.date, t.type, t.created_at, t.updated_at,
                       u.full_name as user_name, u.username,
                       g.name as group_name
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN groups g ON t.group_id = g.id
                WHERE t.group_id = ?
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT ? OFFSET ?
            ''', (group_id, per_page, offset))
            
            transactions = cursor.fetchall()
            
            return {
                "transactions": [
                    {
                        "id": t[0],
                        "user_id": t[1],
                        "group_id": t[2],
                        "描述": t[3],
                        "金額": t[4],
                        "category": t[5],
                        "日期": t[6],
                        "type": t[7],
                        "created_at": t[8],
                        "updated_at": t[9],
                        "user_name": t[10],
                        "username": t[11],
                        "group_name": t[12] or "個人"
                    }
                    for t in transactions
                ],
                "total": total,
                "current_page": page,
                "pages": (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            return {"transactions": [], "total": 0, "current_page": 1, "pages": 0}
    
    def update_transaction(self, transaction_id, **kwargs):
        """更新交易記錄"""
        try:
            allowed_fields = ['description', 'amount', 'category', 'date', 'group_id']
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    if field == 'amount':
                        # 根據金額更新類型
                        transaction_type = 'income' if float(value) > 0 else 'expense'
                        update_fields.append("type = ?")
                        values.append(transaction_type)
                    
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return {"success": False, "message": "沒有可更新的欄位"}
            
            values.append(datetime.now())
            values.append(transaction_id)
            
            cursor = self.db.cursor()
            cursor.execute(f'''
                UPDATE transactions 
                SET {', '.join(update_fields)}, updated_at = ?
                WHERE id = ?
            ''', values)
            
            self.db.commit()
            
            if cursor.rowcount > 0:
                updated_transaction = self.get_transaction_by_id(transaction_id)
                return {
                    "success": True, 
                    "message": "交易記錄更新成功",
                    "transaction": updated_transaction
                }
            else:
                return {"success": False, "message": "交易記錄不存在"}
                
        except Exception as e:
            return {"success": False, "message": f"更新交易記錄失敗: {str(e)}"}
    
    def delete_transaction(self, transaction_id):
        """刪除交易記錄"""
        try:
            cursor = self.db.cursor()
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            self.db.commit()
            
            if cursor.rowcount > 0:
                return {"success": True, "message": "交易記錄刪除成功"}
            else:
                return {"success": False, "message": "交易記錄不存在"}
                
        except Exception as e:
            return {"success": False, "message": f"刪除交易記錄失敗: {str(e)}"}
    
    def get_user_statistics(self, user_id, months=6):
        """獲取用戶統計數據"""
        try:
            cursor = self.db.cursor()
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # 總收支統計
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expense,
                    SUM(amount) as balance
                FROM transactions 
                WHERE user_id = ? AND date >= ?
            ''', (user_id, start_date.strftime('%Y-%m-%d')))
            
            totals = cursor.fetchone()
            
            # 分類統計
            cursor.execute('''
                SELECT category, SUM(ABS(amount)) as total
                FROM transactions 
                WHERE user_id = ? AND amount < 0 AND date >= ?
                GROUP BY category
                ORDER BY total DESC
            ''', (user_id, start_date.strftime('%Y-%m-%d')))
            
            categories = cursor.fetchall()
            
            # 月度趨勢
            monthly_stats = []
            for i in range(months):
                month_start = datetime(end_date.year, end_date.month, 1) - timedelta(days=i*30)
                month_end = month_start + timedelta(days=calendar.monthrange(month_start.year, month_start.month)[1] - 1)
                
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense
                    FROM transactions 
                    WHERE user_id = ? AND date >= ? AND date <= ?
                ''', (user_id, month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d')))
                
                month_data = cursor.fetchone()
                monthly_stats.append({
                    "month": month_start.strftime('%Y-%m'),
                    "income": month_data[0] or 0,
                    "expense": month_data[1] or 0,
                    "balance": (month_data[0] or 0) - (month_data[1] or 0)
                })
            
            return {
                "total_income": totals[0] or 0,
                "total_expense": totals[1] or 0,
                "balance": totals[2] or 0,
                "categories": [
                    {"name": cat[0], "amount": cat[1]}
                    for cat in categories
                ],
                "monthly_trends": list(reversed(monthly_stats))
            }
            
        except Exception as e:
            return {
                "total_income": 0,
                "total_expense": 0,
                "balance": 0,
                "categories": [],
                "monthly_trends": []
            }
    
    def get_group_statistics(self, group_id, months=6):
        """獲取群組統計數據"""
        try:
            cursor = self.db.cursor()
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # 總收支統計
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expense,
                    SUM(amount) as balance
                FROM transactions 
                WHERE group_id = ? AND date >= ?
            ''', (group_id, start_date.strftime('%Y-%m-%d')))
            
            totals = cursor.fetchone()
            
            # 成員貢獻統計
            cursor.execute('''
                SELECT u.full_name, u.username,
                       SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as income,
                       SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as expense,
                       COUNT(*) as transaction_count
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                WHERE t.group_id = ? AND t.date >= ?
                GROUP BY t.user_id, u.full_name, u.username
                ORDER BY (income + expense) DESC
            ''', (group_id, start_date.strftime('%Y-%m-%d')))
            
            members = cursor.fetchall()
            
            # 分類統計
            cursor.execute('''
                SELECT category, SUM(ABS(amount)) as total
                FROM transactions 
                WHERE group_id = ? AND amount < 0 AND date >= ?
                GROUP BY category
                ORDER BY total DESC
            ''', (group_id, start_date.strftime('%Y-%m-%d')))
            
            categories = cursor.fetchall()
            
            return {
                "total_income": totals[0] or 0,
                "total_expense": totals[1] or 0,
                "balance": totals[2] or 0,
                "member_contributions": [
                    {
                        "name": member[0],
                        "username": member[1],
                        "income": member[2] or 0,
                        "expense": member[3] or 0,
                        "transaction_count": member[4]
                    }
                    for member in members
                ],
                "categories": [
                    {"name": cat[0], "amount": cat[1]}
                    for cat in categories
                ]
            }
            
        except Exception as e:
            return {
                "total_income": 0,
                "total_expense": 0,
                "balance": 0,
                "member_contributions": [],
                "categories": []
            }

