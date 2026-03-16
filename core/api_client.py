# core/api_client.py
import requests
import csv
import io
import datetime
from config.settings import settings

class APIClient:
    def __init__(self):
        self.base_url = "https://maharasa.id/api"  # Coba dengan https
        self.timeout = 30  # timeout dalam detik
    
    def send_sales_menu(self, date_str, data_rows, columns):
        """
        Kirim data menu ke API dalam format CSV
        
        Args:
            date_str: tanggal (YYYY-MM-DD)
            data_rows: list of tuples dari database
            columns: list of column names
        """
        # Buat CSV dalam memory
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # Tulis header
        csv_writer.writerow(columns)
        
        # Tulis data
        for row in data_rows:
            csv_writer.writerow(row)
        
        csv_content = csv_buffer.getvalue()
        
        # Siapkan payload
        files = {
            'file': (f'sales_menu_{date_str}.csv', csv_content, 'text/csv')
        }
        
        data = {
            'date': date_str,
            'source': 'pos_closing_system',
            'version': settings.APP_VERSION
        }
        
        headers = {
            # 'Authorization': 'Bearer YOUR_API_KEY',  # Jika perlu API key
            'User-Agent': 'PromisePOS-Internal/1.0'
        }
        
        try:
            # Coba beberapa endpoint yang mungkin
            endpoints = [
                f"{self.base_url}/salesmenu",
                f"{self.base_url}/upload-sales",
                f"{self.base_url}/menu-sales",
            ]
            
            for endpoint in endpoints:
                print(f"🔄 Mencoba endpoint: {endpoint}")
                response = requests.post(
                    endpoint,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    print(f"✅ Berhasil! Endpoint: {endpoint}")
                    return {
                        'success': True,
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response': response.text
                    }
                elif response.status_code == 404:
                    continue  # Coba endpoint berikutnya
                else:
                    # Error lain, stop
                    return {
                        'success': False,
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response': response.text
                    }
            
            # Semua endpoint 404
            return {
                'success': False,
                'error': 'Semua endpoint tidak ditemukan (404)',
                'tried_endpoints': endpoints
            }
            
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Gagal koneksi ke server'}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Timeout, server tidak merespon'}
        except Exception as e:
            return {'success': False, 'error': str(e)}