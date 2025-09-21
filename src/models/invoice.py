import sqlite3
import json
from datetime import datetime, date
from decimal import Decimal

def get_db_connection():
    """獲取資料庫連接"""
    conn = sqlite3.connect('../database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_invoice_tables():
    """初始化發票相關資料表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 創建發票載具表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_carriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            carrier_type TEXT NOT NULL,
            carrier_id TEXT NOT NULL,
            carrier_name TEXT,
            verification_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 創建發票紀錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            carrier_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            invoice_date DATE NOT NULL,
            invoice_time TIME,
            seller_name TEXT,
            seller_id TEXT,
            seller_address TEXT,
            total_amount DECIMAL(10,2) NOT NULL,
            tax_amount DECIMAL(10,2) DEFAULT 0,
            invoice_status TEXT DEFAULT 'normal',
            category_id INTEGER,
            is_processed BOOLEAN DEFAULT 0,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (carrier_id) REFERENCES invoice_carriers (id)
        )
    ''')
    
    # 創建發票明細表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_record_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            item_quantity DECIMAL(10,3) DEFAULT 1,
            item_unit TEXT,
            item_price DECIMAL(10,2) NOT NULL,
            item_amount DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_record_id) REFERENCES invoice_records (id)
        )
    ''')
    
    # 創建同步記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            carrier_id INTEGER NOT NULL,
            sync_type TEXT NOT NULL,
            sync_status TEXT NOT NULL,
            sync_message TEXT,
            invoices_found INTEGER DEFAULT 0,
            invoices_new INTEGER DEFAULT 0,
            invoices_updated INTEGER DEFAULT 0,
            sync_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_end_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (carrier_id) REFERENCES invoice_carriers (id)
        )
    ''')
    
    conn.commit()
    conn.close()

class InvoiceCarrier:
    """發票載具模型"""
    
    @staticmethod
    def get_by_user_id(user_id):
        """獲取使用者的所有載具"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM invoice_carriers 
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
        ''', (user_id,))
        
        carriers = cursor.fetchall()
        conn.close()
        
        return [dict(carrier) for carrier in carriers]
    
    @staticmethod
    def create(user_id, carrier_type, carrier_id, carrier_name=None, verification_code=None):
        """創建新載具"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invoice_carriers 
            (user_id, carrier_type, carrier_id, carrier_name, verification_code)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, carrier_type, carrier_id, carrier_name, verification_code))
        
        carrier_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return carrier_id
    
    @staticmethod
    def get_by_id(carrier_id):
        """根據ID獲取載具"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM invoice_carriers WHERE id = ?', (carrier_id,))
        carrier = cursor.fetchone()
        conn.close()
        
        return dict(carrier) if carrier else None
    
    @staticmethod
    def exists(user_id, carrier_type, carrier_id):
        """檢查載具是否已存在"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM invoice_carriers 
            WHERE user_id = ? AND carrier_type = ? AND carrier_id = ?
        ''', (user_id, carrier_type, carrier_id))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0

class InvoiceRecord:
    """發票紀錄模型"""
    
    @staticmethod
    def get_by_user_id(user_id, page=1, per_page=20, start_date=None, end_date=None, carrier_id=None):
        """獲取使用者的發票紀錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 構建查詢條件
        conditions = ['user_id = ?']
        params = [user_id]
        
        if start_date:
            conditions.append('invoice_date >= ?')
            params.append(start_date)
        
        if end_date:
            conditions.append('invoice_date <= ?')
            params.append(end_date)
        
        if carrier_id:
            conditions.append('carrier_id = ?')
            params.append(carrier_id)
        
        where_clause = ' AND '.join(conditions)
        
        # 計算總數
        cursor.execute(f'''
            SELECT COUNT(*) FROM invoice_records 
            WHERE {where_clause}
        ''', params)
        total = cursor.fetchone()[0]
        
        # 獲取分頁資料
        offset = (page - 1) * per_page
        cursor.execute(f'''
            SELECT * FROM invoice_records 
            WHERE {where_clause}
            ORDER BY invoice_date DESC, invoice_time DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset])
        
        records = cursor.fetchall()
        conn.close()
        
        return {
            'records': [dict(record) for record in records],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @staticmethod
    def create(user_id, carrier_id, invoice_data):
        """創建發票紀錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invoice_records 
            (user_id, carrier_id, invoice_number, invoice_date, invoice_time,
             seller_name, seller_id, total_amount, tax_amount, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, carrier_id, invoice_data['invoice_number'],
            invoice_data['invoice_date'], invoice_data.get('invoice_time'),
            invoice_data.get('seller_name'), invoice_data.get('seller_id'),
            invoice_data['total_amount'], invoice_data.get('tax_amount', 0),
            json.dumps(invoice_data)
        ))
        
        record_id = cursor.lastrowid
        
        # 創建發票明細
        for item in invoice_data.get('items', []):
            cursor.execute('''
                INSERT INTO invoice_items 
                (invoice_record_id, item_name, item_quantity, item_price, item_amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record_id, item['name'], item.get('quantity', 1),
                item['price'], item['amount']
            ))
        
        conn.commit()
        conn.close()
        
        return record_id
    
    @staticmethod
    def exists_by_number(user_id, invoice_number):
        """檢查發票號碼是否已存在"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM invoice_records 
            WHERE user_id = ? AND invoice_number = ?
        ''', (user_id, invoice_number))
        
        record = cursor.fetchone()
        conn.close()
        
        return record[0] if record else None
    
    @staticmethod
    def update(record_id, invoice_data):
        """更新發票紀錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE invoice_records 
            SET seller_name = ?, seller_id = ?, total_amount = ?, 
                tax_amount = ?, raw_data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            invoice_data.get('seller_name'), invoice_data.get('seller_id'),
            invoice_data['total_amount'], invoice_data.get('tax_amount', 0),
            json.dumps(invoice_data), record_id
        ))
        
        conn.commit()
        conn.close()

class SyncLog:
    """同步記錄模型"""
    
    @staticmethod
    def create(user_id, carrier_id, sync_type='manual'):
        """創建同步記錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_logs 
            (user_id, carrier_id, sync_type, sync_status)
            VALUES (?, ?, ?, 'running')
        ''', (user_id, carrier_id, sync_type))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    @staticmethod
    def update(log_id, status, message=None, invoices_found=0, invoices_new=0, invoices_updated=0):
        """更新同步記錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sync_logs 
            SET sync_status = ?, sync_message = ?, invoices_found = ?,
                invoices_new = ?, invoices_updated = ?, sync_end_time = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, message, invoices_found, invoices_new, invoices_updated, log_id))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_user_id(user_id, limit=50):
        """獲取使用者的同步記錄"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sl.*, ic.carrier_name, ic.carrier_id as carrier_code
            FROM sync_logs sl
            JOIN invoice_carriers ic ON sl.carrier_id = ic.id
            WHERE sl.user_id = ?
            ORDER BY sl.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        logs = cursor.fetchall()
        conn.close()
        
        return [dict(log) for log in logs]

