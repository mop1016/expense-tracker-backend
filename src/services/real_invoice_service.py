import requests
import sqlite3
import json
import hashlib
import base64
from datetime import datetime, timedelta, date
from models.invoice import InvoiceCarrier, InvoiceRecord, SyncLog

class RealInvoiceService:
    """真實發票 API 服務類別，支援財政部電子發票 API"""
    
    def __init__(self):
        # TODO: Replace with your actual APP ID and API Key from the Ministry of Finance
        # 請將以下替換為您從財政部取得的真實 APP ID 和 API Key
        self.app_id = "YOUR_APP_ID"
        self.api_key = "YOUR_API_KEY"
        
        # 財政部電子發票 API 基礎 URL
        self.base_url = "https://api.einvoice.nat.gov.tw"
        
        # 是否使用測試模式（設為 False 使用真實 API）
        self.test_mode = True
    
    def validate_carrier(self, carrier_type, carrier_id, verification_code=None):
        """驗證載具有效性"""
        try:
            if carrier_type == 'mobile_barcode':
                return self._validate_mobile_barcode(carrier_id, verification_code)
            elif carrier_type == 'member_card':
                return self._validate_member_card(carrier_id)
            else:
                return {
                    'valid': False,
                    'message': 'Unsupported carrier type'
                }
        except Exception as e:
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }
    
    def _validate_mobile_barcode(self, mobile_barcode, verification_code):
        """驗證手機條碼"""
        if self.test_mode:
            return {
                'valid': True,
                'message': 'Mobile barcode validation passed (test mode)'
            }
        
        try:
            # 呼叫財政部 API 驗證手機條碼
            url = f"{self.base_url}/PB2CAPIVAN/invapp/InvApp"
            
            data = {
                'version': '0.5',
                'type': 'Barcode',
                'invNum': '',
                'action': 'carrierInvChk',
                'timeStamp': int(datetime.now().timestamp()),
                'cardType': '3J0002',
                'cardNo': mobile_barcode,
                'expTimeStamp': int((datetime.now() + timedelta(hours=1)).timestamp()),
                'checkCode': verification_code,
                'appID': self.app_id
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 200:
                return {
                    'valid': True,
                    'message': 'Mobile barcode validation passed'
                }
            else:
                return {
                    'valid': False,
                    'message': f"Validation failed: {result.get('msg', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}'
            }
    
    def _validate_member_card(self, card_number):
        """驗證會員卡載具"""
        return {
            'valid': True,
            'message': 'Member card validation passed (demo mode)'
        }
    
    def sync_carrier_invoices(self, carrier, days_back=30):
        """同步載具的發票資料"""
        try:
            # 計算查詢日期範圍
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            # 查詢發票資料
            if self.test_mode:
                invoices = self._generate_mock_invoices(start_date, end_date)
            else:
                invoices = self._query_carrier_invoices(carrier, start_date, end_date)
            
            invoices_found = len(invoices)
            invoices_new = 0
            invoices_updated = 0
            
            for invoice_data in invoices:
                # 檢查發票是否已存在
                existing_record_id = InvoiceRecord.exists_by_number(
                    carrier['user_id'], 
                    invoice_data['invoice_number']
                )
                
                if existing_record_id:
                    # 更新現有發票
                    InvoiceRecord.update(existing_record_id, invoice_data)
                    invoices_updated += 1
                else:
                    # 新增發票紀錄
                    InvoiceRecord.create(carrier['user_id'], carrier['id'], invoice_data)
                    invoices_new += 1
            
            return {
                'success': True,
                'message': f'Sync completed successfully',
                'invoices_found': invoices_found,
                'invoices_new': invoices_new,
                'invoices_updated': invoices_updated
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Sync failed: {str(e)}'
            }
    
    def _query_carrier_invoices(self, carrier, start_date, end_date):
        """查詢載具的發票資料（真實 API）"""
        try:
            if carrier['carrier_type'] == 'mobile_barcode':
                return self._query_mobile_barcode_invoices(carrier, start_date, end_date)
            else:
                return []
        except Exception as e:
            raise Exception(f"Failed to query invoices: {str(e)}")
    
    def _query_mobile_barcode_invoices(self, carrier, start_date, end_date):
        """查詢手機條碼的發票資料（真實 API）"""
        try:
            url = f"{self.base_url}/PB2CAPIVAN/invapp/InvApp"
            
            # 準備請求參數
            data = {
                'version': '0.5',
                'type': 'Barcode',
                'invNum': '',
                'action': 'carrierInvDetail',
                'timeStamp': int(datetime.now().timestamp()),
                'startDate': start_date.strftime('%Y/%m/%d'),
                'endDate': end_date.strftime('%Y/%m/%d'),
                'onlyWinningInv': 'N',
                'uuid': carrier['carrier_id'],
                'cardType': '3J0002',
                'cardNo': carrier['carrier_id'],
                'expTimeStamp': int((datetime.now() + timedelta(hours=1)).timestamp()),
                'appID': self.app_id
            }
            
            # 發送請求
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 200:
                # 解析發票資料
                invoices = []
                for invoice_data in result.get('details', []):
                    parsed_invoice = self._parse_real_invoice_data(invoice_data)
                    if parsed_invoice:
                        invoices.append(parsed_invoice)
                return invoices
            else:
                raise Exception(f"API Error: {result.get('msg', 'Unknown error')}")
                
        except Exception as e:
            raise Exception(f"Failed to query mobile barcode invoices: {str(e)}")
    
    def _parse_real_invoice_data(self, invoice_data):
        """解析真實 API 回傳的發票資料"""
        try:
            return {
                'invoice_number': invoice_data.get('invNum'),
                'invoice_date': invoice_data.get('invDate'),
                'invoice_time': invoice_data.get('invTime', '00:00:00'),
                'seller_name': invoice_data.get('sellerName'),
                'seller_id': invoice_data.get('sellerBan'),
                'total_amount': float(invoice_data.get('amount', 0)),
                'tax_amount': float(invoice_data.get('taxAmount', 0)),
                'items': self._parse_invoice_items(invoice_data.get('details', []))
            }
        except Exception as e:
            print(f"Failed to parse invoice data: {str(e)}")
            return None
    
    def _parse_invoice_items(self, items_data):
        """解析發票明細項目"""
        items = []
        for item_data in items_data:
            try:
                items.append({
                    'name': item_data.get('description'),
                    'quantity': float(item_data.get('quantity', 1)),
                    'price': float(item_data.get('unitPrice', 0)),
                    'amount': float(item_data.get('amount', 0))
                })
            except Exception as e:
                print(f"Failed to parse item: {str(e)}")
                continue
        return items
    
    def _generate_mock_invoices(self, start_date, end_date):
        """生成模擬發票資料用於測試"""
        mock_invoices = []
        
        # 生成一些模擬發票
        for i in range(5):
            invoice_date = start_date + timedelta(days=i * 3)
            mock_invoices.append({
                'invoice_number': f'AA{12345678 + i:08d}',
                'invoice_date': invoice_date.strftime('%Y-%m-%d'),
                'invoice_time': datetime.now().strftime('%H:%M:%S'),
                'seller_name': f'測試商店 {i+1}',
                'seller_id': '12345678',
                'total_amount': 100 + i * 50,
                'tax_amount': 5 + i * 2,
                'items': [
                    {
                        'name': f'測試商品 {i+1}',
                        'quantity': 1,
                        'price': 100 + i * 50,
                        'amount': 100 + i * 50
                    }
                ]
            })
        
        return mock_invoices
    
    def auto_categorize_invoice(self, invoice_data):
        """自動分類發票 - 統一歸類為載具"""
        return '載具'
    
    def set_real_api_credentials(self, app_id, api_key):
        """設定真實 API 憑證"""
        self.app_id = app_id
        self.api_key = api_key
        self.test_mode = False
        print(f"Real API credentials set. Test mode disabled.")
    
    def enable_test_mode(self):
        """啟用測試模式"""
        self.test_mode = True
        print("Test mode enabled. Using mock data.")
    
    def disable_test_mode(self):
        """停用測試模式"""
        self.test_mode = False
        print("Test mode disabled. Using real API.")

