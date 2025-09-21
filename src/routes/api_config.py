from flask import Blueprint, request, jsonify, session
from services.real_invoice_service import RealInvoiceService

api_config_bp = Blueprint('api_config', __name__)

@api_config_bp.route('/set-credentials', methods=['POST'])
def set_api_credentials():
    """設定真實 API 憑證"""
    try:
        # 檢查用戶是否已登入
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        data = request.get_json()
        
        # 驗證必要欄位
        if 'app_id' not in data or 'api_key' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing app_id or api_key'
            }), 400
        
        # 設定 API 憑證
        from routes.invoice import real_invoice_service
        real_invoice_service.set_real_api_credentials(
            data['app_id'], 
            data['api_key']
        )
        
        return jsonify({
            'success': True,
            'message': 'API credentials set successfully. Real API mode enabled.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_config_bp.route('/enable-test-mode', methods=['POST'])
def enable_test_mode():
    """啟用測試模式"""
    try:
        # 檢查用戶是否已登入
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # 啟用測試模式
        from routes.invoice import real_invoice_service
        real_invoice_service.enable_test_mode()
        
        return jsonify({
            'success': True,
            'message': 'Test mode enabled. Using mock data.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_config_bp.route('/disable-test-mode', methods=['POST'])
def disable_test_mode():
    """停用測試模式"""
    try:
        # 檢查用戶是否已登入
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # 停用測試模式
        from routes.invoice import real_invoice_service
        real_invoice_service.disable_test_mode()
        
        return jsonify({
            'success': True,
            'message': 'Test mode disabled. Using real API.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_config_bp.route('/status', methods=['GET'])
def get_api_status():
    """獲取 API 狀態"""
    try:
        # 檢查用戶是否已登入
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not logged in'
            }), 401
        
        # 獲取 API 狀態
        from routes.invoice import real_invoice_service
        
        return jsonify({
            'success': True,
            'data': {
                'test_mode': real_invoice_service.test_mode,
                'has_credentials': (
                    real_invoice_service.app_id != "YOUR_APP_ID" and 
                    real_invoice_service.api_key != "YOUR_API_KEY"
                ),
                'app_id_set': real_invoice_service.app_id != "YOUR_APP_ID"
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

