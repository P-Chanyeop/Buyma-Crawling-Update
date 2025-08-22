# BUYMA 자동화 프로그램 - 에러 처리 모듈
import requests
import time
import json
import psutil
import os
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

class ErrorHandler:
    """에러 처리 및 세션 관리 클래스"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.max_retries = 3
        self.retry_delay = 5
    
    def check_session_validity(self, driver):
        """세션 유효성 확인"""
        try:
            self.main_window.log_message("🔍 세션 유효성 확인 중...")
            
            # 현재 URL 확인
            current_url = driver.current_url
            
            # 로그인 페이지로 리다이렉트되었는지 확인
            if "login" in current_url.lower():
                self.main_window.log_message("⚠️ 세션이 만료되었습니다.")
                return False
            
            # 마이페이지 접근 테스트
            try:
                original_url = current_url
                driver.get("https://www.buyma.com/my/")
                time.sleep(2)
                
                if "login" in driver.current_url.lower():
                    self.main_window.log_message("⚠️ 세션 만료 - 재로그인이 필요합니다.")
                    return False
                else:
                    self.main_window.log_message("✅ 세션이 유효합니다.")
                    # 원래 페이지로 돌아가기
                    driver.get(original_url)
                    return True
                    
            except Exception as e:
                self.main_window.log_message(f"세션 확인 중 오류: {str(e)}")
                return False
                
        except Exception as e:
            self.main_window.log_message(f"세션 유효성 확인 오류: {str(e)}")
            return False
    
    def handle_session_expired(self, driver):
        """세션 만료 처리"""
        try:
            self.main_window.log_message("🔄 세션 만료로 인한 재로그인 시도...")
            
            # 재로그인 시도
            login_success = self.main_window.buyma_login(driver)
            
            if login_success:
                self.main_window.log_message("✅ 재로그인 성공")
                return True
            else:
                self.main_window.log_message("❌ 재로그인 실패")
                
                # 사용자에게 알림
                QMessageBox.warning(
                    self.main_window, 
                    "세션 만료", 
                    "BUYMA 세션이 만료되어 재로그인에 실패했습니다.\n\n로그인 정보를 확인하고 다시 시도해주세요."
                )
                return False
                
        except Exception as e:
            self.main_window.log_message(f"세션 만료 처리 오류: {str(e)}")
            return False
    
    def robust_network_request(self, url, timeout=10):
        """안정적인 네트워크 요청"""
        for attempt in range(self.max_retries):
            try:
                self.main_window.log_message(f"🌐 네트워크 요청 시도 {attempt + 1}/{self.max_retries}: {url}")
                
                response = requests.get(url, timeout=timeout)
                
                if response.status_code == 200:
                    self.main_window.log_message("✅ 네트워크 요청 성공")
                    return response
                elif response.status_code == 429:  # Too Many Requests
                    self.main_window.log_message("⚠️ 요청 제한 - 대기 후 재시도")
                    time.sleep(30)  # 30초 대기
                    continue
                elif response.status_code == 503:  # Service Unavailable
                    self.main_window.log_message("⚠️ 서비스 일시 중단 - 대기 후 재시도")
                    time.sleep(60)  # 1분 대기
                    continue
                else:
                    self.main_window.log_message(f"⚠️ HTTP 오류 코드: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.main_window.log_message(f"⏰ 타임아웃 발생 (시도 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.ConnectionError:
                self.main_window.log_message(f"🔌 연결 오류 발생 (시도 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * 2)  # 연결 오류는 더 오래 대기
                    
            except requests.exceptions.RequestException as e:
                self.main_window.log_message(f"❌ 요청 오류: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                self.main_window.log_message(f"❌ 예상치 못한 네트워크 오류: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        self.main_window.log_message("❌ 모든 네트워크 재시도 실패")
        return None
    
    def safe_selenium_operation(self, driver, operation_func):
        """안전한 Selenium 작업 실행"""
        for attempt in range(self.max_retries):
            try:
                self.main_window.log_message(f"🔧 Selenium 작업 시도 {attempt + 1}/{self.max_retries}")
                
                # 세션 유효성 확인
                if not self.check_session_validity(driver):
                    if not self.handle_session_expired(driver):
                        return False
                
                # 실제 작업 실행
                result = operation_func(driver)
                
                if result:
                    self.main_window.log_message("✅ Selenium 작업 성공")
                    return True
                else:
                    self.main_window.log_message(f"⚠️ Selenium 작업 실패 (시도 {attempt + 1}/{self.max_retries})")
                    
            except Exception as e:
                self.main_window.log_message(f"❌ Selenium 작업 오류: {str(e)}")
                
                # 페이지 새로고침 시도
                try:
                    driver.refresh()
                    time.sleep(3)
                except:
                    pass
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        self.main_window.log_message("❌ 모든 Selenium 작업 재시도 실패")
        return False
    
    def monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        try:
            # 메모리 사용량 확인
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.main_window.log_message("⚠️ 메모리 사용량이 높습니다 (90% 이상)")
                
                # 가비지 컬렉션 강제 실행
                import gc
                gc.collect()
                
                QMessageBox.warning(
                    self.main_window, 
                    "시스템 리소스 경고", 
                    "메모리 사용량이 높습니다.\n\n잠시 후 다시 시도하거나 다른 프로그램을 종료해주세요."
                )
                return False
            
            # CPU 사용량 확인
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                self.main_window.log_message("⚠️ CPU 사용량이 높습니다 (95% 이상)")
                time.sleep(5)  # 딜레이 추가
            
            return True
            
        except Exception as e:
            self.main_window.log_message(f"시스템 리소스 모니터링 오류: {str(e)}")
            return True  # 모니터링 실패해도 작업은 계속
    
    def create_error_report(self, error_type, error_message, context=None):
        """에러 리포트 생성"""
        try:
            error_report = {
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'error_message': str(error_message),
                'context': context or {},
                'system_info': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
                },
                'program_settings': {
                    'url': getattr(self.main_window, 'dashboard_url', {}).get('text', ''),
                    'count': getattr(self.main_window, 'dashboard_count', {}).get('value', 0),
                    'discount': getattr(self.main_window, 'dashboard_discount', {}).get('value', 0)
                }
            }
            
            # 에러 리포트 파일 저장
            error_file = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_report, f, ensure_ascii=False, indent=2)
            
            self.main_window.log_message(f"📋 에러 리포트 생성: {error_file}")
            return error_file
            
        except Exception as e:
            self.main_window.log_message(f"에러 리포트 생성 실패: {str(e)}")
            return None
    
    def auto_recovery_attempt(self):
        """자동 복구 시도"""
        try:
            self.main_window.log_message("🔄 자동 복구를 시도합니다...")
            
            # 1. 시스템 리소스 정리
            import gc
            gc.collect()
            
            # 2. 네트워크 연결 확인
            if not self.validate_network_connection():
                self.main_window.log_message("❌ 네트워크 연결 불가 - 복구 실패")
                return False
            
            # 3. BUYMA 사이트 접근 확인
            if not self.validate_buyma_access():
                self.main_window.log_message("❌ BUYMA 사이트 접근 불가 - 복구 실패")
                return False
            
            self.main_window.log_message("✅ 자동 복구 완료")
            return True
            
        except Exception as e:
            self.main_window.log_message(f"자동 복구 실패: {str(e)}")
            return False
    
    def validate_network_connection(self):
        """네트워크 연결 확인"""
        try:
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def validate_buyma_access(self):
        """BUYMA 사이트 접근 확인"""
        try:
            response = requests.get("https://www.buyma.com", timeout=10)
            return response.status_code == 200
        except:
            return False
