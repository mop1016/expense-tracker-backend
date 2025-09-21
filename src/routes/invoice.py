from flask import Blueprint, request, jsonify, session
from models.invoice import InvoiceCarrier, InvoiceRecord, SyncLog, init_invoice_tables
from services.invoice_service import InvoiceService
from services.real_invoice_service import RealInvoiceService
from datetime import datetime
import json

invoice_bp = Blueprint('invoice', __name__)

# 初始化發票資料表
init_invoice_tables()

# 全域發票服務實例
real_invoice_service = RealInvoiceService()

@invoice_bp.route('/carriers', methods=['GET'])
def get_carriers():
    """獲取使用者的發票載具列表"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        carriers = InvoiceCarrier.get_by_user_id(user_id)
        
        return jsonify({
            'success': True,
            'data': carriers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@invoice_bp.route('/carriers', methods=['POST'])
def add_carrier():
    """新增發票載具"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        data = request.get_json()
        
        # 驗證必要欄位
        required_fields = ['carrier_type', 'carrier_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # 檢查載具是否已存在
        if InvoiceCarrier.exists(user_id, data['carrier_type'], data['carrier_id']):
            return jsonify({
                'success': False,
                'message': 'Carrier already exists'
            }), 400
        
        # 驗證載具（使用真實 API 服務）
        validation_result = real_invoice_service.validate_carrier(
            data['carrier_type'],
            data['carrier_id'],
            data.get('verification_code')
        )
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'message': validation_result['message']
            }), 400
        
        # 新增載具
        carrier_id = InvoiceCarrier.create(
            user_id=user_id,
            carrier_type=data['carrier_type'],
            carrier_id=data['carrier_id'],
            carrier_name=data.get('carrier_name'),
            verification_code=data.get('verification_code')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'id': carrier_id,
                'carrier_type': data['carrier_type'],
                'carrier_id': data['carrier_id'],
                'carrier_name': data.get('carrier_name')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@invoice_bp.route('/sync/<int:carrier_id>', methods=['POST'])
def sync_invoices(carrier_id):
    """同步指定載具的發票資料"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # 獲取載具資訊
        carrier = InvoiceCarrier.get_by_id(carrier_id)
        if not carrier or carrier['user_id'] != user_id:
            return jsonify({
                'success': False,
                'message': 'Carrier not found or access denied'
            }), 404
        
        # 建立同步記錄
        sync_log_id = SyncLog.create(user_id, carrier_id, 'manual')
        
        try:
            # 執行同步（使用真實 API 服務）
            sync_result = real_invoice_service.sync_carrier_invoices(carrier)
            
            # 更新同步記錄
            SyncLog.update(
                sync_log_id,
                'success' if sync_result['success'] else 'failed',
                sync_result['message'],
                sync_result.get('invoices_found', 0),
                sync_result.get('invoices_new', 0),
                sync_result.get('invoices_updated', 0)
            )
            
            return jsonify({
                'success': sync_result['success'],
                'message': sync_result['message'],
                'data': {
                    'invoices_found': sync_result.get('invoices_found', 0),
                    'invoices_new': sync_result.get('invoices_new', 0),
                    'invoices_updated': sync_result.get('invoices_updated', 0)
                }
            })
        except Exception as e:
            # 更新同步記錄為失敗
            SyncLog.update(sync_log_id, 'failed', str(e))
            raise e
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@invoice_bp.route('/records', methods=['GET'])
def get_invoice_records():
    """獲取發票紀錄列表"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # 分頁參數
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # 查詢參數
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        carrier_id = request.args.get('carrier_id')
        
        result = InvoiceRecord.get_by_user_id(
            user_id, page, per_page, start_date, end_date, carrier_id
        )
        
        return jsonify({
            'success': True,
            'data': result['records'],
            'pagination': {
                'page': result['page'],
                'per_page': result['per_page'],
                'total': result['total'],
                'pages': result['pages']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@invoice_bp.route('/sync-logs', methods=['GET'])
def get_sync_logs():
    """獲取同步記錄"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        logs = SyncLog.get_by_user_id(user_id)
        
        return jsonify({
            'success': True,
            'data': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@invoice_bp.route('/auto-import', methods=['POST'])
def auto_import_to_transactions():
    """將發票紀錄自動匯入為交易紀錄"""
    try:
        # 從 session 獲取 user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        data = request.get_json()
        invoice_record_ids = data.get('invoice_record_ids', [])
        
        if not invoice_record_ids:
            return jsonify({
                'success': False,
                'message': 'No invoice records specified'
            }), 400
        
        # 匯入發票紀錄為交易紀錄
        from models.transaction import Transaction
        import sqlite3
        import os
        
        # 使用與 main.py 相同的資料庫路徑方法
        DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'database.db')
        conn = sqlite3.connect(DATABASE_PATH)
        
        transaction_model = Transaction(conn)
        
        imported_count = 0
        failed_count = 0
        
        for record_id in invoice_record_ids:
            try:
                # 獲取發票紀錄
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM invoice_records 
                    WHERE id = ? AND user_id = ?
                ''', (record_id, user_id))
                
                invoice_record = cursor.fetchone()
                
                if not invoice_record:
                    failed_count += 1
                    continue
                
                # 檢查是否已經匯入
                if invoice_record[13]:  # is_processed column (0-based index 13)
                    continue
                
                # 創建交易紀錄
                transaction_data = {
                    'amount': -float(invoice_record[9]),  # total_amount (負數表示支出)
                    'category': '載具',
                    'description': f"發票載具匯入 - {invoice_record[6] or '未知商家'}",  # seller_name (index 6)
                    'date': invoice_record[4],  # invoice_date
                    'type': 'expense'
                }
                
                
                # 直接使用 SQL 創建交易，不依賴 Transaction 模型
                cursor.execute('''
                    INSERT INTO transactions (user_id, amount, category, description, date, type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, transaction_data['amount'], transaction_data['category'], 
                      transaction_data['description'], transaction_data['date'], transaction_data['type']))
                
                transaction_id = cursor.lastrowid
                
                if transaction_id:
                    # 標記發票紀錄為已處理
                    cursor.execute('''
                        UPDATE invoice_records 
                        SET is_processed = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (record_id,))
                    imported_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {imported_count} invoice records',
            'data': {
                'imported_count': imported_count,
                'failed_count': failed_count
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

