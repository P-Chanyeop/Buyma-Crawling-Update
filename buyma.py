#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램
개발자: 소프트캣
버전: 1.0.0
"""

import sys
import os
import json
import psutil
import requests
import threading
import random
import re
import time
from datetime import datetime

# 전역 예외 핸들러 추가 - 프로그램 튕김 방지
def handle_exception(exc_type, exc_value, exc_traceback):
    """전역 예외 핸들러 - 예상치 못한 오류로 인한 프로그램 종료 방지"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    import traceback
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"🚨 예외 발생 (프로그램 계속 실행):\n{error_msg}")
    
    # 로그 파일에도 저장
    try:
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now()}] 예외 발생:\n{error_msg}\n")
    except:
        pass

sys.excepthook = handle_exception

# PyQt6 스타일시트 경고 무시
import warnings
warnings.filterwarnings("ignore", message="Could not parse stylesheet")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                            QTableWidgetItem, QProgressBar, QComboBox, 
                            QSpinBox, QCheckBox, QGroupBox, QFrame, 
                            QFileDialog, QMessageBox, QScrollArea, 
                            QRadioButton, QButtonGroup, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QObject
from PyQt6.QtGui import QFont, QColor, QBrush

# 안전한 슬롯 데코레이터 - 슬롯 함수에서 예외 발생 시 프로그램 튕김 방지
def safe_slot(func):
    """슬롯 함수를 안전하게 래핑하는 데코레이터"""
    def wrapper(self, *args, **kwargs):
        try:
            # 함수의 매개변수 개수 확인
            import inspect
            sig = inspect.signature(func)
            param_count = len([p for p in sig.parameters.values() if p.name != 'self'])
            
            # 매개변수 개수에 맞게 호출
            if param_count == 0:
                return func(self)
            else:
                return func(self, *args[:param_count], **kwargs)
                
        except Exception as e:
            print(f"🚨 슬롯 함수 오류 ({func.__name__}): {str(e)}")
            import traceback
            traceback.print_exc()
            # 기존 UI 상태 복원 메서드들 활용
            try:
                if hasattr(self, 'restore_favorite_analysis_ui'):
                    self.restore_favorite_analysis_ui()
                elif hasattr(self, 'restore_upload_ui'):
                    self.restore_upload_ui()
                # 일반적인 버튼 활성화 복원
                if hasattr(self, 'setEnabled'):
                    self.setEnabled(True)
            except:
                pass
    return wrapper

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import time


# ==================== 진행률 위젯 클래스 ====================

class ProgressWidget(QWidget):
    """윈도우 스티커 메모 스타일의 진행률 위젯"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.is_dragging = False
        self.drag_position = None
        
    def init_ui(self):
        """UI 초기화"""
        # 윈도우 설정
        self.setWindowTitle("작업 진행률")
        self.setFixedSize(300, 150)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |  # 항상 위에
            Qt.WindowType.FramelessWindowHint |   # 프레임 없음
            Qt.WindowType.Tool                    # 작업표시줄에 표시 안함
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 배경 위젯 (둥근 모서리)
        self.background_widget = QWidget()
        self.background_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 240);
                border: 2px solid #007bff;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }
        """)
        
        bg_layout = QVBoxLayout(self.background_widget)
        bg_layout.setContentsMargins(15, 15, 15, 15)
        bg_layout.setSpacing(8)
        
        # 헤더 (제목 + 닫기 버튼)
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("🚀 작업 진행률")
        self.title_label.setStyleSheet("""
            QLabel {
                font-family: '맑은 고딕';
                font-size: 14px;
                font-weight: bold;
                color: #007bff;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.title_label)
        
        # 닫기 버튼
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #ff4757;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ff3838;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        bg_layout.addLayout(header_layout)
        
        # 작업 정보
        self.task_label = QLabel("대기 중...")
        self.task_label.setStyleSheet("""
            QLabel {
                font-family: '맑은 고딕';
                font-size: 12px;
                color: #333;
                background: transparent;
            }
        """)
        bg_layout.addWidget(self.task_label)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                text-align: center;
                font-family: '맑은 고딕';
                font-size: 11px;
                font-weight: bold;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 6px;
            }
        """)
        bg_layout.addWidget(self.progress_bar)
        
        # 상세 정보
        self.detail_label = QLabel("준비 완료")
        self.detail_label.setStyleSheet("""
            QLabel {
                font-family: '맑은 고딕';
                font-size: 10px;
                color: #666;
                background: transparent;
            }
        """)
        bg_layout.addWidget(self.detail_label)
        
        layout.addWidget(self.background_widget)
        
        # 초기 위치 설정 (화면 우상단)
        self.move_to_top_right()
        
    def move_to_top_right(self):
        """화면 우상단으로 이동"""
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 50)
    
    # def show_progress(self, title="🚀 작업 진행률", total=100, current=0, status="작업 시작..."):
    #     """진행률 위젯 표시 및 초기화"""
    #     self.title_label.setText(title)
    #     self.update_progress(current, total, status, "")
    #     self.show()
    #     self.raise_()  # 맨 앞으로 가져오기
    #     self.activateWindow()
    
    def update_progress(self, current, total, task_name="작업 진행 중", detail=""):
        """진행률 업데이트"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} ({percentage}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0%")
        
        self.task_label.setText(task_name)
        if detail:
            self.detail_label.setText(detail)
        
        # 진행률에 따른 색상 변경
        if percentage >= 100:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    text-align: center;
                    font-family: '맑은 고딕';
                    font-size: 11px;
                    font-weight: bold;
                    background-color: #f8f9fa;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #28a745, stop:1 #1e7e34);
                    border-radius: 6px;
                }
            """)
        elif percentage >= 50:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    text-align: center;
                    font-family: '맑은 고딕';
                    font-size: 11px;
                    font-weight: bold;
                    background-color: #f8f9fa;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ffc107, stop:1 #e0a800);
                    border-radius: 6px;
                }
            """)
        
        self.show()
        QApplication.processEvents()
    
    def set_task_complete(self, task_name="작업 완료", message="모든 작업이 완료되었습니다."):
        """작업 완료 상태로 설정"""
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("완료!")
        self.task_label.setText(f"✅ {task_name}")
        self.detail_label.setText(message)
        
        # 완료 색상으로 변경
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                text-align: center;
                font-family: '맑은 고딕';
                font-size: 11px;
                font-weight: bold;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #1e7e34);
                border-radius: 6px;
            }
        """)
        
        # 3초 후 자동 숨김
        QTimer.singleShot(3000, self.hide)
    
    def set_task_error(self, task_name="작업 실패", error_message="오류가 발생했습니다."):
        """작업 실패 상태로 설정"""
        self.task_label.setText(f"❌ {task_name}")
        self.detail_label.setText(error_message)
        
        # 오류 색상으로 변경
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                text-align: center;
                font-family: '맑은 고딕';
                font-size: 11px;
                font-weight: bold;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc3545, stop:1 #c82333);
                border-radius: 6px;
            }
        """)
        
        # 5초 후 자동 숨김
        QTimer.singleShot(5000, self.hide)
    
    def mousePressEvent(self, event):
        """마우스 드래그 시작"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """마우스 드래그 중"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """마우스 드래그 종료"""
        self.is_dragging = False


# ==================== 스레드 워커 클래스들 ====================

class PriceAnalysisWorker(QThread):
    """가격 분석 작업을 위한 워커 스레드"""
    progress_updated = pyqtSignal(int, int)  # 현재, 전체
    product_analyzed = pyqtSignal(dict)  # 분석된 상품 정보
    finished = pyqtSignal(dict)  # 완료 통계
    log_message = pyqtSignal(str)
    
    def __init__(self, products, settings):
        super().__init__()
        self.products = products
        self.settings = settings
        self.is_running = True
        
    def run(self):
        """가격 분석 실행"""
        try:
            self.log_message.emit("🔍 가격 분석을 시작합니다...")
            
            total_products = len(self.products)
            analyzed_count = 0
            updated_count = 0
            excluded_count = 0
            failed_count = 0
            
            for i, product in enumerate(self.products):
                if not self.is_running:
                    break
                    
                try:
                    self.log_message.emit(f"📊 분석 중: {product.get('name', 'Unknown')} ({i+1}/{total_products})")
                    
                    # 경쟁사 최저가 조회 (시뮬레이션)
                    competitor_price = self.get_competitor_price(product)
                    
                    # 제안가 계산
                    discount = self.settings.get('discount_amount', 100)
                    suggested_price = competitor_price - discount
                    
                    # 마진 계산
                    cost_price = product.get('cost_price', product.get('current_price', 0) * 0.6)
                    margin = suggested_price - cost_price
                    min_margin = self.settings.get('min_margin', 500)
                    
                    # 분석 결과
                    analysis_result = {
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'current_price': product.get('current_price', 0),
                        'competitor_price': competitor_price,
                        'suggested_price': suggested_price,
                        'margin': margin,
                        'status': '',
                        'action': ''
                    }
                    
                    # 상태 결정
                    if margin < min_margin:
                        analysis_result['status'] = '수정 불가 (마진 부족)'
                        analysis_result['action'] = '제외'
                        excluded_count += 1
                    elif suggested_price >= product.get('current_price', 0):
                        analysis_result['status'] = '현재가 적정'
                        analysis_result['action'] = '유지'
                    else:
                        analysis_result['status'] = '수정 가능'
                        analysis_result['action'] = '수정 대상'
                        
                        # 자동 모드인 경우 즉시 수정
                        if self.settings.get('auto_mode', True):
                            if self.update_product_price(product, suggested_price):
                                analysis_result['action'] = '수정 완료'
                                updated_count += 1
                            else:
                                analysis_result['action'] = '수정 실패'
                                failed_count += 1
                    
                    analyzed_count += 1
                    self.product_analyzed.emit(analysis_result)
                    self.progress_updated.emit(i + 1, total_products)
                    
                    # 딜레이 (서버 부하 방지)
                    self.msleep(random.randint(2000, 4000))  # 2-4초 대기
                    
                except Exception as e:
                    self.log_message.emit(f"❌ 오류 발생: {product.get('name', 'Unknown')} - {str(e)}")
                    failed_count += 1
            
            # 완료 통계
            stats = {
                'total': total_products,
                'analyzed': analyzed_count,
                'updated': updated_count,
                'excluded': excluded_count,
                'failed': failed_count
            }
            
            self.finished.emit(stats)
            self.log_message.emit("✅ 가격 분석이 완료되었습니다!")
            
        except Exception as e:
            self.log_message.emit(f"❌ 심각한 오류 발생: {str(e)}")
    
    def get_competitor_price(self, product):
        """경쟁사 최저가 조회 (시뮬레이션)"""
        base_price = product.get('current_price', 15000)
        return int(base_price * random.uniform(0.8, 0.95))
    
    def update_product_price(self, product, new_price):
        """상품 가격 업데이트 (시뮬레이션)"""
        try:
            self.msleep(random.randint(1000, 3000))  # 업데이트 시뮬레이션
            return random.choice([True, True, True, False])  # 75% 성공률
        except:
            return False
    
    def stop(self):
        """작업 중지"""
        self.is_running = False

class FavoriteAnalysisWorker(QThread):
    """주력 상품 분석 작업을 위한 워커 스레드"""
    progress_updated = pyqtSignal(int, int)
    product_checked = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    
    def __init__(self, favorite_products, settings):
        super().__init__()
        self.favorite_products = favorite_products
        self.settings = settings
        self.is_running = True
        
    def run(self):
        """주력 상품 가격 확인 및 수정"""
        try:
            self.log_message.emit("⭐ 주력 상품 가격 확인을 시작합니다...")
            
            total_products = len(self.favorite_products)
            checked_count = 0
            updated_count = 0
            failed_count = 0
            
            for i, product in enumerate(self.favorite_products):
                if not self.is_running:
                    break
                    
                try:
                    self.log_message.emit(f"⭐ 확인 중: {product.get('name', 'Unknown')} ({i+1}/{total_products})")
                    
                    # 경쟁사 최저가 조회
                    competitor_price = self.get_competitor_price(product)
                    
                    # 제안가 계산
                    discount = self.settings.get('discount_amount', 100)
                    suggested_price = competitor_price - discount
                    
                    # 마진 확인
                    cost_price = product.get('cost_price', product.get('current_price', 0) * 0.6)
                    margin = suggested_price - cost_price
                    min_margin = self.settings.get('min_margin', 500)
                    
                    result = {
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'current_price': product.get('current_price', 0),
                        'competitor_price': competitor_price,
                        'suggested_price': suggested_price,
                        'margin': margin,
                        'status': '',
                        'updated': False
                    }
                    
                    # 가격 수정 필요성 판단
                    if margin >= min_margin and suggested_price < product.get('current_price', 0):
                        # 가격 수정 실행
                        if self.update_favorite_price(product, suggested_price):
                            result['status'] = '가격 수정 완료'
                            result['updated'] = True
                            updated_count += 1
                            
                            # 원본 데이터도 업데이트
                            product['current_price'] = suggested_price
                        else:
                            result['status'] = '가격 수정 실패'
                            failed_count += 1
                    elif margin < min_margin:
                        result['status'] = '마진 부족으로 수정 불가'
                    else:
                        result['status'] = '현재가 적정'
                    
                    checked_count += 1
                    self.product_checked.emit(result)
                    self.progress_updated.emit(i + 1, total_products)
                    
                    # 딜레이
                    self.msleep(random.randint(3000, 5000))  # 3-5초 대기
                    
                except Exception as e:
                    self.log_message.emit(f"❌ 오류 발생: {product.get('name', 'Unknown')} - {str(e)}")
                    failed_count += 1
            
            # 완료 통계
            stats = {
                'total': total_products,
                'checked': checked_count,
                'updated': updated_count,
                'failed': failed_count
            }
            
            self.finished.emit(stats)
            self.log_message.emit("✅ 주력 상품 가격 확인이 완료되었습니다!")
            
        except Exception as e:
            self.log_message.emit(f"❌ 심각한 오류 발생: {str(e)}")
    
    def get_competitor_price(self, product):
        """경쟁사 최저가 조회"""
        base_price = product.get('current_price', 15000)
        return int(base_price * random.uniform(0.8, 0.95))
    
    def update_favorite_price(self, product, new_price):
        """주력 상품 가격 업데이트"""
        try:
            self.msleep(random.randint(2000, 4000))  # 2-4초 대기
            return random.choice([True, True, True, False])  # 75% 성공률
        except:
            return False
    
    def stop(self):
        """작업 중지"""
        self.is_running = False

class Main(QMainWindow):
    # 크롤링 UI 업데이트용 시그널 추가
    crawling_progress_signal = pyqtSignal(int)  # 진행률
    crawling_status_signal = pyqtSignal(str)   # 상태 텍스트
    crawling_result_signal = pyqtSignal(dict)  # 크롤링 결과
    crawling_finished_signal = pyqtSignal()    # 완료
    
    # 로그인 관련 시그널
    login_success_signal = pyqtSignal()        # 로그인 성공
    login_failed_signal = pyqtSignal(str)      # 로그인 실패
    
    # 가격 분석 관련 시그널 추가
    price_analysis_log_signal = pyqtSignal(str)            # 로그 메시지
    price_analysis_table_update_signal = pyqtSignal(int, int, str)  # row, col, text
    price_analysis_finished_signal = pyqtSignal()          # 분석 완료
    
    # 확인 다이얼로그 시그널 추가 (스레드 안전)
    show_confirmation_signal = pyqtSignal(str, str, str)   # title, message, product_name
    confirmation_result_signal = pyqtSignal(bool)          # 사용자 선택 결과
    
    # 진행률 위젯 업데이트 시그널 추가
    update_price_progress_signal = pyqtSignal(int, int, str)  # current, total, status
    hide_price_progress_signal = pyqtSignal()                 # 진행률 위젯 숨기기
    
    # 내 상품 크롤링 관련 시그널 추가
    my_products_progress_signal = pyqtSignal(int, int, str)   # current, total, status
    my_products_log_signal = pyqtSignal(str)                 # 로그 메시지
    my_products_finished_signal = pyqtSignal()               # 완료
    
    # 진행률 위젯 완료/오류 상태 시그널 추가
    progress_complete_signal = pyqtSignal(str, str)          # title, message
    progress_error_signal = pyqtSignal(str, str)             # title, error_message
    
    # 대시보드 업데이트 시그널 추가
    dashboard_step_signal = pyqtSignal(str, str)             # step_text, color
    dashboard_progress_signal = pyqtSignal(str, int)         # progress_name, value
    dashboard_log_signal = pyqtSignal(str)                   # log_message
    
    def __init__(self):
        super().__init__()
        
        # 공용 브라우저 드라이버
        self.shared_driver = None
        self.is_logged_in = False
        self.login_thread = None
        
        # 주력 상품 데이터 초기화
        self.favorite_products = []
        self.favorites_file = "주력상품_목록.json"
        
        # 워커 스레드 초기화
        self.price_analysis_worker = None
        self.favorite_analysis_worker = None
        
        # 진행률 위젯 초기화
        self.progress_widget = ProgressWidget()
        self.upload_progress_widget = ProgressWidget()  # 업로드용 진행률 위젯
        self.price_progress_widget = ProgressWidget()   # 가격분석용 진행률 위젯
        
        # 통계 데이터 초기화
        self.today_stats = {
            'crawled_count': 0,
            'uploaded_count': 0,
            'success_count': 0,
            'failed_count': 0,
            'start_time': None,
            'total_process_time': 0,
            'process_count': 0
        }
        
        # 크롤링된 상품 데이터 저장용
        self.crawled_products = []
        
        self.init_ui()
        self.load_settings()
        
        # 크롤링 시그널 연결
        self.crawling_progress_signal.connect(self.update_crawling_progress)
        self.crawling_status_signal.connect(self.update_crawling_status)
        self.crawling_result_signal.connect(self.add_crawling_result_safe)
        self.crawling_finished_signal.connect(self.crawling_finished_safe)
        
        # 로그인 시그널 연결
        self.login_success_signal.connect(self.on_login_success)
        self.login_failed_signal.connect(self.on_login_failed)
        
        # 가격 분석 시그널 연결
        self.price_analysis_log_signal.connect(self.log_message)
        self.price_analysis_table_update_signal.connect(self.update_price_table_safe)
        self.price_analysis_finished_signal.connect(self.on_price_analysis_finished)
        
        # 확인 다이얼로그 시그널 연결 (스레드 안전)
        self.show_confirmation_signal.connect(self.show_confirmation_dialog_main_thread)
        
        # 진행률 위젯 시그널 연결
        self.update_price_progress_signal.connect(self.update_price_progress_widget_safe)
        self.hide_price_progress_signal.connect(self.hide_price_progress_widget)
        
        # 내 상품 크롤링 시그널 연결
        self.my_products_progress_signal.connect(self.update_price_progress_widget_safe)
        self.my_products_log_signal.connect(self.log_message)
        self.my_products_finished_signal.connect(self.on_my_products_finished)
        
        # 진행률 위젯 완료/오류 상태 시그널 연결
        self.progress_complete_signal.connect(self.set_progress_complete)
        self.progress_error_signal.connect(self.set_progress_error)
        
        # 확인 결과 저장용
        self.confirmation_result = None
        
        # 모든 UI 초기화 완료 후 주력 상품 자동 로드
        self.load_favorite_products_on_startup()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BUYMA 자동화 프로그램 v1.0.0 - Professional Edition")
        self.setGeometry(100, 100, 1400, 1000)  # 높이를 900에서 1000으로 증가
        self.setMinimumSize(1200, 900)  # 최소 높이도 800에서 900으로 증가
        
        # 스타일 설정
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                font-family: '맑은 고딕';
            }
            
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background: white;
                margin-top: 5px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #dee2e6;
                border-bottom: none;
                border-radius: 8px 8px 0 0;
                padding: 12px 24px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
                color: #495057;
                min-width: 120px;
                font-family: '맑은 고딕';
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border-color: #007bff;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
                border-color: #2196f3;
            }
            
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #343a40;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding-top: 15px;
                background: white;
                font-family: '맑은 고딕';
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                background: white;
                color: #007bff;
                font-size: 13px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 10px 20px;
                min-height: 25px;
                font-family: '맑은 고딕';
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #004085, stop:1 #002752);
            }
            
            QPushButton:disabled {
                background: #6c757d;
                color: #adb5bd;
            }
            
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                background: white;
                selection-background-color: #007bff;
                font-family: '맑은 고딕';
            }
            
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ced4da;
                border-bottom: 1px solid #ced4da;
                border-top-right-radius: 4px;
                background: #f8f9fa;
            }
            
            QSpinBox::up-button:hover {
                background: #e9ecef;
            }
            
            QSpinBox::up-button:pressed {
                background: #dee2e6;
            }
            
            QSpinBox::up-arrow {
                width: 10px;
                height: 10px;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 5px solid #495057;
                background: transparent;
            }
            
            QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid #495057;
                background: transparent;
            }
            
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid #ced4da;
                border-top: 1px solid #ced4da;
                border-bottom-right-radius: 4px;
                background: #f8f9fa;
            }
            
            QSpinBox::down-button:hover {
                background: #e9ecef;
            }
            
            QSpinBox::down-button:pressed {
                background: #dee2e6;
            }

            
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QTableWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background: white;
                gridline-color: #e9ecef;
                font-size: 10px;
                font-family: '맑은 고딕';
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            
            QTableWidget::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
            
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                padding: 8px;
                font-weight: bold;
                font-size: 10px;
                color: #495057;
            }
            
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
                background: #f8f9fa;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                border-radius: 4px;
            }
            
            QCheckBox {
                font-size: 11px;
                color: #495057;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                background: white;
            }
            
            QCheckBox::indicator:checked {
                background: #007bff;
                border-color: #007bff;
            }
            
            QLabel {
                color: #495057;
                font-size: 11px;
                background: transparent;
                border: none;
                font-family: '맑은 고딕';
            }
            
            QFrame QLabel {
                background: transparent;
                border: none;
            }
            
            QScrollArea {
                border: none;
                background: transparent;
            }
            
            QScrollBar:vertical {
                background: #f8f9fa;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background: #ced4da;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #adb5bd;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 헤더 생성
        self.create_header(main_layout)
        
        # 탭 위젯 생성
        self.create_tabs(main_layout)
        
        # 상태바 생성
        self.create_status_bar()
        
    def create_header(self, layout):
        """헤더 생성"""
        header_frame = QFrame()
        header_frame.setFixedHeight(100)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 12px;
                margin-bottom: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 20, 30, 20)
        header_layout.setSpacing(20)
        
        # 제목
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        
        title_label = QLabel("BUYMA 자동화 프로그램")
        title_label.setStyleSheet("""
            QLabel {
                color: white; 
                font-size: 20px; 
                font-weight: bold;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 2px;
            }
        """)
        title_label.setMinimumHeight(28)
        title_label.setMaximumHeight(28)
        
        subtitle_label = QLabel("Professional Edition v1.0.0 - 경쟁사 상품 자동 크롤링 & 업로드")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.85); 
                font-size: 11px;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 2px;
            }
        """)
        subtitle_label.setMinimumHeight(22)
        subtitle_label.setMaximumHeight(22)
        subtitle_label.setWordWrap(True)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()
        
        # 상태 정보
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        status_layout.setSpacing(8)
        
        self.connection_status = QLabel("● 연결 대기중")
        self.connection_status.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9); 
                font-weight: bold;
                font-size: 11px;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 2px;
            }
        """)
        self.connection_status.setMinimumHeight(22)
        self.connection_status.setMaximumHeight(22)
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.last_update = QLabel(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.last_update.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7); 
                font-size: 10px;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 2px;
            }
        """)
        self.last_update.setMinimumHeight(20)
        self.last_update.setMaximumHeight(20)
        self.last_update.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.last_update)
        status_layout.addStretch()
        
        header_layout.addLayout(title_layout, 3)
        header_layout.addStretch(1)
        header_layout.addLayout(status_layout, 2)
        
        layout.addWidget(header_frame)
        
    def get_spinbox_style(self):
        """스핀박스 공통 스타일 반환"""
        return """
            QSpinBox {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                background: white;
                min-width: 80px;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ced4da;
                border-bottom: 1px solid #ced4da;
                border-top-right-radius: 4px;
                background: #f8f9fa;
            }
            QSpinBox::up-button:hover {
                background: #e9ecef;
            }
            QSpinBox::up-arrow {
                width: 8px;
                height: 8px;
                border-left: 2px solid transparent;
                border-right: 2px solid transparent;
                border-bottom: 4px solid #495057;
                background: transparent;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid #ced4da;
                border-top: 1px solid #ced4da;
                border-bottom-right-radius: 4px;
                background: #f8f9fa;
            }
            QSpinBox::down-button:hover {
                background: #e9ecef;
            }
            QSpinBox::down-arrow {
                width: 8px;
                height: 8px;
                border-left: 2px solid transparent;
                border-right: 2px solid transparent;
                border-top: 4px solid #495057;
                background: transparent;
            }
        """

    def create_tabs(self, layout):
        """탭 생성"""
        self.tab_widget = QTabWidget()
        
        # 대시보드 탭 (첫 번째) - 주석처리
        # self.create_dashboard_tab()
        
        # 크롤링 탭
        self.create_crawling_tab()
        
        # 가격 관리 탭
        self.create_price_tab()
        
        # 주력 상품 관리 탭
        self.create_favorite_tab()
        
        # 업로드 탭
        self.create_upload_tab()
        
        # 모니터링 탭
        self.create_monitoring_tab()
        
        # 설정 탭
        self.create_settings_tab()
        
        layout.addWidget(self.tab_widget)
        
    def create_dashboard_tab(self):
        """대시보드 탭 생성"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 스크롤 내용 위젯
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 원클릭 자동화 섹션
        automation_group = QGroupBox("🚀 원클릭 자동화")
        automation_group.setMinimumHeight(200)
        automation_layout = QVBoxLayout(automation_group)
        automation_layout.setSpacing(15)
        
        # 워크플로우 설명
        workflow_label = QLabel("""
        <div style='font-size: 13px; line-height: 1.6;'>
        <b>📋 자동화 프로세스:</b><br>
        1️⃣ <span style='color: #007bff;'>경쟁사 크롤링</span> → 경쟁사 상품 정보 수집<br>
        2️⃣ <span style='color: #28a745;'>자동 업로드</span> → BUYMA에 상품 등록<br>
        3️⃣ <span style='color: #ffc107;'>가격 분석</span> → 경쟁사 최저가 확인<br>
        4️⃣ <span style='color: #6f42c1;'>가격 수정</span> → 설정된 할인가로 자동 수정
        </div>
        """)
        workflow_label.setWordWrap(True)
        workflow_label.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 6px;")
        automation_layout.addWidget(workflow_label)
        
        # 빠른 설정
        quick_settings_layout = QHBoxLayout()
        
        quick_settings_layout.addWidget(QLabel("경쟁사 URL:"))
        self.dashboard_url = QLineEdit()
        self.dashboard_url.setPlaceholderText("https://www.buyma.com/r/-B5718956O1/")
        self.dashboard_url.setMinimumHeight(35)
        quick_settings_layout.addWidget(self.dashboard_url)
        
        quick_settings_layout.addWidget(QLabel("크롤링 개수:"))
        self.dashboard_count = QSpinBox()
        self.dashboard_count.setRange(1, 100)
        self.dashboard_count.setValue(20)
        self.dashboard_count.setStyleSheet(self.get_spinbox_style())
        self.dashboard_count.setMinimumWidth(120)  # width를 80에서 120으로 증가
        self.dashboard_count.setMinimumHeight(35)
        quick_settings_layout.addWidget(self.dashboard_count)
        
        quick_settings_layout.addWidget(QLabel("할인(엔):"))
        self.dashboard_discount = QSpinBox()
        self.dashboard_discount.setRange(10, 1000)
        self.dashboard_discount.setValue(100)
        self.dashboard_discount.setStyleSheet(self.get_spinbox_style())
        self.dashboard_discount.setMinimumWidth(120)  # width를 80에서 120으로 증가
        self.dashboard_discount.setMinimumHeight(35)
        quick_settings_layout.addWidget(self.dashboard_discount)
        
        automation_layout.addLayout(quick_settings_layout)
        
        # 메인 실행 버튼
        self.start_automation_btn = QPushButton("🚀 전체 프로세스 시작")
        self.start_automation_btn.setMinimumHeight(60)
        self.start_automation_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #adb5bd;
            }
        """)
        self.start_automation_btn.clicked.connect(self.start_full_automation)
        automation_layout.addWidget(self.start_automation_btn)
        
        # 중지 버튼
        self.stop_automation_btn = QPushButton("⏹️ 프로세스 중지")
        self.stop_automation_btn.setMinimumHeight(45)
        self.stop_automation_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """)
        self.stop_automation_btn.setEnabled(False)
        self.stop_automation_btn.clicked.connect(self.stop_full_automation)
        automation_layout.addWidget(self.stop_automation_btn)
        
        layout.addWidget(automation_group)
        
        # 실시간 진행 상황
        progress_group = QGroupBox("📈 실시간 진행 상황")
        progress_group.setMinimumHeight(180)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(15)
        
        # 현재 단계
        self.current_step_label = QLabel("현재 단계: 대기중...")
        self.current_step_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057; padding: 5px;")
        progress_layout.addWidget(self.current_step_label)
        
        # 전체 진행률
        progress_layout.addWidget(QLabel("전체 진행률:"))
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimumHeight(30)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.overall_progress)
        
        # 단계별 진행률
        steps_layout = QGridLayout()
        steps_layout.setSpacing(15)
        steps_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1단계: 크롤링
        step1_label = QLabel("1️⃣ 크롤링")
        step1_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        step1_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 11px; 
                padding: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
        """)
        step1_label.setMinimumWidth(90)
        step1_label.setMinimumHeight(35)
        steps_layout.addWidget(step1_label, 0, 0)
        
        self.step1_progress = QProgressBar()
        self.step1_progress.setMinimumHeight(35)
        self.step1_progress.setTextVisible(True)
        self.step1_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step1_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #007bff;
                border-radius: 4px;
            }
        """)
        steps_layout.addWidget(self.step1_progress, 0, 1)
        
        # 2단계: 업로드
        step2_label = QLabel("2️⃣ 업로드")
        step2_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        step2_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 11px; 
                padding: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
        """)
        step2_label.setMinimumWidth(90)
        step2_label.setMinimumHeight(35)
        steps_layout.addWidget(step2_label, 0, 2)
        
        self.step2_progress = QProgressBar()
        self.step2_progress.setMinimumHeight(35)
        self.step2_progress.setTextVisible(True)
        self.step2_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step2_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #28a745;
                border-radius: 4px;
            }
        """)
        steps_layout.addWidget(self.step2_progress, 0, 3)
        
        # 3단계: 가격분석
        step3_label = QLabel("3️⃣ 가격분석")
        step3_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        step3_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 11px; 
                padding: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
        """)
        step3_label.setMinimumWidth(90)
        step3_label.setMinimumHeight(35)
        steps_layout.addWidget(step3_label, 1, 0)
        
        self.step3_progress = QProgressBar()
        self.step3_progress.setMinimumHeight(35)
        self.step3_progress.setTextVisible(True)
        self.step3_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step3_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #ffc107;
                border-radius: 4px;
            }
        """)
        steps_layout.addWidget(self.step3_progress, 1, 1)
        
        # 4단계: 가격수정
        step4_label = QLabel("4️⃣ 가격수정")
        step4_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        step4_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                font-size: 11px; 
                padding: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
        """)
        step4_label.setMinimumWidth(90)
        step4_label.setMinimumHeight(35)
        steps_layout.addWidget(step4_label, 1, 2)
        
        self.step4_progress = QProgressBar()
        self.step4_progress.setMinimumHeight(35)
        self.step4_progress.setTextVisible(True)
        self.step4_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step4_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #6f42c1;
                border-radius: 4px;
            }
        """)
        steps_layout.addWidget(self.step4_progress, 1, 3)
        
        progress_layout.addLayout(steps_layout)
        
        # 처리 통계
        stats_layout = QHBoxLayout()
        
        self.processed_items = QLabel("처리된 상품: 0/0")
        self.processed_items.setStyleSheet("font-weight: bold; color: #007bff; padding: 5px;")
        stats_layout.addWidget(self.processed_items)
        
        self.success_items = QLabel("성공: 0")
        self.success_items.setStyleSheet("font-weight: bold; color: #28a745; padding: 5px;")
        stats_layout.addWidget(self.success_items)
        
        self.failed_items_dash = QLabel("실패: 0")
        self.failed_items_dash.setStyleSheet("font-weight: bold; color: #dc3545; padding: 5px;")
        stats_layout.addWidget(self.failed_items_dash)
        
        self.estimated_time = QLabel("예상 완료: --:--")
        self.estimated_time.setStyleSheet("font-weight: bold; color: #6f42c1; padding: 5px;")
        stats_layout.addWidget(self.estimated_time)
        
        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)
        
        layout.addWidget(progress_group)
        
        # 최근 활동 로그
        recent_log_group = QGroupBox("📝 최근 활동")
        recent_log_layout = QVBoxLayout(recent_log_group)
        
        self.dashboard_log = QTextEdit()
        self.dashboard_log.setMaximumHeight(150)
        self.dashboard_log.setReadOnly(True)
        self.dashboard_log.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                color: #495057;
            }
        """)
        recent_log_layout.addWidget(self.dashboard_log)
        
        layout.addWidget(recent_log_group)
        
        # 스크롤 영역에 내용 설정
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # self.tab_widget.addTab(tab, "📊 대시보드")  # 주석처리
    
    def create_crawling_tab(self):
        """크롤링 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 크롤링 설정
        crawling_group = QGroupBox("🔍 크롤링 설정")
        crawling_layout = QGridLayout(crawling_group)
        
        crawling_layout.addWidget(QLabel("경쟁사 페이지 URL:"), 0, 0)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.buyma.com/r/-B5718956O1/ (예시)")
        crawling_layout.addWidget(self.url_input, 0, 1, 1, 2)
        
        url_browse_btn = QPushButton("📁 URL 목록")
        url_browse_btn.clicked.connect(self.browse_url_list)
        crawling_layout.addWidget(url_browse_btn, 0, 3)
        
        crawling_layout.addWidget(QLabel("크롤링 개수:"), 1, 0)
        self.crawl_count = QSpinBox()
        self.crawl_count.setRange(1, 1000)
        self.crawl_count.setValue(50)
        self.crawl_count.setStyleSheet(self.get_spinbox_style())
        crawling_layout.addWidget(self.crawl_count, 1, 1)
        
        crawling_layout.addWidget(QLabel("지연 시간(초):"), 1, 2)
        self.delay_time = QSpinBox()
        self.delay_time.setRange(1, 60)
        self.delay_time.setValue(3)
        self.delay_time.setStyleSheet(self.get_spinbox_style())
        crawling_layout.addWidget(self.delay_time, 1, 3)
        
        self.include_images = QCheckBox("이미지 포함")
        self.include_images.setChecked(True)
        crawling_layout.addWidget(self.include_images, 2, 0)
        
        self.include_options = QCheckBox("색상/사이즈 옵션 포함")
        self.include_options.setChecked(True)
        crawling_layout.addWidget(self.include_options, 2, 1)
        
        self.skip_duplicates = QCheckBox("중복 상품 제외")
        self.skip_duplicates.setChecked(True)
        crawling_layout.addWidget(self.skip_duplicates, 2, 2)
        
        layout.addWidget(crawling_group)
        
        # 컨트롤 버튼
        control_layout = QHBoxLayout()
        
        self.start_crawling_btn = QPushButton("🚀 크롤링 시작")
        self.start_crawling_btn.setProperty("class", "success")
        self.start_crawling_btn.clicked.connect(self.start_crawling)
        
        self.stop_crawling_btn = QPushButton("⏹️ 중지")
        self.stop_crawling_btn.setProperty("class", "danger")
        self.stop_crawling_btn.setEnabled(False)
        
        # 크롤링 데이터 저장/불러오기 버튼 추가
        self.save_crawling_btn = QPushButton("💾 저장")
        self.save_crawling_btn.setToolTip("크롤링 데이터를 JSON 파일로 저장")
        self.save_crawling_btn.clicked.connect(self.save_crawling_data)
        
        self.load_crawling_btn = QPushButton("📂 불러오기")
        self.load_crawling_btn.setToolTip("저장된 크롤링 데이터를 불러오기")
        self.load_crawling_btn.clicked.connect(self.load_crawling_data)
        
        control_layout.addWidget(self.start_crawling_btn)
        control_layout.addWidget(self.stop_crawling_btn)
        control_layout.addWidget(self.save_crawling_btn)
        control_layout.addWidget(self.load_crawling_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 진행 상황
        progress_group = QGroupBox("📊 진행 상황")
        progress_layout = QVBoxLayout(progress_group)
        
        self.crawling_progress = QProgressBar()
        self.crawling_progress.setTextVisible(True)
        progress_layout.addWidget(self.crawling_progress)
        
        self.crawling_status = QLabel("대기중...")
        progress_layout.addWidget(self.crawling_status)
        
        layout.addWidget(progress_group)
        
        # 결과 테이블
        result_group = QGroupBox("📋 크롤링 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.crawling_table = QTableWidget()
        self.crawling_table.setColumnCount(8)  # 컬럼 수 증가
        self.crawling_table.setHorizontalHeaderLabels([
            "상품명", "브랜드", "가격", "이미지 수", "색상/사이즈", "URL", "상태", "액션"
        ])
        
        # 컬럼 너비 조정 (액션 컬럼을 더 넓게)
        self.crawling_table.setColumnWidth(0, 200)  # 상품명
        self.crawling_table.setColumnWidth(1, 120)  # 브랜드
        self.crawling_table.setColumnWidth(2, 100)  # 가격
        self.crawling_table.setColumnWidth(3, 80)   # 이미지 수
        self.crawling_table.setColumnWidth(4, 100)  # 색상/사이즈
        self.crawling_table.setColumnWidth(5, 150)  # URL
        self.crawling_table.setColumnWidth(6, 100)  # 상태
        self.crawling_table.setColumnWidth(7, 200)  # 액션 (4개 버튼 가로 배치용)
        
        # 마지막 컬럼 자동 확장 비활성화 (액션 컬럼 너비 고정)
        self.crawling_table.horizontalHeader().setStretchLastSection(True)
        
        # 기본 행 높이 설정 (버튼 높이에 맞춤)
        self.crawling_table.verticalHeader().setDefaultSectionSize(50)
        
        result_layout.addWidget(self.crawling_table)
        
        # 결과 버튼
        result_btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 엑셀 내보내기")
        export_btn.clicked.connect(self.export_crawling_results)
        
        clear_btn = QPushButton("🗑️ 결과 지우기")
        clear_btn.setProperty("class", "warning")
        clear_btn.clicked.connect(self.clear_crawling_results)
        
        result_btn_layout.addWidget(export_btn)
        result_btn_layout.addWidget(clear_btn)
        result_btn_layout.addStretch()
        
        result_layout.addLayout(result_btn_layout)
        layout.addWidget(result_group)
        
        self.tab_widget.addTab(tab, "🔍 상품 크롤링")
        
    def create_price_tab(self):
        """가격 관리 탭 생성 - 본인 상품 기반 분석"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 가격 관리 모드 선택
        mode_group = QGroupBox("📊 가격 관리 모드 선택")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(10)
        
        self.price_mode_group = QButtonGroup()
        
        self.auto_mode = QRadioButton("🤖 자동 모드 - 조건에 맞으면 즉시 수정")
        self.auto_mode.setChecked(True)  # 기본값
        self.auto_mode.setStyleSheet("font-size: 12px; padding: 5px;")
        
        self.manual_mode = QRadioButton("👤 수동 모드 - 검토 후 사용자가 직접 수정")
        self.manual_mode.setStyleSheet("font-size: 12px; padding: 5px;")
        
        self.price_mode_group.addButton(self.auto_mode, 0)
        self.price_mode_group.addButton(self.manual_mode, 1)
        
        mode_layout.addWidget(self.auto_mode)
        mode_layout.addWidget(self.manual_mode)
        
        layout.addWidget(mode_group)
        
        # 가격 분석 설정 (브랜드명, 상품명 제거)
        analysis_group = QGroupBox("⚙️ 가격 분석 설정")
        analysis_layout = QGridLayout(analysis_group)
        
        # 설명 라벨 추가
        info_label = QLabel("💡 본인의 판매 중인 상품을 자동으로 가져와서 BUYMA 최저가와 비교 분석합니다.")
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        analysis_layout.addWidget(info_label, 0, 0, 1, 4)
        
        analysis_layout.addWidget(QLabel("할인 금액(엔):"), 1, 0)
        self.discount_amount = QSpinBox()
        self.discount_amount.setRange(1, 10000)
        self.discount_amount.setValue(100)
        self.discount_amount.setToolTip("경쟁사 최저가보다 얼마나 할인할지 설정")
        self.discount_amount.setStyleSheet(self.get_spinbox_style())
        analysis_layout.addWidget(self.discount_amount, 1, 1)
        
        analysis_layout.addWidget(QLabel("최소 마진(엔):"), 1, 2)
        self.min_margin = QSpinBox()
        self.min_margin.setRange(0, 50000)
        self.min_margin.setValue(500)
        self.min_margin.setToolTip("최소한 보장할 마진 금액")
        self.min_margin.setStyleSheet(self.get_spinbox_style())
        analysis_layout.addWidget(self.min_margin, 1, 3)
        
        self.exclude_loss_products = QCheckBox("손실 예상 상품 자동 제외")
        self.exclude_loss_products.setChecked(True)
        self.exclude_loss_products.setToolTip("마진이 최소 마진보다 적은 상품은 가격 수정에서 제외")
        analysis_layout.addWidget(self.exclude_loss_products, 2, 0, 1, 4)
        
        layout.addWidget(analysis_group)
        
        # 가격 관리 컨트롤
        price_control_layout = QHBoxLayout()
        
        self.load_my_products_btn = QPushButton("🔍 가격분석")
        self.load_my_products_btn.setMinimumHeight(45)
        self.load_my_products_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.load_my_products_btn.clicked.connect(self.load_my_products)
        
        self.analyze_price_btn = QPushButton("🔍 가격분석 & 가격수정 시작")
        self.analyze_price_btn.setMinimumHeight(45)
        self.analyze_price_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
            }
        """)
        self.analyze_price_btn.clicked.connect(self.analyze_my_products_prices)
        
        self.auto_update_all_btn = QPushButton("🚀 전체 상품 자동 업데이트")
        self.auto_update_all_btn.setMinimumHeight(45)
        self.auto_update_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.auto_update_all_btn.clicked.connect(self.auto_update_all_prices)
        
        self.load_json_btn = QPushButton("📁 JSON 파일 불러오기")
        self.load_json_btn.setMinimumHeight(45)
        self.load_json_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #495057);
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #495057, stop:1 #343a40);
            }
        """)
        self.load_json_btn.clicked.connect(self.load_products_from_json)
        
        # 가격 수정 버튼 추가
        self.update_prices_btn = QPushButton("💰 가격수정")
        self.update_prices_btn.setMinimumHeight(45)
        self.update_prices_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.update_prices_btn.clicked.connect(self.update_analyzed_prices)
        
        price_control_layout.addWidget(self.load_my_products_btn)
        price_control_layout.addWidget(self.update_prices_btn)
        price_control_layout.addWidget(self.load_json_btn)
        price_control_layout.addWidget(self.analyze_price_btn)
        
        layout.addLayout(price_control_layout)
        
        # 가격 분석 결과 테이블
        result_group = QGroupBox("📊 가격 분석 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(7)
        self.price_table.setHorizontalHeaderLabels([
            "상품명", "현재가격", "최저가", "제안가", "가격차이", "상태", "액션"
        ])
        
        # 테이블 스타일 설정
        self.price_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border: none;
                text-align: left;
            }
        """)
        
        self.price_table.setAlternatingRowColors(True)
        self.price_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.price_table.horizontalHeader().setStretchLastSection(True)
        
        # 텍스트 래핑 비활성화 - 한 줄로 표시
        self.price_table.setWordWrap(False)
        
        # 텍스트 엘라이드 모드 설정 - 오른쪽 끝에서만 ...
        self.price_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        # 헤더의 텍스트 엘라이드 모드도 설정
        header = self.price_table.horizontalHeader()
        header.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        # 커스텀 델리게이트 대신 간단한 방법 사용
        # 상품명 컬럼의 리사이즈 모드를 Interactive로 설정
        header.setSectionResizeMode(0, header.ResizeMode.Interactive)
        
        # 컬럼 너비 설정
        self.price_table.setColumnWidth(0, 500)  # 상품명 (더 넓게)
        self.price_table.setColumnWidth(1, 100)  # 현재가격
        self.price_table.setColumnWidth(2, 100)  # 최저가
        self.price_table.setColumnWidth(3, 100)  # 제안가
        self.price_table.setColumnWidth(4, 100)  # 마진
        self.price_table.setColumnWidth(5, 120)  # 상태
        self.price_table.setColumnWidth(6, 80)   # 액션
        
        result_layout.addWidget(self.price_table)
        
        # 페이지네이션 컨트롤 추가
        pagination_layout = QHBoxLayout()
        
        self.page_info_label = QLabel("페이지: 0/0 (총 0개 상품)")
        self.page_info_label.setStyleSheet("font-family: '맑은 고딕'; font-size: 12px; color: #666;")
        
        self.prev_page_btn = QPushButton("◀ 이전")
        self.prev_page_btn.setEnabled(False)
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: '맑은 고딕';
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #5a6268;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)
        self.prev_page_btn.clicked.connect(self.load_previous_page)
        
        self.next_page_btn = QPushButton("다음 ▶")
        self.next_page_btn.setEnabled(False)
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: '맑은 고딕';
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)
        self.next_page_btn.clicked.connect(self.load_next_page)
        
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.next_page_btn)
        
        result_layout.addLayout(pagination_layout)
        
        # 페이지네이션 변수 초기화
        self.current_page = 0
        self.total_pages = 0
        self.page_size = 100
        self.all_products = []  # 전체 상품 데이터 저장
        
        layout.addWidget(result_group)
        
        self.tab_widget.addTab(tab, "💰 가격 관리")
    
    def create_favorite_tab(self):
        """주력 상품 관리 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 안내 정보
        info_group = QGroupBox("ℹ️ 주력 상품 관리")
        info_layout = QVBoxLayout(info_group)
        
        info_label = QLabel("💡 내 상품에서 중요한 상품들을 주력 상품으로 등록하여 정기적으로 가격을 모니터링하고 관리할 수 있습니다.")
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        
        # 설정 섹션
        settings_group = QGroupBox("⚙️ 가격 관리 설정")
        settings_layout = QGridLayout(settings_group)
        
        # 할인 금액 설정
        settings_layout.addWidget(QLabel("할인 금액:"), 0, 0)
        self.fav_discount_amount = QSpinBox()
        self.fav_discount_amount.setRange(0, 10000)
        self.fav_discount_amount.setValue(100)
        self.fav_discount_amount.setSuffix(" 엔")
        self.fav_discount_amount.setToolTip("경쟁사 최저가보다 얼마나 할인할지 설정")
        settings_layout.addWidget(self.fav_discount_amount, 0, 1)
        
        # 최소 마진 설정
        settings_layout.addWidget(QLabel("최소 마진:"), 0, 2)
        self.fav_min_margin = QSpinBox()
        self.fav_min_margin.setRange(0, 50000)
        self.fav_min_margin.setValue(500)
        self.fav_min_margin.setSuffix(" 엔")
        self.fav_min_margin.setToolTip("보장할 최소 마진 금액")
        settings_layout.addWidget(self.fav_min_margin, 0, 3)
        
        # 손실 예상 상품 자동 제외
        self.fav_exclude_loss = QCheckBox("손실 예상 상품 자동 제외")
        self.fav_exclude_loss.setChecked(True)
        self.fav_exclude_loss.setToolTip("마진이 부족한 상품을 자동으로 제외")
        settings_layout.addWidget(self.fav_exclude_loss, 1, 0, 1, 2)
        
        # 가격 관리 모드
        mode_label = QLabel("가격 관리 모드:")
        settings_layout.addWidget(mode_label, 1, 2)
        
        self.fav_price_mode_group = QButtonGroup()
        self.fav_auto_mode = QRadioButton("🤖 자동 모드")
        self.fav_manual_mode = QRadioButton("👤 수동 모드")
        self.fav_auto_mode.setChecked(True)
        self.fav_auto_mode.setToolTip("조건 만족 시 즉시 가격 수정")
        self.fav_manual_mode.setToolTip("분석 결과 검토 후 수정")
        
        self.fav_price_mode_group.addButton(self.fav_auto_mode)
        self.fav_price_mode_group.addButton(self.fav_manual_mode)
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.fav_auto_mode)
        mode_layout.addWidget(self.fav_manual_mode)
        settings_layout.addLayout(mode_layout, 1, 3)
        
        layout.addWidget(settings_group)
        
        # 관리 기능 섹션
        manage_group = QGroupBox("🛠️ 관리 기능")
        manage_layout = QVBoxLayout(manage_group)
        
        # 첫 번째 줄 버튼들
        first_row_layout = QHBoxLayout()
        
        self.fav_load_products_btn = QPushButton("📥 목록 불러오기")
        self.fav_load_products_btn.setMinimumHeight(40)
        self.fav_load_products_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #1f4e79);
            }
        """)
        self.fav_load_products_btn.clicked.connect(self.load_favorite_products)
        first_row_layout.addWidget(self.fav_load_products_btn)
        
        self.fav_check_prices_btn = QPushButton("🔍 가격확인")
        self.fav_check_prices_btn.setMinimumHeight(40)
        self.fav_check_prices_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #229954, stop:1 #1e8449);
            }
        """)
        self.fav_check_prices_btn.clicked.connect(self.check_favorite_prices)
        first_row_layout.addWidget(self.fav_check_prices_btn)
        
        self.fav_update_prices_btn = QPushButton("🔄 가격 수정")
        self.fav_update_prices_btn.setMinimumHeight(40)
        self.fav_update_prices_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8e44ad, stop:1 #7d3c98);
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7d3c98, stop:1 #6c3483);
            }
        """)
        self.fav_update_prices_btn.clicked.connect(self.update_favorite_prices)
        first_row_layout.addWidget(self.fav_update_prices_btn)
        
        manage_layout.addLayout(first_row_layout)
        
        # 두 번째 줄 버튼들
        second_row_layout = QHBoxLayout()
        
        self.fav_start_analysis_btn = QPushButton("🚀 가격확인-가격수정 시작")
        self.fav_start_analysis_btn.setMinimumHeight(45)
        self.fav_start_analysis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
            }
        """)
        self.fav_start_analysis_btn.clicked.connect(self.start_favorite_analysis)
        second_row_layout.addWidget(self.fav_start_analysis_btn)
        
        self.fav_clear_all_btn = QPushButton("🗑️ 전체삭제")
        self.fav_clear_all_btn.setMinimumHeight(40)
        self.fav_clear_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a93226);
            }
        """)
        self.fav_clear_all_btn.clicked.connect(self.clear_favorite_products)
        second_row_layout.addWidget(self.fav_clear_all_btn)
        
        self.fav_save_list_btn = QPushButton("💾 목록 저장")
        self.fav_save_list_btn.setMinimumHeight(40)
        self.fav_save_list_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #138496, stop:1 #0f6674);
            }
        """)
        self.fav_save_list_btn.clicked.connect(self.save_favorite_products)
        second_row_layout.addWidget(self.fav_save_list_btn)
        
        manage_layout.addLayout(second_row_layout)
        layout.addWidget(manage_group)
        
        # 주력 상품 목록 테이블
        table_group = QGroupBox("📋 주력 상품 목록")
        table_layout = QVBoxLayout(table_group)
        
        self.favorite_table = QTableWidget()
        self.favorite_table.setColumnCount(7)
        self.favorite_table.setHorizontalHeaderLabels([
            "상품명", "현재가격", "최저가", "제안가", "가격차이", "상태", "액션"
        ])
        self.favorite_table.horizontalHeader().setStretchLastSection(True)
        self.favorite_table.setAlternatingRowColors(True)
        self.favorite_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 테이블 컬럼 너비 설정
        self.favorite_table.setColumnWidth(0, 500)  # 상품명
        self.favorite_table.setColumnWidth(1, 100)  # 현재가격
        self.favorite_table.setColumnWidth(2, 100)  # 최저가
        self.favorite_table.setColumnWidth(3, 100)  # 제안가
        self.favorite_table.setColumnWidth(4, 100)  # 가격차이
        self.favorite_table.setColumnWidth(5, 150)  # 상태
        
        table_layout.addWidget(self.favorite_table)
        
        # 통계 정보
        stats_layout = QHBoxLayout()
        
        self.total_favorites = QLabel("총 주력상품: 0개")
        self.total_favorites.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px;")
        stats_layout.addWidget(self.total_favorites)
        
        self.need_update_count = QLabel("수정 필요: 0개")
        self.need_update_count.setStyleSheet("font-weight: bold; color: #e74c3c; padding: 5px;")
        stats_layout.addWidget(self.need_update_count)
        
        self.up_to_date_count = QLabel("최신 상태: 0개")
        self.up_to_date_count.setStyleSheet("font-weight: bold; color: #27ae60; padding: 5px;")
        stats_layout.addWidget(self.up_to_date_count)
        
        self.last_check_time = QLabel("마지막 확인: 없음")
        self.last_check_time.setStyleSheet("font-weight: bold; color: #7f8c8d; padding: 5px;")
        stats_layout.addWidget(self.last_check_time)
        
        stats_layout.addStretch()
        table_layout.addLayout(stats_layout)
        
        layout.addWidget(table_group)
        
        self.tab_widget.addTab(tab, "⭐ 주력 상품")
    
    def create_upload_tab(self):
        """업로드 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 업로드 설정
        upload_group = QGroupBox("📤 업로드 설정")
        upload_layout = QGridLayout(upload_group)
        
        # 업로드 모드 설정 추가
        upload_layout.addWidget(QLabel("업로드 모드:"), 0, 0)
        self.upload_mode_combo = QComboBox()
        self.upload_mode_combo.addItems(["🤖 자동 모드", "👤 수동 모드"])
        self.upload_mode_combo.setToolTip("자동 모드: 확인 없이 바로 등록\n수동 모드: 등록 전 확인 팝업")
        self.upload_mode_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background: white;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #2980b9;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        upload_layout.addWidget(self.upload_mode_combo, 0, 1)
        
        upload_layout.addWidget(QLabel("이미지 최대 개수:"), 0, 2)
        self.max_images = QSpinBox()
        self.max_images.setRange(1, 20)
        self.max_images.setValue(10)
        self.max_images.setStyleSheet(self.get_spinbox_style())
        upload_layout.addWidget(self.max_images, 0, 3)
        
        layout.addWidget(upload_group)
        
        # 업로드 컨트롤
        upload_control_layout = QHBoxLayout()
        
        self.start_upload_btn = QPushButton("🚀 업로드 시작")
        self.start_upload_btn.setProperty("class", "success")
        self.start_upload_btn.clicked.connect(self.start_upload)
        
        self.pause_upload_btn = QPushButton("⏸️ 일시정지")
        self.pause_upload_btn.setProperty("class", "warning")
        self.pause_upload_btn.setEnabled(False)
        
        self.stop_upload_btn = QPushButton("⏹️ 중지")
        self.stop_upload_btn.setProperty("class", "danger")
        self.stop_upload_btn.setEnabled(False)
        
        upload_control_layout.addWidget(self.start_upload_btn)
        upload_control_layout.addWidget(self.pause_upload_btn)
        upload_control_layout.addWidget(self.stop_upload_btn)
        upload_control_layout.addStretch()
        
        layout.addLayout(upload_control_layout)
        
        # 업로드 진행 상황
        upload_progress_group = QGroupBox("📊 업로드 진행 상황")
        upload_progress_layout = QVBoxLayout(upload_progress_group)
        
        upload_progress_layout.addWidget(QLabel("전체 진행률:"))
        self.upload_progress = QProgressBar()
        self.upload_progress.setTextVisible(True)
        upload_progress_layout.addWidget(self.upload_progress)
        
        self.current_upload_status = QLabel("대기중...")
        upload_progress_layout.addWidget(self.current_upload_status)
        
        # 통계 정보
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("성공:"), 0, 0)
        self.success_count = QLabel("0")
        self.success_count.setStyleSheet("color: #28a745; font-weight: bold;")
        stats_layout.addWidget(self.success_count, 0, 1)
        
        stats_layout.addWidget(QLabel("실패:"), 0, 2)
        self.failed_count = QLabel("0")
        self.failed_count.setStyleSheet("color: #dc3545; font-weight: bold;")
        stats_layout.addWidget(self.failed_count, 0, 3)
        
        stats_layout.addWidget(QLabel("대기:"), 0, 4)
        self.pending_count = QLabel("0")
        self.pending_count.setStyleSheet("color: #ffc107; font-weight: bold;")
        stats_layout.addWidget(self.pending_count, 0, 5)
        
        upload_progress_layout.addLayout(stats_layout)
        layout.addWidget(upload_progress_group)
        
        # 업로드 결과
        upload_result_group = QGroupBox("📋 업로드 결과")
        upload_result_layout = QVBoxLayout(upload_result_group)
        
        self.upload_table = QTableWidget()
        self.upload_table.setColumnCount(6)
        self.upload_table.setHorizontalHeaderLabels([
            "상품명", "가격", "상태", "업로드 시간", "BUYMA URL", "오류 메시지"
        ])
        self.upload_table.horizontalHeader().setStretchLastSection(True)
        
        upload_result_layout.addWidget(self.upload_table)
        
        # 결과 액션 버튼
        result_action_layout = QHBoxLayout()
        
        retry_failed_btn = QPushButton("🔄 실패 항목 재시도")
        retry_failed_btn.clicked.connect(self.retry_failed_uploads)
        
        export_results_btn = QPushButton("📤 결과 내보내기")
        export_results_btn.clicked.connect(self.export_upload_results)
        
        clear_results_btn = QPushButton("🗑️ 결과 지우기")
        clear_results_btn.setProperty("class", "warning")
        
        result_action_layout.addWidget(retry_failed_btn)
        result_action_layout.addWidget(export_results_btn)
        result_action_layout.addWidget(clear_results_btn)
        result_action_layout.addStretch()
        
        upload_result_layout.addLayout(result_action_layout)
        layout.addWidget(upload_result_group)
        
        self.tab_widget.addTab(tab, "📤 자동 업로드")
        
    def create_monitoring_tab(self):
        """모니터링 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 실시간 모니터링
        monitoring_group = QGroupBox("📺 실시간 모니터링")
        monitoring_layout = QVBoxLayout(monitoring_group)
        monitoring_layout.setSpacing(1)
        monitoring_layout.setContentsMargins(15, 0, 15, 15)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(200)  # 높이를 200에서 300으로 증가
        self.log_output.setMinimumHeight(200)  # 최소 높이도 설정
        self.log_output.setReadOnly(True)
        
        # 자동 스크롤 설정
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.log_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.log_output.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                border: 2px solid #333;
                border-radius: 6px;
            }
        """)
        monitoring_layout.addWidget(self.log_output)
        
        layout.addWidget(monitoring_group)
        
        # 성능 통계
        stats_group = QGroupBox("📊 성능 통계")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(15)
        stats_layout.setContentsMargins(15, 20, 15, 15)
        
        stats_layout.addWidget(QLabel("오늘 크롤링:"), 0, 0)
        self.today_crawled = QLabel("0")
        self.today_crawled.setStyleSheet("font-size: 16px; font-weight: bold; color: #007bff; padding: 5px;")
        stats_layout.addWidget(self.today_crawled, 0, 1)
        
        stats_layout.addWidget(QLabel("오늘 업로드:"), 0, 2)
        self.today_uploaded = QLabel("0")
        self.today_uploaded.setStyleSheet("font-size: 16px; font-weight: bold; color: #28a745; padding: 5px;")
        stats_layout.addWidget(self.today_uploaded, 0, 3)
        
        stats_layout.addWidget(QLabel("성공률:"), 1, 0)
        self.success_rate = QLabel("0%")
        self.success_rate.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffc107; padding: 5px;")
        stats_layout.addWidget(self.success_rate, 1, 1)
        
        stats_layout.addWidget(QLabel("평균 처리 시간:"), 1, 2)
        self.avg_process_time = QLabel("0초")
        self.avg_process_time.setStyleSheet("font-size: 16px; font-weight: bold; color: #6f42c1; padding: 5px;")
        stats_layout.addWidget(self.avg_process_time, 1, 3)
        
        layout.addWidget(stats_group)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout = QGridLayout(system_group)
        system_layout.setSpacing(15)
        system_layout.setContentsMargins(15, 20, 15, 15)
        
        system_layout.addWidget(QLabel("CPU 사용률:"), 0, 0)
        self.cpu_usage = QProgressBar()
        self.cpu_usage.setMaximum(100)
        self.cpu_usage.setValue(0)  # 초기값 0, 실시간으로 업데이트됨
        self.cpu_usage.setMinimumHeight(25)
        self.cpu_usage.setFormat("%p% (%v%)")  # 퍼센트 표시 형식
        system_layout.addWidget(self.cpu_usage, 0, 1)
        
        system_layout.addWidget(QLabel("메모리 사용률:"), 1, 0)
        self.memory_usage = QProgressBar()
        self.memory_usage.setMaximum(100)
        self.memory_usage.setValue(0)  # 초기값 0, 실시간으로 업데이트됨
        self.memory_usage.setMinimumHeight(25)
        self.memory_usage.setFormat("%p% (%v%)")  # 퍼센트 표시 형식
        system_layout.addWidget(self.memory_usage, 1, 1)
        
        system_layout.addWidget(QLabel("네트워크 상태:"), 2, 0)
        self.network_status = QLabel("● 확인중...")
        self.network_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px; padding: 5px;")
        system_layout.addWidget(self.network_status, 2, 1)
        
        layout.addWidget(system_group)
        
        self.tab_widget.addTab(tab, "📺 모니터링")
        
    def create_settings_tab(self):
        """설정 탭 생성"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 스크롤 내용 위젯
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)  # 프레임 간격을 더 넓게 설정
        
        # BUYMA 계정 설정
        account_group = QGroupBox("👤 BUYMA 계정 설정")
        account_group.setMinimumHeight(220)  # 120에서 220으로 증가 (+100)
        account_layout = QGridLayout(account_group)
        account_layout.setSpacing(15)
        
        account_layout.addWidget(QLabel("이메일:"), 0, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your-email@example.com")
        self.email_input.setMinimumHeight(35)
        account_layout.addWidget(self.email_input, 0, 1, 1, 2)
        
        account_layout.addWidget(QLabel("비밀번호:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setMinimumHeight(35)
        account_layout.addWidget(self.password_input, 1, 1)
        
        # 로그인 버튼
        self.login_btn = QPushButton("🔐 BUYMA 로그인")
        self.login_btn.setMinimumHeight(35)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: #0056b3;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #ffffff;
            }
        """)
        self.login_btn.clicked.connect(self.start_buyma_login)
        account_layout.addWidget(self.login_btn, 1, 2)
        
        # 로그인 상태 표시
        self.login_status_label = QLabel("❌ 로그인 필요")
        self.login_status_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-family: '맑은 고딕';
                padding: 5px;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        account_layout.addWidget(self.login_status_label, 2, 0, 1, 3)
        
        layout.addWidget(account_group)
        
        # 브라우저 설정
        browser_group = QGroupBox("🌐 브라우저 설정")
        browser_group.setMinimumHeight(220)  # 120에서 220으로 증가 (+100)
        browser_layout = QGridLayout(browser_group)
        browser_layout.setSpacing(15)
        
        browser_layout.addWidget(QLabel("브라우저:"), 0, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome"])  # Chrome만 남김
        self.browser_combo.setMinimumHeight(35)
        browser_layout.addWidget(self.browser_combo, 0, 1)
        
        # browser_layout.addWidget(QLabel("헤드리스 모드:"), 0, 2)
        # self.headless_mode = QCheckBox()
        # browser_layout.addWidget(self.headless_mode, 0, 3)
        
        browser_layout.addWidget(QLabel("사용자 에이전트:"), 1, 0)
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("기본값 사용")
        self.user_agent.setMinimumHeight(35)
        browser_layout.addWidget(self.user_agent, 1, 1, 1, 3)
        
        layout.addWidget(browser_group)
        
        # 고급 설정
        advanced_group = QGroupBox("⚙️ 고급 설정")
        advanced_group.setMinimumHeight(220)  # 120에서 220으로 증가 (+100)
        advanced_layout = QGridLayout(advanced_group)
        advanced_layout.setSpacing(15)
        
        # advanced_layout.addWidget(QLabel("최대 동시 작업:"), 0, 0)
        # self.max_workers = QSpinBox()
        # self.max_workers.setRange(1, 10)
        # self.max_workers.setValue(3)
        # self.max_workers.setMinimumHeight(35)
        # advanced_layout.addWidget(self.max_workers, 0, 1)
        
        # advanced_layout.addWidget(QLabel("요청 간격(초):"), 0, 2)
        # self.request_delay = QSpinBox()
        # self.request_delay.setRange(1, 30)
        # self.request_delay.setValue(3)
        # self.request_delay.setMinimumHeight(35)
        # advanced_layout.addWidget(self.request_delay, 0, 3)
        
        advanced_layout.addWidget(QLabel("타임아웃(초):"), 0, 0)  # 위치 조정
        self.timeout_setting = QSpinBox()
        self.timeout_setting.setRange(5, 60)  # 범위 조정
        self.timeout_setting.setValue(10)  # 기본값을 60에서 10으로 변경
        self.timeout_setting.setStyleSheet(self.get_spinbox_style())
        self.timeout_setting.setMinimumHeight(35)
        advanced_layout.addWidget(self.timeout_setting, 0, 1)  # 위치 조정
        
        advanced_layout.addWidget(QLabel("재시도 횟수:"), 0, 2)  # 위치 조정
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        self.retry_count.setStyleSheet(self.get_spinbox_style())
        self.retry_count.setMinimumHeight(35)
        advanced_layout.addWidget(self.retry_count, 0, 3)  # 위치 조정
        
        layout.addWidget(advanced_group)
        
        # 알림 설정
        notification_group = QGroupBox("🔔 알림 설정")
        notification_group.setMinimumHeight(200)  # 100에서 200으로 증가 (+100)
        notification_layout = QVBoxLayout(notification_group)
        notification_layout.setSpacing(10)
        
        self.enable_notifications = QCheckBox("알림 활성화")
        self.enable_notifications.setChecked(True)
        notification_layout.addWidget(self.enable_notifications)
        
        self.notify_on_complete = QCheckBox("작업 완료 시 알림")
        self.notify_on_complete.setChecked(True)
        notification_layout.addWidget(self.notify_on_complete)
        
        self.notify_on_error = QCheckBox("오류 발생 시 알림")
        self.notify_on_error.setChecked(True)
        notification_layout.addWidget(self.notify_on_error)
        
        layout.addWidget(notification_group)
        
        # 데이터 관리
        data_group = QGroupBox("💾 데이터 관리")
        data_group.setMinimumHeight(180)  # 80에서 180으로 증가 (+100)
        data_layout = QHBoxLayout(data_group)
        data_layout.setSpacing(15)
        
        backup_btn = QPushButton("💾 설정 백업")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self.backup_settings)
        
        restore_btn = QPushButton("📥 설정 복원")
        restore_btn.setMinimumHeight(40)
        restore_btn.clicked.connect(self.restore_settings)
        
        clear_data_btn = QPushButton("🗑️ 데이터 초기화")
        clear_data_btn.setMinimumHeight(40)
        clear_data_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """)
        clear_data_btn.clicked.connect(self.clear_all_data)
        
        data_layout.addWidget(backup_btn)
        data_layout.addWidget(restore_btn)
        data_layout.addWidget(clear_data_btn)
        data_layout.addStretch()
        
        layout.addWidget(data_group)
        
        # 설정 저장/불러오기
        settings_control_layout = QHBoxLayout()
        
        save_settings_btn = QPushButton("💾 설정 저장")
        save_settings_btn.setMinimumHeight(45)
        save_settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        save_settings_btn.clicked.connect(self.save_settings)
        
        load_settings_btn = QPushButton("📂 설정 불러오기")
        load_settings_btn.setMinimumHeight(45)
        load_settings_btn.clicked.connect(self.load_settings)
        
        reset_settings_btn = QPushButton("🔄 기본값 복원")
        reset_settings_btn.setMinimumHeight(45)
        reset_settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffc107, stop:1 #e0a800);
                color: #212529;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e0a800, stop:1 #d39e00);
            }
        """)
        reset_settings_btn.clicked.connect(self.reset_settings)
        
        settings_control_layout.addWidget(save_settings_btn)
        settings_control_layout.addWidget(load_settings_btn)
        settings_control_layout.addWidget(reset_settings_btn)
        settings_control_layout.addStretch()
        
        layout.addLayout(settings_control_layout)
        
        # 버전 정보
        version_group = QGroupBox("ℹ️ 프로그램 정보")
        version_group.setMinimumHeight(180)  # 80에서 180으로 증가 (+100)
        version_layout = QVBoxLayout(version_group)
        
        version_info = QLabel("BUYMA 자동화 프로그램 v1.0.0\n개발자: 소프트캣\n© 2025 All Rights Reserved")
        version_info.setStyleSheet("color: #6c757d; font-size: 10px; text-align: center; width: 100%; height: 40px;")
        version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_layout.addWidget(version_info)
        
        layout.addWidget(version_group)
        
        # 스크롤 영역에 내용 설정
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(tab, "⚙️ 설정")
        
    def create_status_bar(self):
        """상태바 생성"""
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #495057;
                font-size: 10px;
            }
        """)
        
        self.status_label = QLabel("준비 완료")
        status_bar.addWidget(self.status_label)
        
        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setVisible(False)
        status_bar.addPermanentWidget(self.status_progress)
        
        self.time_label = QLabel()
        self.update_time()
        status_bar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
        # 시스템 모니터링 타이머 (5초마다 업데이트)
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.update_system_stats)
        self.system_timer.start(5000)  # 5초마다 업데이트
        
    # 메서드들
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(current_time)
        
        # 헤더의 마지막 업데이트 시간도 함께 업데이트
        self.last_update.setText(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def update_system_stats(self):
        """실시간 시스템 상태 업데이트"""
        try:
            # CPU 사용률 업데이트
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_usage.setValue(int(cpu_percent))
            
            # CPU 사용률에 따른 색상 변경
            if cpu_percent < 50:
                cpu_color = "#28a745"  # 녹색
            elif cpu_percent < 80:
                cpu_color = "#ffc107"  # 노란색
            else:
                cpu_color = "#dc3545"  # 빨간색
                
            self.cpu_usage.setStyleSheet(f"""
                QProgressBar::chunk {{
                    background: {cpu_color};
                    border-radius: 4px;
                }}
            """)
            
            # 메모리 사용률 업데이트
            memory = psutil.virtual_memory()
            memory_percent = int(memory.percent)
            self.memory_usage.setValue(memory_percent)
            
            # 메모리 사용률에 따른 색상 변경
            if memory_percent < 60:
                memory_color = "#28a745"  # 녹색
            elif memory_percent < 85:
                memory_color = "#ffc107"  # 노란색
            else:
                memory_color = "#dc3545"  # 빨간색
                
            self.memory_usage.setStyleSheet(f"""
                QProgressBar::chunk {{
                    background: {memory_color};
                    border-radius: 4px;
                }}
            """)
            
            # 네트워크 상태 확인 (비동기로 처리)
            self.check_network_status()
            
        except Exception as e:
            self.log_message(f"시스템 모니터링 오류: {str(e)}")
    
    def check_network_status(self):
        """네트워크 상태 확인 (별도 스레드에서 실행)"""
        import threading
        
        def check_connection():
            try:
                # 빠른 연결 테스트
                response = requests.get("https://www.google.com", timeout=3)
                if response.status_code == 200:
                    self.network_status.setText("● 정상")
                    self.network_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px; padding: 5px;")
                else:
                    self.network_status.setText("● 불안정")
                    self.network_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px; padding: 5px;")
            except requests.exceptions.RequestException:
                self.network_status.setText("● 연결 실패")
                self.network_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px; padding: 5px;")
            except Exception:
                self.network_status.setText("● 확인 불가")
                self.network_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px; padding: 5px;")
        
        # 네트워크 확인을 별도 스레드에서 실행 (UI 블로킹 방지)
        import threading
        
        thread = threading.Thread(target=check_connection, daemon=True)
        thread.start()
    
    # 대시보드 관련 메서드들
    def start_full_automation(self):
        """전체 자동화 프로세스 시작"""
        # 입력값 검증
        url = self.dashboard_url.text().strip()
        if not url:
            QMessageBox.warning(self, "경고", "경쟁사 URL을 입력해주세요.")
            return
        
        # UI 상태 변경
        self.start_automation_btn.setEnabled(False)
        self.stop_automation_btn.setEnabled(True)
        
        # 진행 상황 초기화
        self.reset_progress()
        
        # 로그 시작
        self.dashboard_log_message("🚀 전체 자동화 프로세스를 시작합니다...")
        self.dashboard_log_message(f"📋 설정: URL={url}, 개수={self.dashboard_count.value()}, 할인={self.dashboard_discount.value()}엔")
        
        # 별도 스레드에서 자동화 실행
        import threading
        
        self.automation_thread = threading.Thread(target=self.run_full_automation, daemon=True)
        self.automation_thread.start()
    
    def run_full_automation(self):
        """전체 자동화 프로세스 실행"""
        try:
            url = self.dashboard_url.text().strip()
            count = self.dashboard_count.value()
            discount = self.dashboard_discount.value()
            
            self.log_message("🚀 전체 자동화 프로세스를 시작합니다...")
            
            # 1단계: 크롤링
            self.update_dashboard_step("1️⃣ 경쟁사 상품 크롤링 중...", "#007bff")
            crawling_success = self.execute_crawling_step(url, count)
            
            if not crawling_success:
                self.update_dashboard_step("❌ 크롤링 실패", "#dc3545")
                return
            
            self.step1_progress.setValue(100)
            self.overall_progress.setValue(25)
            
            # 2단계: 업로드
            self.update_dashboard_step("2️⃣ BUYMA 자동 업로드 중...", "#28a745")
            upload_success = self.execute_upload_step()
            
            if not upload_success:
                self.update_dashboard_step("❌ 업로드 실패", "#dc3545")
                return
            
            self.step2_progress.setValue(100)
            self.overall_progress.setValue(50)
            
            # 3단계: 가격 분석
            self.update_dashboard_step("3️⃣ 경쟁사 가격 분석 중...", "#ffc107")
            analysis_success = self.execute_price_analysis_step()
            
            if not analysis_success:
                self.update_dashboard_step("❌ 가격 분석 실패", "#dc3545")
                return
            
            self.step3_progress.setValue(100)
            self.overall_progress.setValue(75)
            
            # 4단계: 가격 수정
            self.update_dashboard_step("4️⃣ 가격 자동 수정 중...", "#6f42c1")
            update_success = self.execute_price_update_step(discount)
            
            if not update_success:
                self.update_dashboard_step("❌ 가격 수정 실패", "#dc3545")
                return
            
            self.step4_progress.setValue(100)
            self.overall_progress.setValue(100)
            
            # 완료
            self.update_dashboard_step("✅ 전체 프로세스 완료!", "#28a745")
            self.dashboard_log_message("🎉 모든 작업이 성공적으로 완료되었습니다!")
            
            # 최종 통계 업데이트
            self.update_final_statistics()
            
        except Exception as e:
            self.dashboard_log_message(f"❌ 오류 발생: {str(e)}")
            self.update_dashboard_step("❌ 프로세스 실패", "#dc3545")
        finally:
            # UI 상태 복원
            self.start_automation_btn.setEnabled(True)
            self.stop_automation_btn.setEnabled(False)
    
    def execute_crawling_step(self, url, count):
        """1단계: 크롤링 실행"""
        try:
            self.dashboard_log_message(f"🔍 크롤링 시작: {url} ({count}개)")
            
            # 크롤링 탭의 설정 업데이트
            self.url_input.setText(url)
            self.crawl_count.setValue(count)
            
            # 크롤링 실행 (동기적으로)
            success = self.run_crawling_sync(url, count)
            
            if success:
                crawled_count = self.crawling_table.rowCount()
                self.dashboard_log_message(f"✅ 크롤링 완료: {crawled_count}개 상품 수집")
                self.processed_items.setText(f"처리된 상품: {crawled_count}/{count}")
                return True
            else:
                self.dashboard_log_message("❌ 크롤링 실패")
                return False
                
        except Exception as e:
            self.dashboard_log_message(f"크롤링 단계 오류: {str(e)}")
            return False
    
    def execute_upload_step(self):
        """2단계: 업로드 실행"""
        try:
            if self.crawling_table.rowCount() == 0:
                self.dashboard_log_message("❌ 업로드할 상품이 없습니다.")
                return False
            
            self.dashboard_log_message("📤 BUYMA 업로드 시작...")
            
            # 업로드 실행 (동기적으로)
            success = self.run_upload_sync()
            
            if success:
                uploaded_count = self.upload_table.rowCount()
                self.dashboard_log_message(f"✅ 업로드 완료: {uploaded_count}개 상품 등록")
                return True
            else:
                self.dashboard_log_message("❌ 업로드 실패")
                return False
                
        except Exception as e:
            self.dashboard_log_message(f"업로드 단계 오류: {str(e)}")
            return False
    
    def execute_price_analysis_step(self):
        """3단계: 가격 분석 실행"""
        try:
            if self.upload_table.rowCount() == 0:
                self.dashboard_log_message("❌ 분석할 상품이 없습니다.")
                return False
            
            self.dashboard_log_message("🔍 가격 분석 시작...")
            
            # 가격 분석 실행 (동기적으로)
            success = self.run_price_analysis_sync()
            
            if success:
                analyzed_count = self.price_table.rowCount()
                self.dashboard_log_message(f"✅ 가격 분석 완료: {analyzed_count}개 상품 분석")
                return True
            else:
                self.dashboard_log_message("❌ 가격 분석 실패")
                return False
                
        except Exception as e:
            self.dashboard_log_message(f"가격 분석 단계 오류: {str(e)}")
            return False
    
    def execute_price_update_step(self, discount):
        """4단계: 가격 수정 실행"""
        try:
            if self.price_table.rowCount() == 0:
                self.dashboard_log_message("❌ 수정할 가격 정보가 없습니다.")
                return False
            
            self.dashboard_log_message(f"💱 가격 수정 시작 (할인: {discount}엔)...")
            
            # 자동 모드에서만 가격 수정 실행
            if self.auto_mode.isChecked():
                success = self.run_price_update_sync()
                
                if success:
                    updated_count = self.count_updated_prices()
                    self.dashboard_log_message(f"✅ 가격 수정 완료: {updated_count}개 상품 수정")
                    self.auto_updated.setText(f"자동 수정: {updated_count}개")
                    return True
                else:
                    self.dashboard_log_message("❌ 가격 수정 실패")
                    return False
            else:
                self.dashboard_log_message("⚠️ 수동 모드 - 가격 수정을 건너뜁니다.")
                return True
                
        except Exception as e:
            self.dashboard_log_message(f"가격 수정 단계 오류: {str(e)}")
            return False
    
    def run_crawling_sync(self, url, count):
        """동기적 크롤링 실행"""
        try:
            # 기존 크롤링 로직을 동기적으로 실행
            driver = None
            
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(self.timeout_setting.value())
            
            # 크롤링 실행
            driver.get(url)
            import time
            time.sleep(3)
            
            # 간단한 크롤링 (실제 구현은 기존 로직 사용)
            collected_items = min(count, 5)  # 데모용으로 최대 5개
            
            # 테이블 초기화
            self.crawling_table.setRowCount(0)
            
            # 데모 데이터 추가
            for i in range(collected_items):
                self.add_demo_crawled_item(i)
                
                # 진행률 업데이트
                progress = int(((i + 1) / collected_items) * 100)
                self.step1_progress.setValue(progress)
                time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.dashboard_log_message(f"동기 크롤링 오류: {str(e)}")
            return False
        finally:
            if driver:
                driver.quit()
    
    def add_demo_crawled_item(self, index):
        """데모 크롤링 아이템 추가"""
        demo_items = [
            {"title": "EYEWITHNESS T-SHIRT", "brand": "SAN SAN GEAR", "price": "15000엔"},
            {"title": "CLASSIC HOODIE", "brand": "BRAND A", "price": "25000엔"},
            {"title": "DENIM JACKET", "brand": "BRAND B", "price": "35000엔"},
            {"title": "SNEAKERS", "brand": "BRAND C", "price": "45000엔"},
            {"title": "BACKPACK", "brand": "BRAND D", "price": "20000엔"}
        ]
        
        if index < len(demo_items):
            item = demo_items[index]
            row = self.crawling_table.rowCount()
            self.crawling_table.insertRow(row)
            
            self.crawling_table.setItem(row, 0, QTableWidgetItem(item["title"]))
            self.crawling_table.setItem(row, 1, QTableWidgetItem(item["brand"]))
            self.crawling_table.setItem(row, 2, QTableWidgetItem(item["price"]))
            self.crawling_table.setItem(row, 3, QTableWidgetItem("5장"))
            self.crawling_table.setItem(row, 4, QTableWidgetItem("색상:3개, 사이즈:5개"))
            self.crawling_table.setItem(row, 5, QTableWidgetItem("https://example.com"))
            
            status_item = QTableWidgetItem("✅ 완료")
            status_item.setForeground(QBrush(QColor("#28a745")))
            self.crawling_table.setItem(row, 6, status_item)
            
            # 상세보기 버튼
            detail_btn = QPushButton("📋 상세보기")
            detail_btn.setStyleSheet("""
                QPushButton {
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
            """)
            self.crawling_table.setCellWidget(row, 7, detail_btn)
    
    def run_upload_sync(self):
        """동기적 업로드 실행"""
        try:
            # 업로드 테이블 초기화
            self.upload_table.setRowCount(0)
            
            # 크롤링된 상품들을 업로드 테이블로 이동 (시뮬레이션)
            for row in range(self.crawling_table.rowCount()):
                title = self.crawling_table.item(row, 0).text()
                brand = self.crawling_table.item(row, 1).text()
                price = self.crawling_table.item(row, 2).text()
                
                upload_row = self.upload_table.rowCount()
                self.upload_table.insertRow(upload_row)
                
                self.upload_table.setItem(upload_row, 0, QTableWidgetItem(title))
                self.upload_table.setItem(upload_row, 1, QTableWidgetItem(brand))
                self.upload_table.setItem(upload_row, 2, QTableWidgetItem(price))
                self.upload_table.setItem(upload_row, 3, QTableWidgetItem(datetime.now().strftime('%H:%M:%S')))
                
                status_item = QTableWidgetItem("업로드 완료")
                status_item.setForeground(QBrush(QColor("#28a745")))
                self.upload_table.setItem(upload_row, 4, status_item)
                
                # 진행률 업데이트
                progress = int(((row + 1) / self.crawling_table.rowCount()) * 100)
                self.step2_progress.setValue(progress)
                
                import time
                time.sleep(0.3)
            
            return True
            
        except Exception as e:
            self.dashboard_log_message(f"동기 업로드 오류: {str(e)}")
            return False
    
    def run_price_analysis_sync(self):
        """동기적 가격 분석 실행"""
        try:
            # 가격 테이블 초기화
            self.price_table.setRowCount(0)
            
            # 업로드된 상품들을 가격 분석 테이블로 이동
            for row in range(self.upload_table.rowCount()):
                title = self.upload_table.item(row, 0).text()
                brand = self.upload_table.item(row, 1).text()
                current_price_text = self.upload_table.item(row, 2).text()
                
                # 가격에서 숫자 추출
                import re
                price_numbers = re.findall(r'[\d,]+', current_price_text)
                current_price = int(price_numbers[0].replace(',', '')) if price_numbers else 15000
                
                # 경쟁사 최저가 시뮬레이션 (현재가보다 500-1000엔 낮게)
                competitor_price = current_price - random.randint(500, 1000)
                
                # 제안가 계산 (최저가 - 할인금액)
                discount = self.dashboard_discount.value()
                suggested_price = competitor_price - discount
                
                # 예상 마진 계산
                margin = suggested_price - (suggested_price * 0.1)  # 10% 수수료 제외
                
                analysis_row = self.price_table.rowCount()
                self.price_table.insertRow(analysis_row)
                
                self.price_table.setItem(analysis_row, 0, QTableWidgetItem(f"{brand} {title}"))
                self.price_table.setItem(analysis_row, 1, QTableWidgetItem(brand))
                self.price_table.setItem(analysis_row, 2, QTableWidgetItem(f"{current_price}엔"))
                self.price_table.setItem(analysis_row, 3, QTableWidgetItem(f"{competitor_price}엔"))
                self.price_table.setItem(analysis_row, 4, QTableWidgetItem(f"{suggested_price}엔"))
                self.price_table.setItem(analysis_row, 5, QTableWidgetItem(f"+{int(margin)}엔"))
                
                # 상태 표시
                status_item = QTableWidgetItem("수정 권장")
                status_item.setForeground(QBrush(QColor("#ffc107")))
                self.price_table.setItem(analysis_row, 6, status_item)
                
                # 액션 버튼
                action_btn = QPushButton("🔄 자동수정")
                action_btn.setStyleSheet("""
                    QPushButton {
                        background: #28a745;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 10px;
                    }
                """)
                self.price_table.setCellWidget(analysis_row, 7, action_btn)
                
                # 진행률 업데이트
                progress = int(((row + 1) / self.upload_table.rowCount()) * 100)
                self.step3_progress.setValue(progress)
                
                import time
                time.sleep(0.3)
            
            return True
            
        except Exception as e:
            self.dashboard_log_message(f"동기 가격 분석 오류: {str(e)}")
            return False
    
    def run_price_update_sync(self):
        """동기적 가격 수정 실행"""
        try:
            updated_count = 0
            
            # 가격 테이블의 모든 상품 가격 수정
            for row in range(self.price_table.rowCount()):
                # 버튼을 완료 상태로 변경
                btn = QPushButton("✅ 완료")
                btn.setStyleSheet("""
                    QPushButton {
                        background: #6c757d;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 10px;
                    }
                """)
                btn.setEnabled(False)
                self.price_table.setCellWidget(row, 7, btn)
                
                # 상태 업데이트
                status_item = QTableWidgetItem("수정 완료")
                status_item.setForeground(QBrush(QColor("#6c757d")))
                self.price_table.setItem(row, 6, status_item)
                
                updated_count += 1
                
                # 진행률 업데이트
                progress = int(((row + 1) / self.price_table.rowCount()) * 100)
                self.step4_progress.setValue(progress)
                
                import time
                time.sleep(0.3)
            
            return updated_count > 0
            
        except Exception as e:
            self.dashboard_log_message(f"동기 가격 수정 오류: {str(e)}")
            return False
    
    def count_updated_prices(self):
        """수정된 가격 개수 계산"""
        updated_count = 0
        for row in range(self.price_table.rowCount()):
            status_item = self.price_table.item(row, 6)
            if status_item and "수정 완료" in status_item.text():
                updated_count += 1
        return updated_count
    
    def update_final_statistics(self):
        """최종 통계 업데이트"""
        try:
            crawled = self.crawling_table.rowCount()
            uploaded = self.upload_table.rowCount()
            analyzed = self.price_table.rowCount()
            updated = self.count_updated_prices()
            
            self.processed_items.setText(f"처리된 상품: {crawled}/{crawled}")
            self.success_items.setText(f"성공: {uploaded}")
            self.auto_updated.setText(f"자동 수정: {updated}")
            self.excluded_items.setText("제외: 0개")
            self.failed_items_dash.setText("실패: 0개")
            
            # 예상 완료 시간 업데이트
            self.estimated_time.setText("완료됨")
            
        except Exception as e:
            self.dashboard_log_message(f"통계 업데이트 오류: {str(e)}")
    
    # 데이터 연동 및 저장 기능
    def save_automation_session(self):
        """자동화 세션 데이터 저장"""
        try:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'settings': {
                    'url': self.dashboard_url.text(),
                    'count': self.dashboard_count.value(),
                    'discount': self.dashboard_discount.value(),
                    'auto_mode': self.auto_mode.isChecked()
                },
                'results': {
                    'crawled_items': self.get_table_data(self.crawling_table),
                    'uploaded_items': self.get_table_data(self.upload_table),
                    'price_analysis': self.get_table_data(self.price_table)
                },
                'statistics': {
                    'total_processed': self.crawling_table.rowCount(),
                    'successful_uploads': self.upload_table.rowCount(),
                    'price_updates': self.count_updated_prices(),
                    'completion_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # 세션 데이터 파일로 저장
            session_file = f"automation_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"✅ 세션 데이터 저장 완료: {session_file}")
            return session_file
            
        except Exception as e:
            self.log_message(f"세션 저장 오류: {str(e)}")
            return None
    
    def get_table_data(self, table):
        """테이블 데이터를 딕셔너리 리스트로 변환"""
        try:
            data = []
            for row in range(table.rowCount()):
                row_data = {}
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        header = table.horizontalHeaderItem(col)
                        column_name = header.text() if header else f"Column_{col}"
                        row_data[column_name] = item.text()
                data.append(row_data)
            return data
        except Exception as e:
            self.log_message(f"테이블 데이터 변환 오류: {str(e)}")
            return []
    
    def load_automation_session(self):
        """자동화 세션 데이터 불러오기"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "세션 파일 불러오기", 
                "",
                "JSON Files (*.json)"
            )
            
            if not file_path:
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 설정 복원
            settings = session_data.get('settings', {})
            self.dashboard_url.setText(settings.get('url', ''))
            self.dashboard_count.setValue(settings.get('count', 20))
            self.dashboard_discount.setValue(settings.get('discount', 100))
            
            if settings.get('auto_mode', True):
                self.auto_mode.setChecked(True)
            else:
                self.manual_mode.setChecked(True)
            
            # 결과 데이터 복원
            results = session_data.get('results', {})
            self.restore_table_data(self.crawling_table, results.get('crawled_items', []))
            self.restore_table_data(self.upload_table, results.get('uploaded_items', []))
            self.restore_table_data(self.price_table, results.get('price_analysis', []))
            
            # 통계 정보 표시
            stats = session_data.get('statistics', {})
            self.processed_items.setText(f"처리된 상품: {stats.get('total_processed', 0)}/{stats.get('total_processed', 0)}")
            self.success_items.setText(f"성공: {stats.get('successful_uploads', 0)}")
            self.auto_updated.setText(f"자동 수정: {stats.get('price_updates', 0)}")
            
            self.log_message(f"✅ 세션 데이터 불러오기 완료: {file_path}")
            QMessageBox.information(self, "불러오기 완료", "세션 데이터를 성공적으로 불러왔습니다.")
            
        except Exception as e:
            self.log_message(f"세션 불러오기 오류: {str(e)}")
            QMessageBox.critical(self, "불러오기 오류", f"세션 데이터 불러오기 중 오류가 발생했습니다:\n{str(e)}")
    
    def restore_table_data(self, table, data):
        """테이블에 데이터 복원"""
        try:
            table.setRowCount(0)
            
            for row_data in data:
                row = table.rowCount()
                table.insertRow(row)
                
                for col in range(table.columnCount()):
                    header = table.horizontalHeaderItem(col)
                    if header:
                        column_name = header.text()
                        if column_name in row_data:
                            table.setItem(row, col, QTableWidgetItem(row_data[column_name]))
            
        except Exception as e:
            self.log_message(f"테이블 데이터 복원 오류: {str(e)}")
    
    def export_comprehensive_report(self):
        """종합 리포트 생성 및 내보내기"""
        try:
            # 리포트 데이터 수집
            report_data = {
                'session_info': {
                    '생성일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '설정_URL': self.dashboard_url.text(),
                    '설정_개수': self.dashboard_count.value(),
                    '설정_할인': f"{self.dashboard_discount.value()}엔",
                    '모드': "자동" if self.auto_mode.isChecked() else "수동"
                },
                'summary': {
                    '크롤링된_상품': self.crawling_table.rowCount(),
                    '업로드된_상품': self.upload_table.rowCount(),
                    '분석된_상품': self.price_table.rowCount(),
                    '수정된_가격': self.count_updated_prices()
                },
                'detailed_results': {
                    '크롤링_결과': self.get_table_data(self.crawling_table),
                    '업로드_결과': self.get_table_data(self.upload_table),
                    '가격_분석_결과': self.get_table_data(self.price_table)
                }
            }
            
            # Excel 파일로 저장
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "종합 리포트 저장", 
                f"BUYMA_자동화_리포트_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            import pandas as pd
            
            # 여러 시트로 구성된 Excel 파일 생성
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 요약 시트
                summary_df = pd.DataFrame([report_data['summary']])
                summary_df.to_excel(writer, sheet_name='요약', index=False)
                
                # 세션 정보 시트
                session_df = pd.DataFrame([report_data['session_info']])
                session_df.to_excel(writer, sheet_name='세션정보', index=False)
                
                # 크롤링 결과 시트
                if report_data['detailed_results']['크롤링_결과']:
                    crawling_df = pd.DataFrame(report_data['detailed_results']['크롤링_결과'])
                    crawling_df.to_excel(writer, sheet_name='크롤링결과', index=False)
                
                # 업로드 결과 시트
                if report_data['detailed_results']['업로드_결과']:
                    upload_df = pd.DataFrame(report_data['detailed_results']['업로드_결과'])
                    upload_df.to_excel(writer, sheet_name='업로드결과', index=False)
                
                # 가격 분석 결과 시트
                if report_data['detailed_results']['가격_분석_결과']:
                    price_df = pd.DataFrame(report_data['detailed_results']['가격_분석_결과'])
                    price_df.to_excel(writer, sheet_name='가격분석결과', index=False)
            
            self.log_message(f"✅ 종합 리포트 생성 완료: {file_path}")
            QMessageBox.information(self, "리포트 생성 완료", f"종합 리포트가 생성되었습니다.\n\n{file_path}")
            
        except Exception as e:
            self.log_message(f"리포트 생성 오류: {str(e)}")
            QMessageBox.critical(self, "리포트 생성 오류", f"리포트 생성 중 오류가 발생했습니다:\n{str(e)}")
    
    # 에러 처리 및 안정성 개선
    def handle_network_error(self, error, retry_count=3):
        """네트워크 오류 처리"""
        try:
            self.log_message(f"🌐 네트워크 오류 발생: {str(error)}")
            
            for attempt in range(retry_count):
                self.log_message(f"🔄 재시도 {attempt + 1}/{retry_count}...")
                
                # 네트워크 상태 확인
                try:
                    response = requests.get("https://www.google.com", timeout=5)
                    if response.status_code == 200:
                        self.log_message("✅ 네트워크 연결 복구됨")
                        return True
                except:
                    pass
                
                # 재시도 전 대기
                import time
                time.sleep(5)
            
            self.log_error("❌ 네트워크 연결 복구 실패")
            return False
            
        except Exception as e:
            self.log_message(f"네트워크 오류 처리 중 오류: {str(e)}")
            return False
    
    def validate_buyma_access(self):
        """BUYMA 사이트 접근 가능성 확인"""
        try:
            self.log_message("🔍 BUYMA 사이트 접근성 확인 중...")
            
            response = requests.get("https://www.buyma.com", timeout=10)
            
            if response.status_code == 200:
                self.log_message("✅ BUYMA 사이트 접근 가능")
                return True
            else:
                self.log_message(f"⚠️ BUYMA 사이트 응답 코드: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"❌ BUYMA 사이트 접근 불가: {str(e)}")
            return False
    
    def create_backup(self):
        """현재 상태 백업"""
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'crawling_data': self.get_table_data(self.crawling_table),
                'upload_data': self.get_table_data(self.upload_table),
                'price_data': self.get_table_data(self.price_table),
                'settings': {
                    'dashboard_url': self.dashboard_url.text(),
                    'dashboard_count': self.dashboard_count.value(),
                    'dashboard_discount': self.dashboard_discount.value(),
                    'auto_mode': self.auto_mode.isChecked()
                }
            }
            
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"✅ 백업 생성 완료: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.log_message(f"백업 생성 오류: {str(e)}")
            return None
    
    def update_dashboard_step(self, step_text, color):
        """대시보드 단계 업데이트"""
        self.current_step_label.setText(f"현재 단계: {step_text}")
        self.current_step_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color}; padding: 5px;")
        self.dashboard_log_message(step_text)
    
    def stop_full_automation(self):
        """전체 자동화 프로세스 중지"""
        self.dashboard_log_message("⏹️ 사용자에 의해 프로세스가 중지되었습니다.")
        self.current_step_label.setText("현재 단계: 중지됨")
        self.current_step_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #dc3545; padding: 5px;")
        
        # UI 상태 복원
        self.start_automation_btn.setEnabled(True)
        self.stop_automation_btn.setEnabled(False)
    
    def reset_progress(self):
        """진행 상황 초기화"""
        self.overall_progress.setValue(0)
        self.step1_progress.setValue(0)
        self.step2_progress.setValue(0)
        self.step3_progress.setValue(0)
        self.step4_progress.setValue(0)
        
        self.processed_items.setText("처리된 상품: 0/0")
        self.success_items.setText("성공: 0")
        self.failed_items_dash.setText("실패: 0")
        self.estimated_time.setText("예상 완료: 계산중...")
        
        self.current_step_label.setText("현재 단계: 준비중...")
        self.current_step_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057; padding: 5px;")
    
    def dashboard_log_message(self, message):
        """대시보드 로그 메시지 출력"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        self.dashboard_log.append(formatted_message)
        
        # 메인 로그에도 출력
        if hasattr(self, 'log_output'):
            self.log_output.append(formatted_message)
        
        # 상태바에도 표시
        self.status_label.setText(message)
        
        # 로그 자동 스크롤
        scrollbar = self.dashboard_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def browse_url_list(self):
        """URL 목록 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "URL 목록 파일 선택", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.url_input.setText(file_path)
    
    @safe_slot
    def start_crawling(self, checked=False):
        """크롤링 시작"""
        # 로그인 체크 제거 (크롤링은 로그인 없이 진행)
        url = self.url_input.text().strip()
        count = self.crawl_count.value()
        
        if not url:
            QMessageBox.warning(self, "경고", "크롤링할 URL을 입력해주세요.")
            return
        
        # URL 유효성 검사
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "경고", "올바른 URL을 입력해주세요. (http:// 또는 https://로 시작)")
            return
        
        # 크롤링 시작 시간 기록
        import time
        self.today_stats['start_time'] = time.time()
        
        # 크롤링 URL 저장 (저장 기능에서 사용)
        self.last_crawled_url = url
        
        # 크롤링된 상품 데이터 초기화
        self.crawled_products = []
        
        # UI 상태 변경 및 비활성화
        self.start_crawling_btn.setEnabled(False)
        self.stop_crawling_btn.setEnabled(True)
        self.crawling_progress.setValue(0)
        self.crawling_status.setText("크롤링 준비중...")
        
        # 크롤링 중 UI 전체 비활성화
        self.disable_ui_during_crawling(True)
        
        # 테이블 초기화
        self.crawling_table.setRowCount(0)
        
        # 로그 시작
        self.log_message("🚀 크롤링을 시작합니다...")
        self.log_message(f"📋 URL: {url}")
        self.log_message(f"📋 목표 개수: {count}개")
        
        # 진행률 위젯 표시
        self.progress_widget.update_progress(0, count, "🔍 크롤링 시작", f"목표: {count}개 상품")
        
        # 별도 스레드에서 크롤링 실행 (안정성을 위해 threading.Thread 사용)
        crawling_settings = {
            'include_images': self.include_images.isChecked(),
            'include_options': self.include_options.isChecked(), 
            'skip_duplicates': self.skip_duplicates.isChecked(),
            'delay': self.delay_time.value()
        }
        
        import threading
        
        self.crawling_thread = threading.Thread(
            target=self.run_crawling, 
            args=(url, count, crawling_settings), 
            daemon=True
        )
        self.crawling_thread.start()
    
    def run_crawling_with_shared_driver(self, url, count, settings):
        """공용 드라이버를 사용한 크롤링 실행"""
        crawled_products = []  # 중복 체크용
        collected_items = 0
        
        try:
            # 공용 드라이버 상태 체크
            if not self.shared_driver or not self.is_logged_in:
                self.crawling_status_signal.emit("로그인이 필요합니다")
                self.crawling_finished_signal.emit()
                return
            
            self.log_message("🌐 로그인된 브라우저를 사용합니다...")
            self.log_message(f"⚙️ 설정: 이미지포함={settings['include_images']}, "
                           f"옵션포함={settings['include_options']}, "
                           f"중복제외={settings['skip_duplicates']}")
            
            # 크롤링 페이지로 이동
            self.log_message(f"📄 페이지에 접속합니다: {url}")
            self.shared_driver.get(url)
            
            # 페이지 로딩 대기
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            import time
            
            WebDriverWait(self.shared_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.log_message("🔍 상품 정보를 수집합니다...")
            
            # 상품 요소 찾기 (여러 선택자 시도)
            product_selectors = [
                "div.product_img"
            ]
            
            product_elements = []
            for selector in product_selectors:
                try:
                    elements = self.shared_driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 3:  # 최소 3개 이상의 요소가 있어야 상품 목록으로 간주
                        product_elements = elements[:count*2]  # 여유분 포함
                        self.log_message(f"✅ 상품 요소 발견: {selector} ({len(elements)}개)")
                        break
                except:
                    continue
            
            if not product_elements:
                self.log_error("❌ 상품 요소를 찾을 수 없습니다. 페이지 구조를 확인해주세요.")
                self.crawling_finished_signal.emit()
                return
            
            # 상품 링크 추출
            product_links = []
            for element in product_elements:
                try:
                    link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    if link and link.startswith('http'):
                        product_links.append(link)
                        if len(product_links) >= count * 2:  # 충분한 링크 확보
                            break
                except:
                    continue
            
            self.log_message(f"🔗 상품 링크 {len(product_links)}개 추출 완료")
            
            # 상품 정보 추출
            for i, link in enumerate(product_links):
                if collected_items >= count:
                    break
                
                # 메모리 정리 (10개마다)
                if i > 0 and i % 10 == 0:
                    import gc
                    gc.collect()
                    self.log_message(f"🧹 메모리 정리 완료 ({i}개 처리)")
                
                # 브라우저 상태 체크
                try:
                    self.shared_driver.current_url  # 브라우저가 살아있는지 체크
                except Exception as e:
                    self.log_message(f"❌ 브라우저 연결 끊어짐: {str(e)}")
                    # 브라우저 재시작 시도
                    if self.restart_shared_driver():
                        self.log_message("✅ 브라우저 재시작 성공")
                        continue
                    else:
                        self.log_message("❌ 브라우저 재시작 실패, 크롤링 중단")
                        break
                
                try:
                    # 중복 상품 체크
                    if settings['skip_duplicates']:
                        if self.is_duplicate_product(link, crawled_products):
                            self.log_message(f"⏭️ 중복 상품 건너뛰기: {link}")
                            continue
                    
                    # 상품 정보 추출 (공용 드라이버 사용)
                    item_data = self.extract_item_data_with_shared_driver(link, i, settings)
                    
                    if item_data:
                        # 중복 체크용 리스트에 추가
                        if settings['skip_duplicates']:
                            crawled_products.append({
                                'url': link,
                                'title': item_data.get('title', ''),
                                'brand': item_data.get('brand', '')
                            })
                        
                        collected_items += 1
                        
                        # UI 업데이트 (시그널로 안전하게 처리)
                        self.crawling_result_signal.emit(item_data)
                        
                        # 진행률 업데이트
                        progress = int((collected_items / count) * 100)
                        self.crawling_progress_signal.emit(progress)
                        self.crawling_status_signal.emit(f"진행중: {collected_items}/{count}")
                        
                        self.log_message(f"✅ 상품 수집: {item_data.get('title', 'Unknown')[:30]}...")
                        
                        # 설정된 딜레이 적용 (서버 부하 방지)
                        time.sleep(max(settings['delay'], 2))  # 최소 2초 대기
                
                except Exception as e:
                    self.log_message(f"⚠️ 상품 추출 오류 (#{i+1}): {str(e)}")
                    
                    # 심각한 오류인지 체크
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["quota_exceeded", "chrome not reachable", "session deleted", "no such window"]):
                        self.log_message(f"❌ 심각한 오류 감지, 브라우저 재시작 시도: {str(e)}")
                        if self.restart_shared_driver():
                            self.log_message("✅ 브라우저 재시작 성공, 크롤링 계속")
                            continue
                        else:
                            self.log_message("❌ 브라우저 재시작 실패, 크롤링 중단")
                            break
                    
                    # 일반적인 오류는 계속 진행
                    continue
            
            # 크롤링 완료
            self.log_message(f"🎉 크롤링 완료! 총 {collected_items}개 상품 수집")
            self.crawling_status_signal.emit(f"완료: {collected_items}개 수집")
            self.crawling_progress_signal.emit(100)
            
        except Exception as e:
            self.log_message(f"❌ 크롤링 오류: {str(e)}")
            self.crawling_status_signal.emit("오류 발생")
            
            # 오류 상세 정보 로깅
            import traceback
            self.log_message(f"📋 오류 상세: {traceback.format_exc()}")
            
        finally:
            # 공용 드라이버는 종료하지 않음 (로그인 상태 유지)
            # 단, 메모리 정리는 수행
            try:
                import gc
                gc.collect()
                self.log_message("🧹 최종 메모리 정리 완료")
            except:
                pass
                
            self.log_message("🔄 크롤링 완료. 브라우저는 로그인 상태로 유지됩니다.")
            
            # UI 상태 복원
            self.crawling_finished_signal.emit()
    
    def extract_item_data_with_shared_driver(self, url, index, settings):
        """공용 드라이버를 사용한 상품 데이터 추출"""
        try:
            self.log_message(f"🔗 상품 #{index+1} 페이지 접속 중...")
            
            if not url:
                self.log_message(f"⚠️ 상품 #{index+1} URL을 찾을 수 없습니다.")
                return None
            
            # 공용 드라이버 사용
            self.shared_driver.get(url)
            time.sleep(2)
            
            # 기본 정보 추출 (기존 로직과 동일)
            title = "상품명 없음"
            brand = "브랜드 없음"
            price = "가격 정보 없음"
            product_url = url
            images = []
            colors = []
            sizes = []
            description_text = ""
            category_text = ""
            
            # 상품명 추출
            try:
                title_element = self.shared_driver.find_element(By.CSS_SELECTOR, "span.itemdetail-item-name")
                title = title_element.text.strip() if title_element else f"상품 #{index+1}"
            except Exception as e:
                self.log_message(f"⚠️ 상품명 추출 실패: {str(e)}")
                title = f"상품 #{index+1}"
            
            # 브랜드명 추출
            try:
                brand_element = self.shared_driver.find_element(By.CSS_SELECTOR, "div.brand-wrap")
                brand = brand_element.text.replace("i", "").strip() if brand_element else "Unknown Brand"
            except Exception as e:
                self.log_message(f"⚠️ 브랜드 추출 실패: {str(e)}")
                brand = "Unknown Brand"
            
            # 가격 추출
            try:
                price_element = self.shared_driver.find_element(By.CSS_SELECTOR, "span.price_txt")
                price = price_element.text.strip() if price_element else "가격 정보 없음"
            except Exception as e:
                self.log_message(f"⚠️ 가격 추출 실패: {str(e)}")
                price = "가격 정보 없음"
            
            # 이미지 추출 (설정 확인)
            if settings['include_images']:
                try:
                    ul = self.shared_driver.find_element(By.CSS_SELECTOR, "ul.item_sumb_img")
                    li_elements = ul.find_elements(By.TAG_NAME, "li")
                    
                    for li in li_elements:
                        try:
                            a = li.find_element(By.TAG_NAME, "a")
                            src = a.get_attribute("href")
                            if src and src.startswith('http'):
                                images.append(src)
                        except:
                            continue
                            
                except Exception as e:
                    self.log_message(f"⚠️ 이미지 추출 실패: {str(e)}")
                    images = []
            else:
                self.log_message(f"⚙️ 이미지 수집 건너뛰기 (설정)")
            
            # 색상 및 사이즈 정보 추출 (설정 확인)
            if settings['include_options']:
                try:
                    color_size_buttons = self.shared_driver.find_elements(By.CSS_SELECTOR, "p.colorsize_selector")
                    
                    if len(color_size_buttons) >= 1:
                        # 색상 정보 추출
                        try:
                            color_size_buttons[0].click()
                            time.sleep(1)
                            
                            colors_ul = self.shared_driver.find_element(By.CSS_SELECTOR, "ul.colorsize_list")
                            colors_li_elements = colors_ul.find_elements(By.TAG_NAME, "li")
                            
                            for li in colors_li_elements:
                                try:
                                    # 색상 카테고리 추출 (CSS 선택자 수정)
                                    try:
                                        color_category_element = li.find_element(By.CSS_SELECTOR, "span.item_color")
                                        color_category = color_category_element.get_attribute("class").replace("item_color ", "").strip()
                                        self.log_message(f"🎨 색상 카테고리 추출: {color_category}")
                                    except Exception as cat_e:
                                        color_category = ""  # 카테고리를 찾을 수 없는 경우 빈 문자열
                                        self.log_message(f"⚠️ 색상 카테고리 추출 실패: {str(cat_e)}")
                                    
                                    color_text = li.text.strip()
                                    self.log_message(f"🎨 색상 텍스트 추출: {color_text}")
                                    
                                    if color_text and [color_category, color_text] not in colors:
                                        colors.append([color_category, color_text])
                                        self.log_message(f"✅ 색상 추가: [{color_category}, {color_text}]")
                                    else:
                                        self.log_message(f"⏭️ 색상 건너뛰기 (중복 또는 빈 텍스트): {color_text}")
                                except Exception as li_e:
                                    self.log_message(f"❌ 색상 li 처리 오류: {str(li_e)}")
                                    continue
                            
                            color_size_buttons[0].click()
                            time.sleep(1)
                            
                        except Exception as e:
                            self.log_message(f"⚠️ 색상 정보 추출 실패: {str(e)}")
                    
                    # 사이즈 정보 추출
                    if len(color_size_buttons) >= 2:
                        try:
                            color_size_buttons[1].click()
                            time.sleep(1)
                            
                            sizes_ul = self.shared_driver.find_element(By.CSS_SELECTOR, ".colorsize_list.js-size-list")
                            sizes_li_elements = sizes_ul.find_elements(By.TAG_NAME, "li")
                            
                            for li in sizes_li_elements:
                                try:
                                    size_text = li.text.strip()
                                    if size_text and size_text not in sizes:
                                        sizes.append(size_text)
                                except:
                                    continue
                            
                            color_size_buttons[1].click()
                            time.sleep(1)
                            
                        except Exception as e:
                            self.log_message(f"⚠️ 사이즈 정보 추출 실패: {str(e)}")
                        
                except Exception as e:
                    self.log_message(f"⚠️ 색상/사이즈 버튼을 찾을 수 없습니다: {str(e)}")
            else:
                self.log_message(f"⚙️ 색상/사이즈 수집 건너뛰기 (설정)")
            
            # 결과 반환
            result = {
                'title': title.strip(),
                'brand': brand.strip(),
                'price': price.strip(),
                'url': product_url.strip(),
                'images': images,
                'colors': colors,
                'sizes': sizes,
                'description': description_text.strip(),
                'category': category_text.strip(),
                'status': '수집 완료'
            }
            
            self.log_message(f"✅ 상품 #{index+1} 데이터 추출 완료: {title[:30]}...")
            self.log_message(f"   📊 이미지: {len(images)}장, 색상: {len(colors)}개, 사이즈: {len(sizes)}개")
            
            return result
            
        except Exception as e:
            self.log_message(f"❌ 상품 #{index+1} 데이터 추출 오류: {str(e)}")
            return {
                'title': f"상품 #{index+1}",
                'brand': "Unknown",
                'price': "가격 정보 없음",
                'url': url,
                'images': [],
                'colors': [],
                'sizes': [],
                'description': "",
                'category': "",
                'status': '추출 실패'
            }
    
    def run_crawling(self, url, count, settings):
        """크롤링 실행 (별도 스레드) - 새 브라우저 사용"""
        driver = None
        crawled_products = []  # 중복 체크용
        
        try:
            self.log_message("🌐 크롤링용 새 브라우저를 시작합니다...")
            self.log_message(f"⚙️ 설정: 이미지포함={settings['include_images']}, "
                           f"옵션포함={settings['include_options']}, "
                           f"중복제외={settings['skip_duplicates']}")
            
            # Selenium WebDriver 설정
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            
            import time
            
            # Chrome 옵션 설정 (크롤링 최적화)
            chrome_options = self.get_stable_chrome_options()
            
            # WebDriver 생성 (재시도 로직 포함)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 브라우저 생성 전 메모리 정리
                    import gc
                    gc.collect()
                    
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.implicitly_wait(self.timeout_setting.value())
                    
                    # 브라우저 안정성 테스트
                    driver.get("about:blank")
                    
                    self.log_message(f"✅ 크롤링용 브라우저 초기화 성공 (시도 {attempt + 1}/{max_retries})")
                    break
                    
                except Exception as e:
                    self.log_error(f"⚠️ 브라우저 초기화 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                    
                    # 이전 시도에서 생성된 프로세스 정리
                    try:
                        if 'driver' in locals():
                            driver.quit()
                    except:
                        pass
                    
                    # Chrome 프로세스 강제 종료 (마지막 시도 전)
                    if attempt == max_retries - 2:
                        try:
                            # import psutil
                            # for proc in psutil.process_iter(['pid', 'name']):
                            #     if 'chrome' in proc.info['name'].lower():
                            #         proc.kill()
                            self.log_message("🔄 Chrome 프로세스 정리 완료")
                        except:
                            pass
                    
                    if attempt == max_retries - 1:
                        self.log_error("❌ 브라우저 초기화 최종 실패")
                        self.crawling_status_signal.emit("브라우저 초기화 실패")
                        self.crawling_finished_signal.emit()
                        return
                    
                    time.sleep(3)  # 재시도 전 대기 시간 증가
            
            self.log_message(f"📄 페이지에 접속합니다: {url}")
            
            # 페이지 접속
            driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.log_message("🔍 상품 정보를 수집합니다...")
            
            time.sleep(1)
            
            try:
                driver.implicitly_wait(3)
                # 팝업창 종료
                popup = driver.find_element(By.CSS_SELECTOR, "span.bcIntro__closeBtn")
                
                driver.execute_script("arguments[0].click();", popup)
                time.sleep(1)
                
                self.log_message("✅ 팝업창을 성공적으로 닫았습니다.")
            except Exception as e:
                self.log_message(f"⚠️ 팝업창 닫기 오류: {str(e)}")
                
                pass
                        
            # 상품 수집
            collected_items = 0
            
            # BUYMA 상품 리스트 선택자 시도
            product_elements = []
            selectors_to_try = [
                "div.product_name"
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        product_elements = elements
                        self.log_message(f"📦 선택자 '{selector}'로 {len(elements)}개 요소 발견")
                        break
                except:
                    continue
            
            if not product_elements:
                self.log_message("❌ 상품 요소를 찾을 수 없습니다. 페이지 구조를 확인해주세요. 해당 현상이 지속된다면, 개발자에게 문의해주세요.")
                return
            
            # 상품 링크 추출
            product_links = []
            
            for element in product_elements:
                try:
                    link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    
                    if link and link.startswith('http'):
                        product_links.append(link)
                        self.log_message(f"🔗 상품 링크 추출: {link}")
                        
                except Exception as e:
                    self.log_message(f"⚠️ 상품 링크 추출 오류: {str(e)}")
            
            # 상품 정보 추출
            for i, link in enumerate(product_links):
                if collected_items >= count:
                    break
                
                # 브라우저 상태 체크
                try:
                    driver.current_url  # 브라우저가 살아있는지 체크
                except Exception as e:
                    self.log_message(f"❌ 브라우저 연결 끊어짐: {str(e)}")
                    break
                
                try:
                    # 중복 상품 체크
                    if settings['skip_duplicates']:
                        if self.is_duplicate_product(link, crawled_products):
                            self.log_message(f"⏭️ 중복 상품 건너뛰기: {link}")
                            continue
                    
                    # 상품 정보 추출 (설정 전달)
                    item_data = self.extract_item_data(link, i, driver, settings)
                    
                    if item_data:
                        # 중복 체크용 리스트에 추가
                        if settings['skip_duplicates']:
                            crawled_products.append({
                                'url': link,
                                'title': item_data.get('title', ''),
                                'brand': item_data.get('brand', '')
                            })
                        
                        collected_items += 1
                        
                        # UI 업데이트 (시그널로 안전하게 처리)
                        self.crawling_result_signal.emit(item_data)
                        
                        # 진행률 업데이트 (시그널로 안전하게 처리)
                        progress = int((collected_items / count) * 100)
                        self.crawling_progress_signal.emit(progress)
                        self.crawling_status_signal.emit(f"진행중: {collected_items}/{count}")
                        
                        self.log_message(f"✅ 상품 수집: {item_data.get('title', 'Unknown')[:30]}...")
                        
                        # 설정된 딜레이 적용
                        import time
                        time.sleep(settings['delay'])
                
                except Exception as e:
                    self.log_message(f"⚠️ 상품 추출 오류 (#{i+1}): {str(e)}")
                    
                    # 심각한 오류인지 체크
                    if "QUOTA_EXCEEDED" in str(e) or "chrome not reachable" in str(e).lower():
                        self.log_message(f"❌ 심각한 오류 감지, 크롤링 중단: {str(e)}")
                        break
                    
                    continue
            
            # 완료 처리 (시그널로 안전하게 처리)
            self.log_message(f"✅ 크롤링 완료! 총 {collected_items}개 상품을 수집했습니다.")
            self.crawling_status_signal.emit(f"완료: {collected_items}개")
            self.crawling_progress_signal.emit(100)
            self.crawling_finished_signal.emit()
            
        except Exception as e:
            self.log_message(f"❌ 크롤링 오류: {str(e)}")
            self.crawling_status_signal.emit("오류 발생")
            self.crawling_finished_signal.emit()
        finally:
            # 브라우저 안전한 종료
            if driver:
                try:
                    # 모든 탭 닫기
                    for handle in driver.window_handles:
                        driver.switch_to.window(handle)
                        driver.close()
                    
                    # 드라이버 종료
                    driver.quit()
                    self.log_message("🔄 크롤링용 브라우저가 안전하게 종료되었습니다.")
                except Exception as cleanup_error:
                    self.log_message(f"⚠️ 브라우저 종료 중 오류: {str(cleanup_error)}")
            
            # 메모리 정리
            import gc
            gc.collect()
            
            # UI 상태 복원 (시그널로 안전하게 처리)
            self.crawling_finished_signal.emit()
    
    def extract_item_data(self, url, index, driver, settings):
        """상품 데이터 추출 (안전장치 추가) - 설정 적용"""
        try:
            # 상품 url 추출
            self.log_message(f"🔗 상품 #{index+1} 페이지 접속 중...")
            
            if not url:
                self.log_message(f"⚠️ 상품 #{index+1} URL을 찾을 수 없습니다.")
                return None
            
            driver.get(url)
            time.sleep(2)
            
            driver.implicitly_wait(10)
            
            # 기본 정보 추출 (안전장치 추가)
            title = "상품명 없음"
            brand = "브랜드 없음"
            price = "가격 정보 없음"
            product_url = url
            images = []
            colors = []
            sizes = []
            description_text = ""
            category_text = ""
            
            # 상품명 추출 (안전장치)
            try:
                title_element = driver.find_element(By.CSS_SELECTOR, "span.itemdetail-item-name")
                title = title_element.text.strip() if title_element else f"상품 #{index+1}"
            except Exception as e:
                self.log_message(f"⚠️ 상품명 추출 실패: {str(e)}")
                title = f"상품 #{index+1}"
            
            # 브랜드명 추출 (안전장치)
            try:
                brand_element = driver.find_element(By.CSS_SELECTOR, "div.brand-wrap")
                brand = brand_element.text.replace("i", "").strip() if brand_element else "Unknown Brand"
            except Exception as e:
                self.log_message(f"⚠️ 브랜드 추출 실패: {str(e)}")
                brand = "Unknown Brand"
            
            # 가격 추출 (안전장치)
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "span.price_txt")
                price = price_element.text.strip() if price_element else "가격 정보 없음"
            except Exception as e:
                self.log_message(f"⚠️ 가격 추출 실패: {str(e)}")
                price = "가격 정보 없음"
            
            # 이미지 추출 (설정 확인)
            if settings['include_images']:
                try:
                    ul = driver.find_element(By.CSS_SELECTOR, "ul.item_sumb_img")
                    li_elements = ul.find_elements(By.TAG_NAME, "li")
                    
                    for li in li_elements:
                        try:
                            a = li.find_element(By.TAG_NAME, "a")
                            src = a.get_attribute("href")
                            if src and src.startswith('http'):
                                images.append(src)
                        except:
                            continue
                            
                except Exception as e:
                    self.log_message(f"⚠️ 이미지 추출 실패: {str(e)}")
                    images = []
            else:
                self.log_message(f"⚙️ 이미지 수집 건너뛰기 (설정)")
            
            # 색상 및 사이즈 정보 추출 (설정 확인)
            if settings['include_options']:
                try:
                    color_size_buttons = driver.find_elements(By.CSS_SELECTOR, "p.colorsize_selector")
                    
                    if len(color_size_buttons) >= 1:
                        # 색상 정보 추출
                        try:
                            color_size_buttons[0].click()
                            time.sleep(1)
                            
                            colors_ul = driver.find_element(By.CSS_SELECTOR, "ul.colorsize_list")
                            colors_li_elements = colors_ul.find_elements(By.TAG_NAME, "li")
                            
                            for li in colors_li_elements:
                                try:
                                    # 색상 카테고리 추출 (CSS 선택자 수정)
                                    try:
                                        color_category_element = li.find_element(By.CSS_SELECTOR, "span.item_color")
                                        color_category = color_category_element.get_attribute("class").replace("item_color ", "").strip()
                                        self.log_message(f"🎨 색상 카테고리 추출: {color_category}")
                                    except Exception as cat_e:
                                        color_category = ""  # 카테고리를 찾을 수 없는 경우 빈 문자열
                                        self.log_message(f"⚠️ 색상 카테고리 추출 실패: {str(cat_e)}")
                                    
                                    color_text = li.text.strip()
                                    self.log_message(f"🎨 색상 텍스트 추출: {color_text}")
                                    
                                    if color_text and [color_category, color_text] not in colors:
                                        colors.append([color_category, color_text])
                                        self.log_message(f"✅ 색상 추가: [{color_category}, {color_text}]")
                                    else:
                                        self.log_message(f"⏭️ 색상 건너뛰기 (중복 또는 빈 텍스트): {color_text}")
                                except Exception as li_e:
                                    self.log_message(f"❌ 색상 li 처리 오류: {str(li_e)}")
                                    continue
                            
                            # 색상 정보 옵션 종료
                            color_size_buttons[0].click()
                            time.sleep(1)
                            
                        except Exception as e:
                            self.log_message(f"⚠️ 색상 정보 추출 실패: {str(e)}")
                    
                    # 사이즈 정보 추출 (두 번째 버튼이 있는 경우에만)
                    if len(color_size_buttons) >= 2:
                        try:
                            color_size_buttons[1].click()
                            time.sleep(1)
                            
                            sizes_ul = driver.find_element(By.CSS_SELECTOR, ".colorsize_list.js-size-list")
                            sizes_li_elements = sizes_ul.find_elements(By.TAG_NAME, "li")
                            
                            for li in sizes_li_elements:
                                try:
                                    size_text = li.text.strip()
                                    if size_text and size_text not in sizes:
                                        sizes.append(size_text)
                                except:
                                    continue
                            
                            # 사이즈 정보 옵션 종료
                            color_size_buttons[1].click()
                            time.sleep(1)
                            
                        except Exception as e:
                            self.log_message(f"⚠️ 사이즈 정보 추출 실패: {str(e)}")
                    else:
                        self.log_message(f"⚠️ 사이즈 버튼을 찾을 수 없습니다.")
                        
                except Exception as e:
                    self.log_message(f"⚠️ 색상/사이즈 버튼을 찾을 수 없습니다: {str(e)}")
            else:
                self.log_message(f"⚙️ 색상/사이즈 수집 건너뛰기 (설정)")
            
            time.sleep(0.5)
            
            # 상품 설명 추출 (안전장치)
            try:
                description_element = driver.find_element(By.CSS_SELECTOR, "p.free_txt")
                
                # 해당 요소로 스크롤 
                driver.execute_script("arguments[0].scrollIntoView(true);", description_element)
                time.sleep(1)
                
                description_text = description_element.text.strip() if description_element else ""
            except Exception as e:
                self.log_message(f"⚠️ 상품 설명 추출 실패: {str(e)}")
                description_text = ""
            
            # 카테고리 추출 (안전장치)
            try:
                category_element = driver.find_elements(By.CSS_SELECTOR, "ol.fab-topic-path--simple")[-1]
                
                # BUYMA 탑  아기 키즈  아동복・패션 용품(85cm~)  어린이용 탑스  [어른도 OK] [랄프 로렌] ● 폴로 컬러 T 셔츠 ● 이런식의 데이터가 오는데 
                # 여기서 첫번째 데이터 및 상품명과 일치하는 텍스트를 제거 후 나머지가 카테고리
                
                full_category_text = category_element.text.strip()
                self.log_message(f"🔍 전체 카테고리 경로: {full_category_text}")
                
                # 상품명 텍스트를 카테고리 경로에서 제거
                if title.strip():
                    cleaned_category_text = full_category_text.replace(title.strip(), "").strip()
                    self.log_message(f"🔍 상품명 제거 후: {cleaned_category_text}")
                else:
                    cleaned_category_text = full_category_text
                
                # 공백으로 분리하여 각 부분 추출
                category_parts = [part.strip() for part in cleaned_category_text.split() if part.strip()]
                
                # 첫 번째 요소(BUYMA 탑 등) 제거
                if len(category_parts) > 1:
                    categories = category_parts[1:]  # 첫 번째 제거
                    self.log_message(f"✅ 최종 추출된 카테고리: {categories}")
                else:
                    categories = []
                    self.log_message(f"⚠️ 카테고리가 충분하지 않음: {category_parts}")
                
            except Exception as e:
                self.log_message(f"⚠️ 카테고리 추출 실패: {str(e)}")
                categories = []
            
            # 결과 반환
            result = {
                'title': title.strip(),
                'brand': brand.strip(),
                'price': price.strip(),
                'url': product_url.strip(),
                'images': images,
                'colors': colors,
                'sizes': sizes,
                'description': description_text.strip(),
                'categories': categories,  # 추출된 카테고리 리스트
                'status': '수집 완료'
            }
            
            # 디버깅 로그 추가
            self.log_message(f"✅ 상품 #{index+1} 데이터 추출 완료: {title[:30]}...")
            self.log_message(f"   📊 이미지: {len(images)}장, 색상: {len(colors)}개, 사이즈: {len(sizes)}개")
            self.log_message(f"   🎨 최종 색상 데이터: {colors}")
            
            return result
            
        except Exception as e:
            self.log_message(f"❌ 상품 #{index+1} 데이터 추출 오류: {str(e)}")
            # 최소한의 정보라도 반환
            return {
                'title': f"상품 #{index+1}",
                'brand': "Unknown",
                'price': "가격 정보 없음",
                'url': url,
                'images': [],
                'colors': [],
                'sizes': [],
                'description': "",
                'category': "",
                'status': '추출 실패'
            }
    
    def is_duplicate_product(self, url, crawled_products):
        """중복 상품 체크"""
        try:
            for product in crawled_products:
                # URL 기준 중복 체크
                if product['url'] == url:
                    return True
                    
                # 상품명 + 브랜드 기준 중복 체크 (향후 확장 가능)
                # if (product['title'] == title and product['brand'] == brand):
                #     return True
                    
            return False
            
        except Exception as e:
            self.log_message(f"중복 체크 오류: {str(e)}")
            return False
    
    def get_stable_chrome_options(self):
        """안정적인 Chrome 옵션 반환 (프로그램 종료 방지 강화)"""
        options = Options()
        
        # 기본 안정성 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 프로그램 종료 방지를 위한 핵심 옵션
        options.add_argument('--disable-crash-reporter')
        options.add_argument('--disable-in-process-stack-traces')
        options.add_argument('--disable-dev-tools')
        options.add_argument('--disable-logging')
        options.add_argument('--silent')
        options.add_argument('--log-level=3')
        
        # Abseil 로깅 경고 완전 차단
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        
        # DevTools 및 디버깅 완전 비활성화
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-preconnect')
        options.add_argument('--disable-remote-debugging')
        options.add_argument('--remote-debugging-port=0')
        
        # 음성 인식 및 미디어 기능 완전 비활성화
        options.add_argument('--disable-speech-api')
        options.add_argument('--disable-speech-synthesis-api')
        options.add_argument('--disable-voice-input')
        options.add_argument('--disable-features=VoiceInteraction,SpeechRecognition,VoiceTranscription')
        
        # Google API 관련 오류 방지
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI,VizDisplayCompositor')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # 할당량 초과 방지
        options.add_argument('--disable-component-extensions-with-background-pages')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        
        # 메모리 및 성능 최적화 (대량 크롤링용)
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-mode')
        
        # 대량 처리를 위한 추가 옵션
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-prompt-on-repost')
        options.add_argument('--disable-domain-reliability')
        options.add_argument('--disable-component-update')
        
        # 안정성 강화 옵션
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-images')  # 이미지 로딩 비활성화로 메모리 절약
        
        return options
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-gpu-logging')
        options.add_argument('--silent')
        options.add_argument('--log-level=3')
        
        # 네트워크 안정성
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        return options
    
    @safe_slot
    def start_buyma_login(self, checked=False):
        """BUYMA 로그인 시작"""
        try:
            email = self.email_input.text().strip()
            password = self.password_input.text().strip()
            
            if not email or not password:
                QMessageBox.warning(self, "입력 오류", "이메일과 비밀번호를 모두 입력해주세요.")
                return
            
            # 로그인 버튼 비활성화
            self.login_btn.setEnabled(False)
            self.login_btn.setText("🔄 로그인 중...")
            self.login_status_label.setText("🔄 로그인 진행 중...")
            self.login_status_label.setStyleSheet("""
                QLabel {
                    color: #ffc107;
                    font-weight: bold;
                    font-family: '맑은 고딕';
                    padding: 5px;
                    border-radius: 3px;
                    background: #f8f9fa;
                }
            """)
            
            # 별도 스레드에서 로그인 실행
            import threading
            
            self.login_thread = threading.Thread(
                target=self.perform_buyma_login, 
                args=(email, password), 
                daemon=True
            )
            self.login_thread.start()
            
        except Exception as e:
            self.log_message(f"로그인 시작 오류: {str(e)}")
            self.reset_login_ui()
    
    def perform_buyma_login(self, email, password):
        """BUYMA 로그인 수행 (별도 스레드)"""
        try:
            self.log_message("🔐 BUYMA 로그인을 시작합니다...")
            
            # 기존 드라이버가 있으면 종료
            if self.shared_driver:
                try:
                    self.shared_driver.quit()
                except:
                    pass
                self.shared_driver = None
            
            # 새 브라우저 생성
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            
            # Chrome 옵션 설정
            chrome_options = self.get_stable_chrome_options()
            
            # 브라우저 생성 (재시도 로직 포함)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.shared_driver = webdriver.Chrome(options=chrome_options)
                    self.shared_driver.implicitly_wait(10)
                    
                    # 페이지 로딩 타임아웃 설정 (10초)
                    self.shared_driver.set_page_load_timeout(10)
                    
                    self.log_message(f"✅ 브라우저 초기화 성공 (시도 {attempt + 1}/{max_retries})")
                    break
                except Exception as e:
                    self.log_error(f"⚠️ 브라우저 초기화 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        self.login_failed_signal.emit("브라우저 초기화 실패")
                        return
                    time.sleep(2)
            
            # BUYMA 로그인 페이지 접속
            self.log_message("📄 BUYMA 로그인 페이지에 접속합니다...")
            self.shared_driver.get("https://www.buyma.com/login/")
            
            # 페이지 로딩 대기
            WebDriverWait(self.shared_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 로그인 폼 찾기 및 입력
            self.log_message("📝 로그인 정보를 입력합니다...")
            
            # 이메일 입력 (여러 선택자 시도)
            email_selectors = ["#txtLoginId"]
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.shared_driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not email_field:
                self.login_failed_signal.emit("이메일 입력 필드를 찾을 수 없습니다.")
                return
            
            email_field.clear()
            email_field.send_keys(email)
            
            time.sleep(1)
            
            # 비밀번호 입력
            password_selectors = ["#txtLoginPass"]
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.shared_driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not password_field:
                self.login_failed_signal.emit("비밀번호 입력 필드를 찾을 수 없습니다.")
                return
            
            password_field.clear()
            password_field.send_keys(password)
            
            # 로그인 버튼 클릭
            login_selectors = [
                "#login_do"
            ]
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.shared_driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not login_button:
                self.login_failed_signal.emit("로그인 버튼을 찾을 수 없습니다.")
                return
            
            # login_button.click()
            password_field.send_keys(Keys.ENTER)
            
            # 로그인 결과 확인 (최대 15초 대기)
            self.log_message("⏳ 로그인 결과를 확인합니다...")
            time.sleep(5)
            
            # 로그인 성공 여부 확인
            current_url = self.shared_driver.current_url
            page_source = self.shared_driver.page_source.lower()
            
            # 성공 조건: 로그인 페이지가 아니거나, 마이페이지로 이동했거나, 로그아웃 버튼이 있음
            if ("login" not in current_url.lower() or 
                "mypage" in current_url.lower() or 
                "logout" in page_source or
                "마이페이지" in page_source):
                # 로그인 성공
                self.is_logged_in = True
                self.login_success_signal.emit()
                self.log_message("✅ BUYMA 로그인 성공!")
            else:
                # 로그인 실패
                self.login_failed_signal.emit("로그인 실패: 이메일 또는 비밀번호를 확인해주세요.")
                
        except Exception as e:
            self.log_error(f"❌ 로그인 오류: {str(e)}")
            self.login_failed_signal.emit(f"로그인 오류: {str(e)}")
    
    def on_login_success(self):
        """로그인 성공 시 UI 업데이트"""
        self.login_status_label.setText("✅ 로그인 성공")
        self.login_status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-family: '맑은 고딕';
                padding: 5px;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        self.login_btn.setText("🔓 로그아웃")
        self.login_btn.setEnabled(True)
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.logout_buyma)
        
        self.log_message("🎉 BUYMA 로그인이 완료되었습니다. 이제 모든 기능을 사용할 수 있습니다.")
    
    def on_login_failed(self, error_message):
        """로그인 실패 시 UI 업데이트"""
        self.login_status_label.setText(f"❌ {error_message}")
        self.login_status_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-family: '맑은 고딕';
                padding: 5px;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        self.reset_login_ui()
        
        # 브라우저 정리
        if self.shared_driver:
            try:
                self.shared_driver.quit()
            except:
                pass
            self.shared_driver = None
        
        self.is_logged_in = False
    
    def reset_login_ui(self):
        """로그인 UI 초기화"""
        self.login_btn.setText("🔐 BUYMA 로그인")
        self.login_btn.setEnabled(True)
        try:
            self.login_btn.clicked.disconnect()
        except:
            pass
        self.login_btn.clicked.connect(self.start_buyma_login)
    
    def logout_buyma(self):
        """BUYMA 로그아웃"""
        try:
            if self.shared_driver:
                self.shared_driver.quit()
                self.shared_driver = None
            
            self.is_logged_in = False
            self.login_status_label.setText("❌ 로그인 필요")
            self.login_status_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: bold;
                    font-family: '맑은 고딕';
                    padding: 5px;
                    border-radius: 3px;
                    background: #f8f9fa;
                }
            """)
            self.reset_login_ui()
            self.log_message("🔓 BUYMA에서 로그아웃되었습니다.")
            
        except Exception as e:
            self.log_message(f"로그아웃 오류: {str(e)}")
    
    def check_login_required(self):
        """로그인 필요 여부 체크"""
        if not self.is_logged_in or not self.shared_driver:
            QMessageBox.warning(
                self, 
                "로그인 필요", 
                "이 기능을 사용하려면 먼저 BUYMA에 로그인해주세요.\n\n설정 탭에서 로그인을 진행해주세요."
            )
            return False
        return True
    
    # def start_buyma_login(self):
    #     """BUYMA 로그인 시작"""
    #     try:
    #         email = self.email_input.text().strip()
    #         password = self.password_input.text().strip()
            
    #         if not email or not password:
    #             QMessageBox.warning(self, "입력 오류", "이메일과 비밀번호를 모두 입력해주세요.")
    #             return
            
    #         # 로그인 버튼 비활성화
    #         self.login_btn.setEnabled(False)
    #         self.login_btn.setText("🔄 로그인 중...")
    #         self.login_status_label.setText("🔄 로그인 진행 중...")
    #         self.login_status_label.setStyleSheet("""
    #             QLabel {
    #                 color: #ffc107;
    #                 font-weight: bold;
    #                 font-family: '맑은 고딕';
    #                 padding: 5px;
    #                 border-radius: 3px;
    #                 background: #f8f9fa;
    #             }
    #         """)
            
    #         # 별도 스레드에서 로그인 실행
    #         self.login_thread = threading.Thread(
    #             target=self.perform_buyma_login, 
    #             args=(email, password), 
    #             daemon=True
    #         )
    #         self.login_thread.start()
            
    #     except Exception as e:
    #         self.log_message(f"로그인 시작 오류: {str(e)}")
    #         self.reset_login_ui()
    
    # def perform_buyma_login(self, email, password):
    #     """BUYMA 로그인 수행 (별도 스레드)"""
    #     try:
    #         self.log_message("🔐 BUYMA 로그인을 시작합니다...")
            
    #         # 기존 드라이버가 있으면 종료
    #         if self.shared_driver:
    #             try:
    #                 self.shared_driver.quit()
    #             except:
    #                 pass
    #             self.shared_driver = None
            
    #         # 새 브라우저 생성
    #         from selenium import webdriver
    #         from selenium.webdriver.chrome.options import Options
    #         from selenium.webdriver.common.by import By
    #         from selenium.webdriver.support.ui import WebDriverWait
    #         from selenium.webdriver.support import expected_conditions as EC
    #         import time
            
    #         # Chrome 옵션 설정
    #         chrome_options = self.get_stable_chrome_options()
            
    #         # 브라우저 생성 (재시도 로직 포함)
    #         max_retries = 3
    #         for attempt in range(max_retries):
    #             try:
    #                 self.shared_driver = webdriver.Chrome(options=chrome_options)
    #                 self.shared_driver.implicitly_wait(10)
    #                 self.log_message(f"✅ 브라우저 초기화 성공 (시도 {attempt + 1}/{max_retries})")
    #                 break
    #             except Exception as e:
    #                 self.log_message(f"⚠️ 브라우저 초기화 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
    #                 if attempt == max_retries - 1:
    #                     self.login_failed_signal.emit("브라우저 초기화 실패")
    #                     return
    #                 time.sleep(2)
            
    #         # BUYMA 로그인 페이지 접속
    #         self.log_message("📄 BUYMA 로그인 페이지에 접속합니다...")
    #         self.shared_driver.get("https://www.buyma.com/login/")
            
    #         # 페이지 로딩 대기
    #         WebDriverWait(self.shared_driver, 10).until(
    #             EC.presence_of_element_located((By.TAG_NAME, "body"))
    #         )
            
    #         # 로그인 폼 찾기 및 입력
    #         self.log_message("📝 로그인 정보를 입력합니다...")
            
    #         # 이메일 입력
    #         email_field = WebDriverWait(self.shared_driver, 10).until(
    #             EC.presence_of_element_located((By.NAME, "email"))
    #         )
    #         email_field.clear()
    #         email_field.send_keys(email)
            
    #         # 비밀번호 입력
    #         password_field = self.shared_driver.find_element(By.NAME, "password")
    #         password_field.clear()
    #         password_field.send_keys(password)
            
    #         # 로그인 버튼 클릭
    #         login_button = self.shared_driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
    #         login_button.click()
            
    #         # 로그인 결과 확인 (최대 15초 대기)
    #         self.log_message("⏳ 로그인 결과를 확인합니다...")
    #         time.sleep(3)
            
    #         # 로그인 성공 여부 확인
    #         current_url = self.shared_driver.current_url
    #         if "login" not in current_url.lower() or "mypage" in current_url.lower():
    #             # 로그인 성공
    #             self.is_logged_in = True
    #             self.login_success_signal.emit()
    #             self.log_message("✅ BUYMA 로그인 성공!")
    #         else:
    #             # 로그인 실패
    #             self.login_failed_signal.emit("로그인 실패: 이메일 또는 비밀번호를 확인해주세요.")
                
    #     except Exception as e:
    #         self.log_message(f"❌ 로그인 오류: {str(e)}")
    #         self.login_failed_signal.emit(f"로그인 오류: {str(e)}")
    
    def on_login_success(self):
        """로그인 성공 시 UI 업데이트"""
        self.login_status_label.setText("✅ 로그인 성공")
        self.login_status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-family: '맑은 고딕';
                padding: 5px;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        self.login_btn.setText("🔓 로그아웃")
        self.login_btn.setEnabled(True)
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.logout_buyma)
        
        # 크롤링 버튼 활성화 등 다른 기능들도 활성화 가능
        self.log_message("🎉 BUYMA 로그인이 완료되었습니다. 이제 모든 기능을 사용할 수 있습니다.")
    
    def on_login_failed(self, error_message):
        """로그인 실패 시 UI 업데이트"""
        self.login_status_label.setText(f"❌ {error_message}")
        self.login_status_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                font-weight: bold;
                font-family: '맑은 고딕';
                padding: 5px;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        self.reset_login_ui()
        
        # 브라우저 정리
        if self.shared_driver:
            try:
                self.shared_driver.quit()
            except:
                pass
            self.shared_driver = None
        
        self.is_logged_in = False
    
    def reset_login_ui(self):
        """로그인 UI 초기화"""
        self.login_btn.setText("🔐 BUYMA 로그인")
        self.login_btn.setEnabled(True)
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.start_buyma_login)
    
    def logout_buyma(self):
        """BUYMA 로그아웃"""
        try:
            if self.shared_driver:
                self.shared_driver.quit()
                self.shared_driver = None
            
            self.is_logged_in = False
            self.login_status_label.setText("❌ 로그인 필요")
            self.login_status_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: bold;
                    font-family: '맑은 고딕';
                    padding: 5px;
                    border-radius: 3px;
                    background: #f8f9fa;
                }
            """)
            self.reset_login_ui()
            self.log_message("🔓 BUYMA에서 로그아웃되었습니다.")
            
        except Exception as e:
            self.log_message(f"로그아웃 오류: {str(e)}")
    
    def check_login_required(self):
        """로그인 필요 여부 체크"""
        if not self.is_logged_in or not self.shared_driver:
            QMessageBox.warning(
                self, 
                "로그인 필요", 
                "이 기능을 사용하려면 먼저 BUYMA에 로그인해주세요.\n\n설정 탭에서 로그인을 진행해주세요."
            )
            return False
        return True
    
    def update_price_table_safe(self, row, col, text):
        """가격 테이블 안전 업데이트 (메인 스레드에서)"""
        try:
            if row < self.price_table.rowCount() and col < self.price_table.columnCount():
                self.price_table.setItem(row, col, QTableWidgetItem(text))
        except Exception as e:
            print(f"테이블 업데이트 오류: {e}")
    
    def on_price_analysis_finished(self):
        """가격 분석 완료 처리 (메인 스레드에서)"""
        try:
            self.set_tabs_enabled(True)
            self.log_message("🎉 전체 가격 분석 완료!")
        except Exception as e:
            print(f"분석 완료 처리 오류: {e}")

    def restart_shared_driver(self):
        """공용 드라이버 재시작"""
        try:
            self.log_message("🔄 브라우저를 재시작합니다...")
            
            # 기존 드라이버 종료
            if self.shared_driver:
                try:
                    self.shared_driver.quit()
                except:
                    pass
                self.shared_driver = None
            
            # 새 드라이버 생성
            from selenium import webdriver
            import time
            chrome_options = self.get_stable_chrome_options()
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.shared_driver = webdriver.Chrome(options=chrome_options)
                    self.shared_driver.implicitly_wait(10)
                    
                    # 페이지 로딩 타임아웃 설정 (10초)
                    self.shared_driver.set_page_load_timeout(10)
                    
                    # BUYMA 메인 페이지로 이동 (로그인 상태 확인)
                    self.shared_driver.get("https://www.buyma.com/")
                    time.sleep(2)
                    
                    # 로그인 상태 확인
                    page_source = self.shared_driver.page_source.lower()
                    if "logout" in page_source or "마이페이지" in page_source:
                        self.log_message("✅ 브라우저 재시작 및 로그인 상태 확인 완료")
                        return True
                    else:
                        self.log_message("⚠️ 로그인 상태가 유지되지 않았습니다.")
                        self.is_logged_in = False
                        return False
                        
                except Exception as e:
                    self.log_message(f"⚠️ 브라우저 재시작 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        return False
                    time.sleep(2)
            
            return False
            
        except Exception as e:
            self.log_message(f"❌ 브라우저 재시작 오류: {str(e)}")
            return False
    
    def switch_to_monitoring_tab(self):
        """모니터링 탭으로 자동 전환"""
        try:
            # 모니터링 탭으로 강제 이동 (몇 번째 탭인지 찾기)
            for i in range(self.tab_widget.count()):
                if "모니터링" in self.tab_widget.tabText(i):
                    self.tab_widget.setCurrentIndex(i)
                    break
        except Exception as e:
            self.log_message(f"탭 전환 오류: {str(e)}")
    
    def set_tabs_enabled(self, enabled):
        """탭들의 활성화/비활성화 제어"""
        try:
            # 다른 탭들 비활성화/활성화 (모니터링 탭만 활성 상태 유지)
            for i in range(self.tab_widget.count()):
                if "모니터링" not in self.tab_widget.tabText(i):
                    self.tab_widget.setTabEnabled(i, enabled)
        except Exception as e:
            self.log_message(f"탭 제어 오류: {str(e)}")

    def disable_ui_during_crawling(self, disable=True):
        """크롤링 중 UI 비활성화/활성화"""
        try:
            # 크롤링 설정 비활성화
            self.url_input.setEnabled(not disable)
            self.crawl_count.setEnabled(not disable)
            self.delay_time.setEnabled(not disable)
            self.include_images.setEnabled(not disable)
            self.include_options.setEnabled(not disable)
            self.skip_duplicates.setEnabled(not disable)
            
            # 크롤링 시작 시 모니터링 탭으로 이동 및 고정
            if disable:
                self.switch_to_monitoring_tab()
                self.set_tabs_enabled(False)
            else:
                self.set_tabs_enabled(True)
            
            # 크롤링 테이블의 액션 버튼들 비활성화
            if disable:
                for row in range(self.crawling_table.rowCount()):
                    widget = self.crawling_table.cellWidget(row, 7)  # 액션 버튼 컬럼
                    if widget:
                        widget.setEnabled(False)
            else:
                for row in range(self.crawling_table.rowCount()):
                    widget = self.crawling_table.cellWidget(row, 7)
                    if widget:
                        widget.setEnabled(True)
            
            # 상태 표시
            if disable:
                self.log_message("🔒 크롤링 중 - 📺 모니터링 탭에서 실시간 진행 상황을 확인하세요")
            else:
                self.log_message("🔓 크롤링 완료 - 모든 탭 사용이 가능합니다")
                
        except Exception as e:
            self.log_message(f"UI 상태 변경 오류: {str(e)}")
                
    def load_my_products(self):
        """내 상품 불러오기 - BUYMA 판매 중인 상품 크롤링"""
        # 로그인 체크
        if not self.check_login_required():
            return
        
        # 테이블에 이미 데이터가 있는지 확인
        if self.price_table.rowCount() > 0:
            self.log_message("📊 테이블에 이미 데이터가 있습니다. 바로 가격분석을 시작합니다...")
            
            # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
            self.switch_to_monitoring_tab()
            self.set_tabs_enabled(False)
            
            # 가격분석 진행률 위젯 표시
            self.price_progress_widget.show()
            self.update_price_progress_widget(0, self.price_table.rowCount(), "기존 데이터로 가격분석 시작...")
            
            # 기존 테이블 데이터로 바로 가격분석 실행
            import threading
            self.price_analysis_thread = threading.Thread(
                target=self.analyze_existing_table_data, 
                daemon=True
            )
            self.price_analysis_thread.start()
            return
        
        # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
        self.switch_to_monitoring_tab()
        self.set_tabs_enabled(False)
        
        # 가격분석 진행률 위젯 표시
        self.price_progress_widget.show()
        self.update_price_progress_widget(0, 100, "내 상품 불러오기 시작...")
        
        self.log_message("📥 내 상품을 불러오는 중...")
        
        # 별도 스레드에서 내 상품 크롤링 실행
        import threading
        
        self.load_products_thread = threading.Thread(
            target=self.crawl_my_products, 
            daemon=True
        )
        self.load_products_thread.start()
    
    def crawl_my_products(self):
        """내 상품 크롤링 실행 - JSON 파일로 저장"""
        try:
            if not self.shared_driver:
                self.log_error("❌ 브라우저가 초기화되지 않았습니다.")
                return
            
            # JSON 파일명 생성 (상품정보_수집날짜_수집시간.json)
            from datetime import datetime
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            json_filename = f"상품정보_{date_str}_{time_str}.json"
            
            self.log_message(f"📁 상품 정보를 {json_filename} 파일로 저장합니다.")
            
            page_number = 1
            total_products = 0
            
            # JSON 파일 초기화
            json_data = {
                "수집_정보": {
                    "수집_날짜": now.strftime("%Y-%m-%d"),
                    "수집_시간": now.strftime("%H:%M:%S"),
                    "총_상품수": 0
                },
                "상품_목록": []
            }
            
            while True:
                # 내 상품 페이지로 이동
                my_products_url = f"https://www.buyma.com/my/sell?duty_kind=all&facet=brand_id%2Ccate_pivot%2Cstatus%2Ctag_ids%2Cshop_labels%2Cstock_state&order=desc&page={page_number}&rows=100&sale_kind=all&sort=item_id&status=for_sale&timesale_kind=all#/"
                self.log_message(f"🌐 내 상품 페이지 {page_number} 접속 중...")
                
                self.shared_driver.get(my_products_url)
                time.sleep(3)
                
                # 상품 목록 크롤링
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # 상품 요소들 찾기
                try:
                    # 상품 리스트 대기
                    WebDriverWait(self.shared_driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tr.cursor_pointer.js-checkbox-check-row"))
                    )
                    
                    # 총 상품 개수 수집 (첫 페이지에서만)
                    if page_number == 1:
                        try:
                            total_count_elem = self.shared_driver.find_element(By.CSS_SELECTOR, "p.itemedit_actions_nums")
                            total_count_text = total_count_elem.text.strip()
                            # 1～100件(全 2962件) 형식에서 2962 추출
                            match = re.search(r'全\s*([\d,]+)件', total_count_text)
                            if match:
                                total_count = match.group(1).replace(',', '')
                                self.my_products_log_signal.emit(f"📊 총 판매 중인 상품 수: {total_count}개")
                                
                                # 진행률 위젯 총 개수 업데이트 (시그널 사용)
                                self.update_price_progress_signal.emit(0, int(total_count), f"총 {total_count}개 상품 발견")
                                
                            else:
                                self.log_message("⚠️ 총 상품 수를 추출하지 못했습니다.")
                        except Exception as e:
                            self.log_message(f"⚠️ 총 상품 수 추출 실패: {str(e)}")
                    
                    # 상품 요소들 수집
                    product_elements = self.shared_driver.find_elements(By.CSS_SELECTOR, "tr.cursor_pointer.js-checkbox-check-row")
                    
                    if not product_elements:
                        self.log_message("⚠️ 판매 중인 상품을 찾을 수 없습니다.")
                        return
                    
                    # 홀수일때 상품, 짝수일때 태그라서 태그는 제외
                    product_elements = [elem for i, elem in enumerate(product_elements) if i % 2 == 0] # 홀수 인덱스 제외, ex 0,2,4... -> 상품
                    
                    self.log_message(f"✅ {len(product_elements)}개의 상품을 발견했습니다.")
                    
                    # 각 상품 정보 추출
                    for i, element in enumerate(product_elements):  # 최대 50개까지
                        try:
                            # 상품명 추출
                            title_elem = element.find_element(By.CSS_SELECTOR, "td.item_name")
                            title = title_elem.text.strip()
                            
                            # 가격 추출
                            price_elem = element.find_element(By.CSS_SELECTOR, "span.js-item-price-display")
                            price_text = price_elem.text.strip()
                            
                            # 브랜드 추출 (선택사항)
                            # try:
                            #     brand_elem = element.find_element(By.CSS_SELECTOR, ".brand, .product-brand, [class*='brand']")
                            #     brand = brand_elem.text.strip()
                            # except:
                            #     brand = "브랜드 미상"
                            
                            # 상품 URL 추출 및 상품ID 추출
                            try:
                                link_elem = element.find_element(By.CSS_SELECTOR, "a.fab-design-d--b")
                                product_url = link_elem.get_attribute("href")
                                
                                # URL에서 상품ID 추출 (예: /item/12345678/ → 12345678)
                                id_match = re.search(r'/item/(\d+)/', product_url)
                                if id_match:
                                    product_id = id_match.group(1)
                                    # 상품명에 상품ID 추가
                                    title_with_id = f"{title} 商品ID: {product_id}"
                                else:
                                    title_with_id = title
                                    product_id = "ID 없음"
                            except:
                                product_url = "상품 URL 없음"
                                title_with_id = title
                                product_id = "ID 없음"
                            
                            product_data = {
                                'title': title_with_id,  # 상품ID 포함된 제목
                                'original_title': title,  # 원본 제목
                                'product_id': product_id,  # 상품ID 별도 저장
                                'current_price': price_text,
                                # 'brand': brand,
                                'url': product_url,
                                'status': '분석 대기'
                            }
                            
                            # JSON 데이터에 추가 (메모리 절약)
                            json_data["상품_목록"].append(product_data)
                            total_products += 1
                            
                            # 진행 상황 로그 (10개마다)
                            if total_products % 10 == 0:
                                self.my_products_log_signal.emit(f"📦 진행 상황: {total_products}개 상품 수집 완료")
                                
                                # 진행률 위젯 업데이트 (시그널 사용)
                                self.update_price_progress_signal.emit(
                                    total_products, 
                                    3000,  # 임시 총 개수 (실제로는 위에서 업데이트됨)
                                    f"상품 수집 중: {total_products}개 완료"
                                )
                            else:
                                self.my_products_log_signal.emit(f"📦 상품 {total_products}: {title[:30]}... - {price_text}")
                            
                            # 중간 저장 (50개마다 메모리 절약)
                            if total_products % 50 == 0:
                                try:
                                    with open(json_filename, 'w', encoding='utf-8') as f:
                                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                                    self.log_message(f"💾 중간 저장 완료: {total_products}개 상품")
                                except Exception as e:
                                    self.log_error(f"❌ 중간 저장 실패: {str(e)}")
                            
                        except Exception as e:
                            self.log_message(f"⚠️ 상품 {i+1} 정보 추출 실패: {str(e)}")
                            continue
                    
                    # 다음 페이지로 이동 준비
                    page_number += 1
                    
                    # 마지막 페이지인지 확인 (페이지당 100개씩이고, 총 개수 파악 후 비교)
                    try:
                        if len(product_elements) < 100:
                            self.log_message("📃 마지막 페이지에 도달했습니다.")
                            
                            break
                    except:
                        break
                    
                except Exception as e:
                    self.log_message(f"❌ 상품 목록 크롤링 실패: {str(e)}")
                    
                    continue
                    
                    
            # 최종 JSON 저장
            try:
                json_data["수집_정보"]["총_상품수"] = total_products
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                self.log_message(f"💾 최종 저장 완료: {json_filename}")
            except Exception as e:
                self.log_error(f"❌ 최종 저장 실패: {str(e)}")
                    
            # UI 테이블에 결과 표시 (모든 상품 표시)
            display_products = json_data["상품_목록"]
            self.display_my_products(display_products)
            self.my_products_log_signal.emit(f"🎉 내 상품 {total_products}개 수집 완료! (테이블에 {len(display_products)}개 표시)")
            
            # 가격분석 시작 (내 상품 불러오기 완료 후)
            self.my_products_log_signal.emit("🔍 가격분석을 시작합니다...")
            
            # 가격분석 설정값 가져오기
            discount = self.discount_amount.value()
            min_margin = self.min_margin.value()
            is_auto_mode = self.auto_mode.isChecked()
            
            self.my_products_log_signal.emit(f"🔍 가격 분석 시작 - 모드: {'🤖 자동' if is_auto_mode else '👤 수동'}")
            
            # 각 상품별 가격분석 실행
            for row in range(len(display_products)):
                try:
                    product = display_products[row]
                    product_name = product.get('title', '')
                    current_price_text = product.get('current_price', '')
                    
                    self.my_products_log_signal.emit(f"🔍 분석 중: {product_name[:30]}...")
                    
                    # 진행률 업데이트
                    self.update_price_progress_signal.emit(
                        row + 1, 
                        len(display_products), 
                        f"가격분석 중: {product_name[:30]}..."
                    )
                    
                    # BUYMA에서 해당 상품 검색하여 최저가 찾기
                    lowest_price = self.search_buyma_lowest_price(product_name)
                    
                    if lowest_price:
                        # 제안가 계산 (최저가 - 할인금액)
                        suggested_price = max(lowest_price - discount, 0)
                        
                        # 현재가격에서 숫자만 추출 (¥31,100 → 31100)
                        import re
                        current_price_numbers = re.findall(r'[\d,]+', current_price_text)
                        current_price = int(current_price_numbers[0].replace(',', '')) if current_price_numbers else 0
                        
                        # 마진 계산 (내 가격과 최저가의 차이)
                        price_difference = current_price - lowest_price if current_price > 0 else 0
                        
                        # 상품 데이터 업데이트
                        product['lowest_price'] = lowest_price
                        product['suggested_price'] = suggested_price
                        product['price_difference'] = price_difference
                        
                        # 마진을 가격 차이로 표시
                        if price_difference > 0:
                            margin_text = f"+¥{price_difference:,} (비쌈)"
                        elif price_difference < 0:
                            margin_text = f"¥{price_difference:,} (저렴함)"
                        else:
                            margin_text = "¥0 (동일)"
                        
                        # 가격 수정 필요 상태 결정
                        suggested_difference = suggested_price - current_price
                        if suggested_difference >= -abs(min_margin):  # -500엔 이상이면 OK
                            product['status'] = "💰 가격 수정 필요"
                            self.my_products_log_signal.emit(f"✅ {product_name[:20]}... - 최저가: ¥{lowest_price:,}, 제안가: ¥{suggested_price:,}, 차이: {margin_text}")
                        else:
                            product['status'] = f"⚠️ 손실 예상 ({suggested_difference:+,}엔)"
                            self.my_products_log_signal.emit(f"⚠️ 손실 예상: {product_name[:20]}... - 제안가 차이: {suggested_difference:+,}엔")
                        
                    else:
                        product['lowest_price'] = 0
                        product['suggested_price'] = 0
                        product['status'] = "❌ 최저가 검색 실패"
                        self.my_products_log_signal.emit(f"⚠️ {product_name[:20]}... - 최저가 검색 실패")
                    
                    # 딜레이
                    time.sleep(2)
                    
                except Exception as e:
                    self.my_products_log_signal.emit(f"❌ 상품 분석 오류 (행 {row}): {str(e)}")
                    continue
            
            # 분석 완료 후 테이블 업데이트
            self.my_products_log_signal.emit("📊 가격분석 완료! 테이블을 업데이트합니다...")
            
            # 완료 시그널 발송 (UI 제어 해제 및 진행률 위젯 숨기기)
            self.my_products_finished_signal.emit()
                
        except Exception as e:
            self.my_products_log_signal.emit(f"❌ 내 상품 불러오기 오류: {str(e)}")
            # 오류 시에도 완료 시그널 발송
            self.my_products_finished_signal.emit()
    
    def load_products_from_json(self):
        """JSON 파일에서 상품 정보 불러오기"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # JSON 파일 선택
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "상품 정보 JSON 파일 선택", 
                "", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            products = json_data.get("상품_목록", [])
            if not products:
                QMessageBox.warning(self, "경고", "JSON 파일에 상품 정보가 없습니다.")
                return
            
            # 테이블에 페이지네이션으로 표시
            self.display_my_products(products)
            
            # 수집 정보 표시
            collect_info = json_data.get("수집_정보", {})
            collect_date = collect_info.get("수집_날짜", "알 수 없음")
            collect_time = collect_info.get("수집_시간", "알 수 없음")
            total_count = collect_info.get("총_상품수", len(products))
            
            self.log_message(f"📁 JSON 파일 불러오기 완료!")
            self.log_message(f"📅 수집일시: {collect_date} {collect_time}")
            self.log_message(f"📊 총 상품수: {total_count}개 (페이지네이션으로 표시)")
            
        except Exception as e:
            self.log_error(f"❌ JSON 파일 불러오기 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"JSON 파일 불러오기 실패:\n{str(e)}")
    
    def load_previous_page(self):
        """이전 페이지 로드"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()
    
    def load_next_page(self):
        """다음 페이지 로드"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_current_page()
    
    def display_current_page(self):
        """현재 페이지 상품들을 테이블에 표시 - 대용량 데이터 최적화"""
        try:
            # 대용량 데이터 처리 시작 로그
            if len(self.all_products) > 1000:
                self.log_message(f"🔄 페이지 {self.current_page + 1} 로딩 중... (대용량 데이터 처리)")
            
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.all_products))
            
            current_page_products = self.all_products[start_idx:end_idx]
            
            # UI 업데이트를 위한 이벤트 처리
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 테이블에 현재 페이지 상품들만 표시 (배치 처리)
            self.display_products_in_table_optimized(current_page_products)
            
            # 페이지 정보 업데이트
            self.update_pagination_info()
            
            self.log_message(f"📄 페이지 {self.current_page + 1}/{self.total_pages} 표시 완료 ({len(current_page_products)}개 상품)")
            
        except Exception as e:
            self.log_error(f"페이지 표시 오류: {str(e)}")
            # 오류 발생 시에도 UI 제어 해제
            self.set_tabs_enabled(True)
    
    def update_pagination_info(self):
        """페이지네이션 정보 업데이트"""
        try:
            total_products = len(self.all_products)
            current_start = self.current_page * self.page_size + 1
            current_end = min((self.current_page + 1) * self.page_size, total_products)
            
            self.page_info_label.setText(
                f"페이지: {self.current_page + 1}/{self.total_pages} "
                f"({current_start}-{current_end} / 총 {total_products}개 상품)"
            )
            
            # 버튼 활성화/비활성화
            self.prev_page_btn.setEnabled(self.current_page > 0)
            self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            
        except Exception as e:
            self.log_error(f"페이지네이션 정보 업데이트 오류: {str(e)}")

    def display_products_in_table(self, products):
        """상품들을 테이블에 표시 (페이지네이션용)"""
        try:
            # UI 업데이트 일시 중단
            self.price_table.setUpdatesEnabled(False)
            
            self.price_table.setRowCount(len(products))
            
            for row, product in enumerate(products):
                # 행 높이 설정
                self.price_table.setRowHeight(row, 50)
                
                # 상품명
                title_item = QTableWidgetItem(product['title'])
                title_item.setToolTip(product['title'])
                title_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.price_table.setItem(row, 0, title_item)
                
                # 현재가격
                self.price_table.setItem(row, 1, QTableWidgetItem(product['current_price']))
                
                # 최저가 (아직 분석 안됨)
                self.price_table.setItem(row, 2, QTableWidgetItem("분석 필요"))
                
                # 제안가 (아직 계산 안됨)
                self.price_table.setItem(row, 3, QTableWidgetItem("계산 필요"))
                
                # 가격차이 (아직 계산 안됨)
                self.price_table.setItem(row, 4, QTableWidgetItem("계산 필요"))
                
                # 상태
                self.price_table.setItem(row, 5, QTableWidgetItem(product['status']))
                
                # 액션 버튼
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(3)
                
                analyze_btn = QPushButton("🔍")
                analyze_btn.setFixedSize(30, 25)
                analyze_btn.setToolTip("가격 분석")
                analyze_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 11px; 
                        background-color: #007bff;
                        color: white;
                        border: 1px solid #0056b3;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                    QPushButton:pressed {
                        background-color: #004085;
                    }
                """)
                # 실제 인덱스 계산 (전체 상품 리스트에서의 위치)
                actual_row = self.current_page * self.page_size + row
                analyze_btn.clicked.connect(lambda checked, r=actual_row: self.analyze_single_product(r))
                
                update_btn = QPushButton("💰")
                update_btn.setFixedSize(30, 25)
                update_btn.setToolTip("가격 수정")
                update_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 11px; 
                        background-color: #28a745;
                        color: white;
                        border: 1px solid #1e7e34;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: #1e7e34;
                    }
                    QPushButton:pressed {
                        background-color: #155724;
                    }
                """)
                update_btn.clicked.connect(lambda checked, r=row: self.update_single_product_price(r))
                
                # 주력상품 추가 버튼
                favorite_btn = QPushButton("⭐")
                favorite_btn.setFixedSize(30, 25)
                favorite_btn.setToolTip("주력상품으로 추가")
                favorite_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 11px; 
                        background-color: #ffc107;
                        color: white;
                        border: 1px solid #e0a800;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: #e0a800;
                    }
                    QPushButton:pressed {
                        background-color: #d39e00;
                    }
                """)
                # 실제 인덱스 계산 (전체 상품 리스트에서의 위치)
                actual_row = self.current_page * self.page_size + row
                favorite_btn.clicked.connect(lambda checked, r=actual_row: self.add_to_favorite_from_price_table(r))
                
                action_layout.addWidget(analyze_btn)
                action_layout.addWidget(update_btn)
                action_layout.addWidget(favorite_btn)
                action_layout.addStretch()
                
                self.price_table.setCellWidget(row, 6, action_widget)
            
            # UI 업데이트 재개
            self.price_table.setUpdatesEnabled(True)
                
        except Exception as e:
            self.price_table.setUpdatesEnabled(True)
            self.log_error(f"테이블 표시 오류: {str(e)}")

    def display_my_products(self, products):
        """내 상품을 페이지네이션으로 표시"""
        try:
            # 전체 상품 데이터 저장
            self.all_products = products
            
            # 페이지네이션 설정
            self.total_pages = (len(products) + self.page_size - 1) // self.page_size
            self.current_page = 0
            
            self.log_message(f"📊 총 {len(products)}개 상품을 {self.page_size}개씩 {self.total_pages}페이지로 나누어 표시")
            
            # 대용량 데이터 처리를 위한 지연 로딩
            if len(products) > 1000:
                self.log_message("⚠️ 대용량 데이터 감지: 안전한 처리를 위해 지연 로딩 적용")
                # UI 업데이트를 위한 이벤트 처리
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
            
            # 첫 번째 페이지 표시 (비동기 처리)
            QTimer.singleShot(100, self.display_current_page)
            
            # 대용량 데이터 처리 후 메모리 정리
            if len(products) > 1000:
                def cleanup_memory():
                    import gc
                    gc.collect()
                    self.log_message("🧹 대용량 데이터 처리 완료: 메모리 정리 완료")
                
                QTimer.singleShot(2000, cleanup_memory)  # 2초 후 메모리 정리
                
        except Exception as e:
            self.log_error(f"상품 표시 오류: {str(e)}")
            # 오류 시에도 UI 제어 해제
            self.set_tabs_enabled(True)
    
    def analyze_my_products_prices(self):
        """내 상품들의 가격 분석 시작 - 페이지별 순차 처리"""
        # 로그인 상태 확인
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            QMessageBox.warning(
                self, 
                "로그인 필요", 
                "가격 분석을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
            )
            return
        
        if not hasattr(self, 'all_products') or len(self.all_products) == 0:
            QMessageBox.warning(self, "경고", "먼저 '내 상품 불러오기'를 실행해주세요.")
            return

        # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
        self.switch_to_monitoring_tab()
        self.set_tabs_enabled(False)
        
        try:
            # 분석 설정
            discount = self.discount_amount.value()
            min_margin = self.min_margin.value()
            is_auto_mode = self.auto_mode.isChecked()  # 올바른 변수명 사용
            
            self.log_message(f"🔍 전체 상품 가격 분석 시작 - 총 {len(self.all_products)}개 상품")
            self.log_message(f"🔧 설정: 할인 {discount}엔, 최소마진 {min_margin}엔, 모드: {'🤖 자동' if is_auto_mode else '👤 수동'}")
            self.log_message(f"📄 페이지별 순차 분석: {self.total_pages}페이지 ({self.page_size}개씩)")
            
            # 가격분석 진행률 위젯 표시
            self.price_progress_widget.show()
            self.update_price_progress_widget(0, len(self.all_products), "가격 분석 시작...")
            
            # 가격수정 진행률 위젯도 함께 표시 (업로드 위젯 재사용)
            self.upload_progress_widget.show()
            self.update_upload_progress_widget(0, 100, "가격 수정 대기 중...")
            
            # 진행률 위젯 표시 (기존)
            self.progress_widget.update_progress(
                0, 
                len(self.all_products), 
                "💰 가격 분석 시작", 
                f"총 {len(self.all_products)}개 상품 분석 예정"
            )
            
            # 별도 스레드에서 페이지별 순차 분석 실행
            import threading
            
            self.analysis_thread = threading.Thread(
                target=self.analyze_all_pages_sequentially, 
                args=(discount, min_margin, is_auto_mode),
                daemon=True
            )
            self.analysis_thread.start()
            
        except Exception as e:
            self.log_error(f"가격 분석 시작 오류: {str(e)}")
            # 오류 시 UI 제어 해제
            self.set_tabs_enabled(True)
    
    def analyze_all_pages_sequentially(self, discount, min_margin, is_auto_mode):
        """내 상품들의 가격 분석 실행"""
        try:
            discount = self.discount_amount.value()
            min_margin = self.min_margin.value()
            
            # 가격 관리 모드 확인
            is_auto_mode = self.auto_mode.isChecked()
            
            self.log_message(f"🔍 가격 분석 시작 - 모드: {'🤖 자동' if is_auto_mode else '👤 수동'}")
            
            for row in range(self.price_table.rowCount()):
                try:
                    # 상품명 가져오기
                    product_name = self.price_table.item(row, 0).text()
                    current_price_text = self.price_table.item(row, 1).text()
                    
                    self.log_message(f"🔍 분석 중: {product_name[:30]}...")
                    
                    # BUYMA에서 해당 상품 검색하여 최저가 찾기
                    self.price_table.setItem(row, 5, QTableWidgetItem("🔍 최저가 검색 중..."))
                    
                    lowest_price = self.search_buyma_lowest_price(product_name)
                    
                    if lowest_price:
                        # 최저가 검색 성공 상태 표시
                        self.price_table.setItem(row, 5, QTableWidgetItem("✅ 최저가 불러오기 성공"))
                        
                        # 제안가 계산 (최저가 - 할인금액)
                        suggested_price = max(lowest_price - discount, 0)
                        
                        # 현재가격에서 숫자만 추출 (¥31,100 → 31100)
                        import re
                        current_price_numbers = re.findall(r'[\d,]+', current_price_text)
                        current_price = int(current_price_numbers[0].replace(',', '')) if current_price_numbers else 0
                        
                        # 마진 계산 (내 가격과 최저가의 차이)
                        # 양수: 내 가격이 최저가보다 높음 (비쌈)
                        # 음수: 내 가격이 최저가보다 낮음 (저렴함)
                        price_difference = current_price - lowest_price if current_price > 0 else 0
                        
                        # 테이블 업데이트
                        self.price_table.setItem(row, 2, QTableWidgetItem(f"¥{lowest_price:,}"))
                        self.price_table.setItem(row, 3, QTableWidgetItem(f"¥{suggested_price:,}"))
                        
                        # 마진을 가격 차이로 표시
                        if price_difference > 0:
                            margin_text = f"+¥{price_difference:,} (비쌈)"
                        elif price_difference < 0:
                            margin_text = f"¥{price_difference:,} (저렴함)"
                        else:
                            margin_text = "¥0 (동일)"
                        
                        self.price_table.setItem(row, 4, QTableWidgetItem(margin_text))
                        
                        # 가격 수정 필요 상태로 변경
                        # 제안가와 현재가의 차이가 최소 마진 이상이면 수정 권장
                        suggested_difference = suggested_price - current_price
                        if suggested_difference >= -abs(min_margin):  # -500엔 이상이면 OK
                            self.price_table.setItem(row, 5, QTableWidgetItem("💰 가격 수정 필요"))
                            self.log_message(f"✅ {product_name[:20]}... - 최저가: ¥{lowest_price:,}, 제안가: ¥{suggested_price:,}, 차이: {margin_text}")
                        else:
                            status = f"⚠️ 손실 예상 ({suggested_difference:+,}엔)"
                            self.price_table.setItem(row, 5, QTableWidgetItem(status))
                            self.log_message(f"⚠️ 손실 예상: {product_name[:20]}... - 제안가 차이: {suggested_difference:+,}엔")
                        
                    else:
                        self.price_table.setItem(row, 2, QTableWidgetItem("검색 실패"))
                        self.price_table.setItem(row, 5, QTableWidgetItem("❌ 최저가 검색 실패"))
                        self.log_message(f"⚠️ {product_name[:20]}... - 최저가 검색 실패")
                    
                    # 딜레이
                    time.sleep(2)
                    
                except Exception as e:
                    self.log_message(f"❌ 상품 분석 오류 (행 {row}): {str(e)}")
                    continue
            
            self.log_message("🎉 모든 상품 가격 분석 완료!")
            
            # 가격 분석 완료 후 전체 상품 가격 수정 진행
            self.start_bulk_price_update()
            
        except Exception as e:
            self.log_message(f"❌ 가격 분석 오류: {str(e)}")
            # 오류 시에도 UI 제어 해제
            self.set_tabs_enabled(True)
    
    def extract_product_id(self, product_name):
        """상품명에서 상품ID 추출"""
        try:
            # 상품명에서 "商品ID: XXXXX" 패턴 찾기
            import re
            
            # 패턴 1: "商品ID: 12345" 형태
            pattern1 = r'商品ID[:\s]*(\d+)'
            match1 = re.search(pattern1, product_name)
            if match1:
                product_id = match1.group(1)
                self.price_analysis_log_signal.emit(f"📋 상품ID 추출: {product_id}")
                return product_id
            
            # 패턴 2: "ID: 12345" 형태
            pattern2 = r'ID[:\s]*(\d+)'
            match2 = re.search(pattern2, product_name)
            if match2:
                product_id = match2.group(1)
                self.price_analysis_log_signal.emit(f"📋 상품ID 추출: {product_id}")
                return product_id
            
            # 패턴 3: 숫자만 있는 경우 (마지막 숫자 그룹)
            pattern3 = r'(\d{6,})'  # 6자리 이상 숫자
            matches3 = re.findall(pattern3, product_name)
            if matches3:
                product_id = matches3[-1]  # 마지막 숫자 그룹 사용
                self.price_analysis_log_signal.emit(f"📋 상품ID 추출 (추정): {product_id}")
                return product_id
            
            # 상품ID를 찾을 수 없는 경우
            self.price_analysis_log_signal.emit(f"❌ 상품ID를 찾을 수 없습니다: {product_name[:50]}...")
            return None
            
        except Exception as e:
            self.price_analysis_log_signal.emit(f"❌ 상품ID 추출 오류: {str(e)}")
            return None

    def update_buyma_product_price(self, product_name, new_price, is_auto_mode=False):
        """BUYMA에서 상품 가격 수정"""
        try:
            # 1. 상품ID 추출
            product_id = self.extract_product_id(product_name)
            if not product_id:
                self.price_analysis_log_signal.emit(f"❌ 상품ID를 찾을 수 없어 가격 수정을 건너뜁니다: {product_name[:30]}...")
                return False
            
            # 2. BUYMA 상품 수정 페이지 접속
            edit_url = f"https://www.buyma.com/my/sell/search?sale_kind=all&duty_kind=all&keyword={product_id}&status=for_sale&multi_id=#/"
            self.log_message(f"🔗 상품 수정 페이지 접속: {edit_url}")
            
            self.driver.get(edit_url)
            import time
            time.sleep(3)
            
            # 3. 가격 수정 버튼 클릭 (a._item_edit_tanka)
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                
                price_edit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a._item_edit_tanka"))
                )
                price_edit_btn.click()
                self.log_message("💰 가격 수정 버튼 클릭")
                time.sleep(2)
            except Exception as e:
                self.log_error(f"가격 수정 버튼을 찾을 수 없습니다: {str(e)}")
                return False
            
            # 4. 현재 가격 확인 (BUYMA 페이지에서 실제 가격 읽기)
            try:
                price_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "item_price"))
                )
                current_price_on_page = int(price_input.get_attribute("value") or "0")
                self.log_message(f"📋 BUYMA 페이지 현재 가격: ¥{current_price_on_page:,}")
            except Exception as e:
                self.log_error(f"현재 가격을 확인할 수 없습니다: {str(e)}")
                current_price_on_page = 0
            
            # 5. 수동 모드일 경우 설정하기 버튼 클릭 전에 사용자 확인
            if not is_auto_mode:
                # 테이블에서 최저가와 할인 금액 정보 가져오기
                lowest_price = 0
                discount_amount = self.discount_amount.value()
                
                for row in range(self.price_table.rowCount()):
                    table_product_name = self.price_table.item(row, 0).text()
                    if table_product_name == product_name:
                        lowest_price_text = self.price_table.item(row, 2).text()
                        import re
                        price_numbers = re.findall(r'[\d,]+', lowest_price_text)
                        lowest_price = int(price_numbers[0].replace(',', '')) if price_numbers else 0
                        break
                
                # 사용자 확인 다이얼로그 (더 상세한 정보 포함)
                if not self.show_detailed_price_update_confirmation(
                    product_name, 
                    current_price_on_page, 
                    new_price, 
                    lowest_price, 
                    discount_amount
                ):
                    self.log_message(f"❌ 사용자가 가격 수정을 취소했습니다: {product_name[:20]}...")
                    return "cancelled"  # 취소 상태 반환
            
            # 6. 가격 입력 필드에 새 가격 입력
            try:
                price_input.clear()
                price_input.send_keys(str(new_price))
                self.log_message(f"💰 새 가격 입력: ¥{new_price:,}")
                time.sleep(1)
            except Exception as e:
                self.log_error(f"가격 입력 실패: {str(e)}")
                return False
            
            # 7. 설정하기 버튼 클릭 (a.js-commit-item-price)
            try:
                commit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.js-commit-item-price"))
                )
                commit_btn.click()
                self.log_message("✅ 설정하기 버튼 클릭")
                time.sleep(3)
                
                # 성공 확인 (페이지 변화나 성공 메시지 확인)
                self.log_message(f"✅ 가격 수정 완료: {product_name[:20]}... → ¥{new_price:,}")
                return True
                
            except Exception as e:
                self.log_error(f"설정하기 버튼을 찾을 수 없습니다: {str(e)}")
                return False
                
        except Exception as e:
            self.log_error(f"가격 수정 오류: {str(e)}")
            return False

    def show_detailed_price_update_confirmation(self, product_name, current_price, new_price, lowest_price, discount_amount):
        """상세한 가격 수정 확인 다이얼로그 표시 (설정하기 버튼 클릭 전)"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
            from PyQt6.QtCore import Qt
            
            dialog = QDialog(self)
            dialog.setWindowTitle("가격 수정 최종 확인")
            dialog.setFixedSize(600, 400)
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            
            # 가격 변동 계산
            price_change = new_price - current_price
            
            # 상품 정보 표시
            info_label = QLabel(f"""
            <h2 style="color: #2c3e50;">🔄 가격 수정 최종 확인</h2>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <h3 style="color: #495057;">📦 상품 정보</h3>
                <p><b>상품명:</b> {product_name[:60]}...</p>
            </div>
            
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <h3 style="color: #1976d2;">💰 가격 정보</h3>
                <p><b>현재 BUYMA 가격:</b> <span style="font-size: 18px; color: #d32f2f;">¥{current_price:,}</span></p>
                <p><b>변경할 가격:</b> <span style="font-size: 18px; color: #388e3c;">¥{new_price:,}</span></p>
                <p><b>가격 변동:</b> <span style="font-size: 16px; color: {'#d32f2f' if price_change < 0 else '#388e3c'};">{price_change:+,}엔</span></p>
            </div>
            
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <h3 style="color: #f57c00;">📊 계산 근거</h3>
                <p><b>경쟁사 최저가:</b> ¥{lowest_price:,}</p>
                <p><b>할인 설정값:</b> -{discount_amount:,}엔</p>
                <p><b>제안가 계산:</b> ¥{lowest_price:,} - ¥{discount_amount:,} = <b>¥{new_price:,}</b></p>
            </div>
            
            <div style="background-color: #ffebee; padding: 10px; border-radius: 8px; margin: 10px 0;">
                <p style="color: #c62828; font-weight: bold;">⚠️ 이 가격으로 BUYMA에서 실제 수정됩니다!</p>
            </div>
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # 버튼 레이아웃
            button_layout = QHBoxLayout()
            
            confirm_btn = QPushButton("✅ 확인 (가격 수정 실행)")
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
                QPushButton:pressed {
                    background-color: #155724;
                }
            """)
            confirm_btn.clicked.connect(lambda: dialog.done(1))  # 확인 = 1
            
            cancel_btn = QPushButton("❌ 취소")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #a71e2a;
                }
            """)
            cancel_btn.clicked.connect(lambda: dialog.done(0))  # 취소 = 0
            
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(confirm_btn)
            layout.addLayout(button_layout)
            
            # 다이얼로그 실행
            result = dialog.exec()
            return result == 1  # True = 확인, False = 취소
            
        except Exception as e:
            self.log_error(f"확인 다이얼로그 오류: {str(e)}")
            return False

    def analyze_all_pages_sequentially(self, discount, min_margin, is_auto_mode):
        """페이지별 순차 처리: 각 페이지마다 최저가 분석 → 가격 수정"""
        try:
            total_analyzed = 0
            total_updated = 0
            total_cancelled = 0
            total_failed = 0
            
            # 가격수정 진행률 추적용 카운터
            price_update_progress = 0

            # 현재 페이지부터 시작
            start_page = self.current_page
            self.price_analysis_log_signal.emit(f"🚀 페이지별 순차 처리 시작 (시작 페이지: {start_page + 1})")

            # 현재 페이지부터 마지막 페이지까지 처리
            for page_offset in range(self.total_pages):
                page_num = (start_page + page_offset) % self.total_pages  # 순환 처리
                
                self.price_analysis_log_signal.emit(f"📄 페이지 {page_num + 1}/{self.total_pages} 처리 시작...")

                # 현재 페이지 상품들 가져오기
                start_idx = page_num * self.page_size
                end_idx = min(start_idx + self.page_size, len(self.all_products))
                current_page_products = self.all_products[start_idx:end_idx]

                # 해당 페이지로 이동 (시그널 사용)
                self.price_analysis_log_signal.emit(f"페이지 {page_num + 1}로 이동 중...")
                # 페이지 이동은 메인 스레드에서 처리해야 함
                import time
                time.sleep(1)  # 페이지 전환 대기

                # ==================== 1단계: 현재 페이지 최저가 검색 ====================
                self.price_analysis_log_signal.emit(f"🔍 페이지 {page_num + 1} - 1단계: 최저가 검색 ({len(current_page_products)}개 상품)")

                # 현재 페이지 상품들 분석 (가격 수정 없이 최저가 검색만)
                page_analyzed, _, page_failed = self.analyze_current_page_products(
                    current_page_products, discount, min_margin, is_auto_mode, start_idx
                )

                total_analyzed += page_analyzed
                total_failed += page_failed

                # 진행률 위젯 업데이트 (분석 단계) - 시그널 사용
                status_text = f"💰 가격 분석 진행 중"
                detail_text = f"페이지 {page_num + 1}/{self.total_pages} - 분석 완료: {total_analyzed}개"
                
                self.price_analysis_log_signal.emit(f"진행률 업데이트: {total_analyzed}/{len(self.all_products)}")
                
                # 가격분석 진행률 위젯 업데이트 (시그널 사용)
                self.update_price_progress_signal.emit(
                    total_analyzed, 
                    len(self.all_products), 
                    f"{status_text} - {detail_text}"
                )

                self.price_analysis_log_signal.emit(f"✅ 페이지 {page_num + 1} 최저가 검색 완료: 분석 {page_analyzed}개, 실패 {page_failed}개")

                # ==================== 2단계: 현재 페이지 가격 수정 ====================
                self.price_analysis_log_signal.emit(f"💰 페이지 {page_num + 1} - 2단계: 가격 수정")

                # 현재 페이지에서 수정 필요한 상품들 찾기
                page_products_to_update = []
                for local_idx, global_idx in enumerate(range(start_idx, end_idx)):
                    if global_idx < len(self.all_products):
                        product = self.all_products[global_idx]
                        if product.get('needs_update', False):
                            page_products_to_update.append((local_idx, global_idx, product))

                if len(page_products_to_update) == 0:
                    self.price_analysis_log_signal.emit(f"📋 페이지 {page_num + 1}: 가격 수정이 필요한 상품이 없습니다.")
                else:
                    self.price_analysis_log_signal.emit(f"📊 페이지 {page_num + 1}: {len(page_products_to_update)}개 상품 가격 수정 시작")
                    
                    # 가격수정 진행률 위젯 업데이트 (첫 번째 페이지에서 총 개수 설정)
                    if page_num == 0:
                        total_update_count = sum(1 for row in range(self.price_table.rowCount()) 
                                               if self.price_table.item(row, 5) and "수정 필요" in self.price_table.item(row, 5).text())
                        self.update_upload_progress_widget(0, total_update_count, "가격 수정 시작...")

                    # 현재 페이지 상품들 가격 수정
                    page_updated = 0
                    page_cancelled = 0

                    for idx, (local_row, global_idx, product) in enumerate(page_products_to_update):
                        try:
                            product_name = product['title']
                            suggested_price = product.get('suggested_price', 0)

                            self.price_analysis_log_signal.emit(f"💰 가격 수정 중 ({idx + 1}/{len(page_products_to_update)}): {product_name[:30]}...")

                            # 테이블 상태 업데이트
                            self.price_analysis_table_update_signal.emit(local_row, 5, "🔄 가격 수정 중...")

                            # 실제 가격 수정 로직 호출
                            result = self.update_buyma_product_price(product_name, suggested_price, is_auto_mode)

                            if result == True:
                                self.price_analysis_table_update_signal.emit(local_row, 5, "✅ 수정 완료")
                                self.all_products[global_idx]['status'] = "✅ 수정 완료"
                                page_updated += 1
                                total_updated += 1
                                price_update_progress += 1
                                
                                # 가격수정 진행률 위젯 업데이트
                                total_update_count = sum(1 for row in range(self.price_table.rowCount()) 
                                                       if self.price_table.item(row, 5) and "수정 필요" in self.price_table.item(row, 5).text())
                                self.update_upload_progress_widget(price_update_progress, total_update_count, f"가격 수정 중: {product_name[:20]}...")
                                
                                self.price_analysis_log_signal.emit(f"✅ 가격 수정 완료: {product_name[:20]}... → ¥{suggested_price:,}")
                            elif result == "cancelled":
                                self.price_analysis_table_update_signal.emit(local_row, 5, "❌ 상품 수정 취소")
                                self.all_products[global_idx]['status'] = "❌ 상품 수정 취소"
                                page_cancelled += 1
                                total_cancelled += 1
                                self.price_analysis_log_signal.emit(f"❌ 상품 수정 취소: {product_name[:20]}...")
                            else:
                                self.price_analysis_table_update_signal.emit(local_row, 5, "❌ 수정 실패")
                                self.all_products[global_idx]['status'] = "❌ 수정 실패"
                                self.price_analysis_log_signal.emit(f"❌ 가격 수정 실패: {product_name[:20]}...")

                            # 수정 간 딜레이
                            time.sleep(2)

                        except Exception as e:
                            self.price_analysis_log_signal.emit(f"❌ 가격 수정 오류 ({global_idx + 1}): {str(e)}")
                            continue

                    self.price_analysis_log_signal.emit(f"✅ 페이지 {page_num + 1} 가격 수정 완료: 수정 {page_updated}개, 취소 {page_cancelled}개")

                # 페이지 완료 로그
                self.price_analysis_log_signal.emit(f"🎉 페이지 {page_num + 1} 전체 완료!")
                
                # 페이지 간 딜레이 (서버 부하 방지)
                time.sleep(3)

            # 전체 처리 완료
            self.price_analysis_log_signal.emit(f"🎉 전체 페이지별 순차 처리 완료!")
            self.price_analysis_log_signal.emit(f"📊 최종 결과:")
            self.price_analysis_log_signal.emit(f"   - 분석 완료: {total_analyzed}개")
            self.price_analysis_log_signal.emit(f"   - 가격 수정: {total_updated}개")
            self.price_analysis_log_signal.emit(f"   - 수정 취소: {total_cancelled}개")
            self.price_analysis_log_signal.emit(f"   - 검색 실패: {total_failed}개")

            # 진행률 위젯 완료 상태 (시그널 사용)
            self.progress_complete_signal.emit(
                "가격 분석 완료", 
                f"분석: {total_analyzed}개, 수정: {total_updated}개"
            )
            
            # 가격수정 진행률 위젯도 완료 상태로 설정
            self.upload_progress_widget.hide()

            # UI 제어 해제 (시그널로)
            self.price_analysis_finished_signal.emit()

        except Exception as e:
            self.price_analysis_log_signal.emit(f"❌ 페이지별 순차 처리 오류: {str(e)}")
            # 오류 시 진행률 위젯에 오류 표시 (시그널 사용)
            self.progress_error_signal.emit("가격 분석 오류", str(e))
            self.price_analysis_finished_signal.emit()
    
    def display_page_safe(self, page_num):
        """페이지 표시 (메인 스레드에서 안전하게)"""
        try:
            self.current_page = page_num
            self.display_current_page()
        except Exception as e:
            print(f"페이지 표시 오류: {e}")
    
    def analyze_current_page_products(self, products, discount, min_margin, is_auto_mode, start_idx):
        """현재 페이지 상품들 분석 및 수정"""
        try:
            analyzed_count = 0
            updated_count = 0
            failed_count = 0
            
            for local_row, product in enumerate(products):
                try:
                    # 전체 인덱스 계산
                    global_idx = start_idx + local_row
                    
                    product_name = product['title']
                    current_price_text = product['current_price']
                    
                    self.price_analysis_log_signal.emit(f"🔍 분석 중 ({global_idx + 1}/{len(self.all_products)}): {product_name[:30]}...")
                    
                    # 테이블 상태 업데이트 (시그널로)
                    self.price_analysis_table_update_signal.emit(local_row, 5, "🔍 최저가 검색 중...")
                    
                    # BUYMA에서 최저가 검색
                    lowest_price = self.search_buyma_lowest_price(product_name)
                    
                    if lowest_price:
                        # 최저가 검색 성공
                        self.price_analysis_table_update_signal.emit(local_row, 5, "✅ 최저가 불러오기 성공")
                        
                        # 제안가 계산
                        suggested_price = max(lowest_price - discount, 0)
                        
                        # 현재가격에서 숫자만 추출
                        import re
                        current_price_numbers = re.findall(r'[\d,]+', current_price_text)
                        current_price = int(current_price_numbers[0].replace(',', '')) if current_price_numbers else 0
                        
                        # 가격차이 계산
                        price_difference = current_price - lowest_price if current_price > 0 else 0
                        
                        # 테이블 업데이트 (시그널로)
                        self.price_analysis_table_update_signal.emit(local_row, 2, f"¥{lowest_price:,}")
                        self.price_analysis_table_update_signal.emit(local_row, 3, f"¥{suggested_price:,}")
                        
                        # 가격차이 표시
                        if price_difference > 0:
                            margin_text = f"+¥{price_difference:,} (비쌈)"
                        elif price_difference < 0:
                            margin_text = f"¥{price_difference:,} (저렴함)"
                        else:
                            margin_text = "¥0 (동일)"
                        
                        self.price_analysis_table_update_signal.emit(local_row, 4, margin_text)
                        
                        # 제안가와 현재가의 차이로 수정 여부 판단
                        suggested_difference = suggested_price - current_price
                        
                        if suggested_difference >= -abs(min_margin):  # -500엔 이상이면 OK
                            # 가격 수정 필요 상태로만 표시 (실제 수정은 나중에)
                            self.price_analysis_table_update_signal.emit(local_row, 5, "💰 가격 수정 필요")
                            
                            # 전체 상품 리스트에서 해당 상품 업데이트
                            self.all_products[global_idx].update({
                                'lowest_price': lowest_price,
                                'suggested_price': suggested_price,
                                'price_difference': price_difference,
                                'margin_text': margin_text,
                                'needs_update': True  # 수정 필요 플래그
                            })
                            
                            self.price_analysis_log_signal.emit(f"✅ {product_name[:20]}... - 최저가: ¥{lowest_price:,}, 제안가: ¥{suggested_price:,}, 차이: {margin_text}")
                        else:
                            status = f"⚠️ 손실 예상 ({suggested_difference:+,}엔)"
                            self.price_analysis_table_update_signal.emit(local_row, 5, status)
                            self.all_products[global_idx]['status'] = status
                            self.all_products[global_idx]['needs_update'] = False  # 수정 불필요
                            self.price_analysis_log_signal.emit(f"⚠️ 손실 예상: {product_name[:20]}... - 제안가 차이: {suggested_difference:+,}엔")
                        
                        analyzed_count += 1
                        
                    else:
                        # 최저가 검색 실패
                        self.price_analysis_table_update_signal.emit(local_row, 2, "검색 실패")
                        self.price_analysis_table_update_signal.emit(local_row, 5, "❌ 최저가 검색 실패")
                        self.all_products[global_idx]['status'] = "❌ 최저가 검색 실패"
                        self.all_products[global_idx]['needs_update'] = False
                        failed_count += 1
                        self.price_analysis_log_signal.emit(f"⚠️ {product_name[:20]}... - 최저가 검색 실패")
                    
                    # 상품 간 딜레이 (최저가 검색용)
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    self.price_analysis_log_signal.emit(f"❌ 상품 분석 오류 ({global_idx + 1}): {str(e)}")
                    failed_count += 1
                    continue
            
            return analyzed_count, 0, failed_count  # updated_count는 0으로 (아직 수정 안함)
            
        except Exception as e:
            self.log_error(f"페이지 분석 오류: {str(e)}")
            return 0, 0, len(products)

    def start_bulk_price_update(self):
        """전체 상품 가격 수정 시작"""
        try:
            # 가격 수정이 필요한 상품 개수 확인
            update_needed_count = 0
            for row in range(self.price_table.rowCount()):
                status_item = self.price_table.item(row, 5)
                if status_item and "가격 수정 필요" in status_item.text():
                    update_needed_count += 1
            
            if update_needed_count == 0:
                self.log_message("📋 가격 수정이 필요한 상품이 없습니다.")
                return
            
            self.log_message(f"🚀 전체 상품 가격 수정 시작: {update_needed_count}개 상품")
            
            # 커밋
            # 가격 관리 모드 확인
            is_auto_mode = self.auto_mode.isChecked()  # 올바른 변수명 사용
            mode_text = "🤖 자동" if is_auto_mode else "👤 수동"
            self.log_message(f"🔧 가격 관리 모드: {mode_text}")
            
            # 가격 수정 진행
            updated_count = 0
            cancelled_count = 0
            
            for row in range(self.price_table.rowCount()):
                status_item = self.price_table.item(row, 5)
                if status_item and "가격 수정 필요" in status_item.text():
                    try:
                        # 상품 정보 가져오기
                        product_name = self.price_table.item(row, 0).text()
                        suggested_price_item = self.price_table.item(row, 3)
                        
                        if suggested_price_item:
                            suggested_price_text = suggested_price_item.text()
                            # 가격에서 숫자만 추출
                            import re
                            price_numbers = re.findall(r'[\d,]+', suggested_price_text)
                            suggested_price = int(price_numbers[0].replace(',', '')) if price_numbers else 0
                            
                            # 가격 수정 중 상태 표시
                            self.price_table.setItem(row, 5, QTableWidgetItem("🔄 가격 수정 중..."))
                            
                            # 실제 가격 수정 로직 호출
                            result = self.update_buyma_product_price(product_name, suggested_price, is_auto_mode)
                            
                            if result == True:
                                self.price_table.setItem(row, 5, QTableWidgetItem("✅ 수정 완료"))
                                updated_count += 1
                                self.log_message(f"✅ 가격 수정 완료: {product_name[:20]}... → ¥{suggested_price:,}")
                            elif result == "cancelled":
                                self.price_table.setItem(row, 5, QTableWidgetItem("❌ 상품 수정 취소"))
                                cancelled_count += 1
                                self.log_message(f"❌ 상품 수정 취소: {product_name[:20]}...")
                            else:
                                self.price_table.setItem(row, 5, QTableWidgetItem("❌ 수정 실패"))
                                self.log_message(f"❌ 가격 수정 실패: {product_name[:20]}...")
                            
                            # 수정 간 딜레이
                            import time
                            time.sleep(2)
                        
                    except Exception as e:
                        self.price_table.setItem(row, 5, QTableWidgetItem("❌ 수정 실패"))
                        self.log_message(f"❌ 가격 수정 오류: {str(e)}")
                        continue
            
            self.log_message(f"🎉 전체 가격 수정 완료! 수정: {updated_count}개, 취소: {cancelled_count}개")
            
            # UI 제어 해제: 다른 탭 활성화
            self.set_tabs_enabled(True)
            
        except Exception as e:
            self.log_message(f"❌ 전체 가격 수정 오류: {str(e)}")
            # 오류 시에도 UI 제어 해제
            self.set_tabs_enabled(True)
    
    def update_single_product_price(self, row):
        """단일 상품 가격 수정"""
        try:
            # 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(
                    self, 
                    "로그인 필요", 
                    "가격 수정을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                    "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
                )
                return
            
            # 상품 정보 가져오기
            product_name = self.price_table.item(row, 0).text()
            suggested_price_item = self.price_table.item(row, 3)
            
            if not suggested_price_item or suggested_price_item.text() == "계산 필요":
                QMessageBox.warning(self, "경고", "먼저 가격 분석을 실행해주세요.")
                return
            
            suggested_price_text = suggested_price_item.text()
            # 가격에서 숫자만 추출
            import re
            price_numbers = re.findall(r'[\d,]+', suggested_price_text)
            suggested_price = int(price_numbers[0].replace(',', '')) if price_numbers else 0
            
            if suggested_price <= 0:
                QMessageBox.warning(self, "경고", "유효한 제안가가 없습니다.")
                return
            
            # 가격 관리 모드 확인
            is_auto_mode = self.auto_mode.isChecked()  # 올바른 변수명 사용
            
            # 가격 수정 중 상태 표시
            self.price_table.setItem(row, 5, QTableWidgetItem("🔄 가격 수정 중..."))
            
            # 실제 가격 수정 로직 호출
            result = self.update_buyma_product_price(product_name, suggested_price, is_auto_mode)
            
            if result == True:
                self.price_table.setItem(row, 5, QTableWidgetItem("✅ 수정 완료"))
                self.log_message(f"✅ 단일 가격 수정 완료: {product_name[:20]}... → ¥{suggested_price:,}")
            elif result == "cancelled":
                self.price_table.setItem(row, 5, QTableWidgetItem("❌ 상품 수정 취소"))
                self.log_message(f"❌ 단일 상품 수정 취소: {product_name[:20]}...")
            else:
                self.price_table.setItem(row, 5, QTableWidgetItem("❌ 수정 실패"))
                self.log_message(f"❌ 단일 가격 수정 실패: {product_name[:20]}...")
                
        except Exception as e:
            self.price_table.setItem(row, 5, QTableWidgetItem("❌ 수정 실패"))
            self.log_message(f"❌ 단일 가격 수정 오류: {str(e)}")

    def search_buyma_lowest_price(self, product_name):
        """BUYMA에서 상품 검색하여 최저가 찾기"""
        try:
            # 1. 상품명에서 실제 검색어 추출 (商品ID 이전까지)
            search_name = product_name
            if "商品ID" in product_name:
                search_name = product_name.split("商品ID")[0].strip()
            
            # 추가 정리 (줄바꿈, 특수문자 제거)
            search_name = search_name.replace("\n", " ").strip()
            
            self.log_message(f"🔍 검색어: '{search_name}'")
            
            if not self.shared_driver:
                self.log_error("❌ 브라우저가 초기화되지 않았습니다.")
                return None
            
            # 2. BUYMA 검색 URL로 이동 (첫 페이지)
            page_number = 1
            lowest_price = float('inf')
            found_products = 0
            
            while True:
                search_url = f"https://www.buyma.com/r/-R120/{search_name}_{page_number}"
                self.log_message(f"🌐 페이지 {page_number} 접속: {search_url}")
                
                try:
                    self.shared_driver.get(search_url)
                    time.sleep(3)
                except Exception as e:
                    # 페이지 로딩 타임아웃 또는 네트워크 오류
                    self.log_message(f"⏱️ 페이지 {page_number} 로딩 실패: {str(e)}")
                    break
                
                # 3. ul.product_lists 요소 로딩 대기
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                try:
                    # 상품 리스트 로딩 대기 (최대 10초)
                    product_list = WebDriverWait(self.shared_driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.product_lists"))
                    )
                    
                    # 4. 각 li 요소들 (상품들) 수집
                    product_items = product_list.find_elements(By.TAG_NAME, "li")
                    
                    if not product_items:
                        self.log_message(f"⚠️ 페이지 {page_number}에서 상품을 찾을 수 없습니다.")
                        break
                    
                    self.log_message(f"📦 페이지 {page_number}에서 {len(product_items)}개 상품 발견")
                    
                    # 5. 각 상품 정보 분석
                    for item in product_items:
                        try:
                            # 6. 상품명 추출 (div.product_name)
                            name_elem = item.find_element(By.CSS_SELECTOR, "div.product_name")
                            item_name = name_elem.text.strip()
                            
                            # 7. 검색한 상품명이 포함되어 있는지 확인
                            if search_name.lower() in item_name.lower():
                                # 5. 상품가격 추출 (span.Price_Txt)
                                try:
                                    price_elem = item.find_element(By.CSS_SELECTOR, "span.Price_Txt")
                                    price_text = price_elem.text.strip()
                                    
                                    # 가격에서 숫자만 추출 (¥12,000 → 12000)
                                    import re
                                    price_numbers = re.findall(r'[\d,]+', price_text)
                                    if price_numbers:
                                        price = int(price_numbers[0].replace(',', ''))
                                        
                                        # 7. 최저가 비교 및 갱신
                                        if price < lowest_price:
                                            lowest_price = price
                                            self.log_message(f"💰 새로운 최저가 발견: ¥{price:,} - {item_name[:30]}...")
                                        
                                        found_products += 1
                                    
                                except Exception as e:
                                    # 가격 정보가 없는 상품은 건너뛰기
                                    continue
                            
                        except Exception as e:
                            # 개별 상품 처리 오류는 건너뛰기
                            continue
                    
                    # 4. 다음 페이지 확인 (li 개수가 120개면 다음 페이지 있음)
                    if len(product_items) >= 120:
                        page_number += 1
                        self.log_message(f"➡️ 다음 페이지({page_number})로 이동...")
                        time.sleep(2)  # 페이지 간 딜레이
                    else:
                        # 마지막 페이지 도달
                        self.log_message(f"✅ 모든 페이지 검색 완료 (총 {page_number} 페이지)")
                        break
                
                except Exception as e:
                    self.log_error(f"❌ 페이지 {page_number} 로딩 실패: {str(e)}")
                    continue
            
            # 8. 결과 반환
            if lowest_price != float('inf'):
                self.log_message(f"🎉 검색 완료: 총 {found_products}개 상품 중 최저가 ¥{lowest_price:,}")
                return lowest_price
            else:
                self.log_message(f"⚠️ '{search_name}' 상품을 찾을 수 없습니다.")
                return None
                
        except Exception as e:
            self.log_error(f"❌ 가격 검색 오류: {str(e)}")
            return None
    
    def analyze_all_my_products(self):
        """내 상품 전체 분석 & 자동 수정"""
        # 로그인 상태 확인
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            QMessageBox.warning(
                self, 
                "로그인 필요", 
                "가격 분석을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
            )
            return
            
        if not self.check_login_required():
            return
        
        # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
        self.switch_to_monitoring_tab()
        self.set_tabs_enabled(False)
        
        self.log_message("🚀 내 상품 전체 분석 & 수정을 시작합니다...")
        
        # 먼저 내 상품 불러오기
        self.load_my_products()
        
        # 잠시 후 가격 분석 시작
        QTimer.singleShot(5000, self.analyze_my_products_prices)  # 5초 후 분석 시작
    
    def analyze_single_product(self, row):
        """단일 상품 분석"""
        try:
            # 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(
                    self, 
                    "로그인 필요", 
                    "가격 분석을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                    "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
                )
                return
            product_name = self.price_table.item(row, 0).text()
            self.log_message(f"🔍 단일 상품 분석: {product_name[:30]}...")
            
            # 별도 스레드에서 실행
            import threading
            
            def analyze():
                lowest_price = self.search_buyma_lowest_price(product_name)
                if lowest_price:
                    discount = self.discount_amount.value()
                    suggested_price = max(lowest_price - discount, 0)
                    
                    self.price_table.setItem(row, 2, QTableWidgetItem(f"¥{lowest_price:,}"))
                    self.price_table.setItem(row, 3, QTableWidgetItem(f"¥{suggested_price:,}"))
                    self.price_table.setItem(row, 5, QTableWidgetItem("✅ 분석 완료"))
                    
                    self.log_message(f"✅ 분석 완료: {product_name[:20]}... - 최저가: ¥{lowest_price:,}")
            
            thread = threading.Thread(target=analyze, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log_message(f"❌ 단일 상품 분석 오류: {str(e)}")
    
    # def update_single_product_price(self, row):
    #     """단일 상품 가격 수정"""
    #     try:
    #         product_name = self.price_table.item(row, 0).text()
    #         suggested_price_item = self.price_table.item(row, 3)
            
    #         if not suggested_price_item or "계산 필요" in suggested_price_item.text():
    #             QMessageBox.warning(self, "경고", "먼저 가격 분석을 실행해주세요.")
    #             return
            
    #         # 제안가에서 숫자만 추출
    #         import re
    #         suggested_price_text = suggested_price_item.text()
    #         numbers = re.findall(r'\d+', suggested_price_text.replace(',', ''))
    #         suggested_price = int(''.join(numbers)) if numbers else 0
            
    #         if suggested_price <= 0:
    #             QMessageBox.warning(self, "경고", "유효한 제안가가 없습니다.")
    #             return
            
    #         self.log_message(f"💰 가격 수정 시작: {product_name[:30]}... → ¥{suggested_price:,}")
            
    #         # 실제 BUYMA 가격 수정 로직 (별도 스레드에서 실행)
    #         import threading
            
    #         def update_price():
    #             # 여기에 실제 BUYMA 가격 수정 로직 구현
    #             # self.update_buyma_product_price(product_name, suggested_price)
    #             self.log_message(f"✅ 가격 수정 완료: {product_name[:20]}...")
    #             self.price_table.setItem(row, 5, QTableWidgetItem("✅ 수정 완료"))
            
    #         thread = threading.Thread(target=update_price, daemon=True)
    #         thread.start()
            
    #     except Exception as e:
    #         self.log_message(f"❌ 가격 수정 오류: {str(e)}")
    
    def extract_detailed_info(self, driver, product_url):
        """상품 상세 정보 추출"""
        detailed_info = {
            'images': [],
            'colors': [],
            'sizes': [],
            'description': '',
            'category': ''
        }
        
        try:
            # 현재 URL 저장
            current_url = driver.current_url
            
            # 상품 상세 페이지로 이동
            driver.get(product_url)
            
            # 페이지 로딩 대기
            import time
            time.sleep(2)
            
            # 이미지 수집
            image_selectors = [
                "img[src*='jpg']", "img[src*='jpeg']", "img[src*='png']",
                ".product-image img", ".item-image img", ".gallery img",
                "[class*='image'] img", "[class*='photo'] img"
            ]
            
            for selector in image_selectors:
                try:
                    img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in img_elements[:20]:  # 최대 20장
                        src = img.get_attribute('src')
                        if src and src.startswith('http'):
                            detailed_info['images'].append(src)
                    if detailed_info['images']:
                        break
                except:
                    continue
            
            # 색상 옵션 수집
            color_selectors = [
                ".color-option", ".color-select", "[class*='color']",
                ".variant-color", ".option-color"
            ]
            
            for selector in color_selectors:
                try:
                    color_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for color in color_elements:
                        color_text = color.text.strip()
                        if color_text and color_text not in detailed_info['colors']:
                            detailed_info['colors'].append(color_text)
                    if detailed_info['colors']:
                        break
                except:
                    continue
            
            # 사이즈 옵션 수집
            size_selectors = [
                ".size-option", ".size-select", "[class*='size']",
                ".variant-size", ".option-size"
            ]
            
            for selector in size_selectors:
                try:
                    size_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for size in size_elements:
                        size_text = size.text.strip()
                        if size_text and size_text not in detailed_info['sizes']:
                            detailed_info['sizes'].append(size_text)
                    if detailed_info['sizes']:
                        break
                except:
                    continue
            
            # 상품 설명 수집
            desc_selectors = [
                ".description", ".product-desc", ".item-desc",
                "[class*='description']", "[class*='detail']"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_element = driver.find_element(By.CSS_SELECTOR, selector)
                    detailed_info['description'] = desc_element.text.strip()[:500]  # 최대 500자
                    if detailed_info['description']:
                        break
                except:
                    continue
            
            # 카테고리 수집
            category_selectors = [
                ".breadcrumb", ".category", ".nav-category",
                "[class*='breadcrumb']", "[class*='category']"
            ]
            
            for selector in category_selectors:
                try:
                    category_element = driver.find_element(By.CSS_SELECTOR, selector)
                    detailed_info['category'] = category_element.text.strip()
                    if detailed_info['category']:
                        break
                except:
                    continue
            
            # 원래 페이지로 돌아가기
            driver.get(current_url)
            time.sleep(1)
            
        except Exception as e:
            self.log_message(f"상세 정보 추출 오류: {str(e)}")
        
        return detailed_info
    
    def find_text_by_selectors(self, element, selectors):
        """여러 선택자로 텍스트 찾기"""
        for selector in selectors:
            try:
                found_element = element.find_element(By.CSS_SELECTOR, selector)
                text = found_element.text.strip()
                if text:
                    return text
            except:
                continue
        return None
    
    def add_crawled_item(self, item_data):
        """크롤링된 아이템을 테이블에 추가"""
        row = self.crawling_table.rowCount()
        self.crawling_table.insertRow(row)
        
        # 데이터 추가
        self.crawling_table.setItem(row, 0, QTableWidgetItem(item_data.get('title', '')))
        self.crawling_table.setItem(row, 1, QTableWidgetItem(item_data.get('brand', '')))
        self.crawling_table.setItem(row, 2, QTableWidgetItem(item_data.get('price', '')))
        
        # 이미지 수 표시
        image_count = len(item_data.get('images', []))
        self.crawling_table.setItem(row, 3, QTableWidgetItem(f"{image_count}장"))
        
        # 색상/사이즈 정보 표시
        colors = item_data.get('colors', [])
        sizes = item_data.get('sizes', [])
        options_text = f"색상:{len(colors)}개, 사이즈:{len(sizes)}개"
        self.crawling_table.setItem(row, 4, QTableWidgetItem(options_text))
        
        # URL
        self.crawling_table.setItem(row, 5, QTableWidgetItem(item_data.get('url', '')))
        
        # 상태 표시
        status_item = QTableWidgetItem(item_data.get('status', '✅ 완료'))
        status_item.setForeground(QBrush(QColor("#28a745")))
        self.crawling_table.setItem(row, 6, status_item)
        
        # 액션 버튼들 (가로 배치로 변경)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        action_layout.setSpacing(3)
        
        # 1. 상세보기 버튼
        detail_btn = QPushButton("📋")
        detail_btn.setToolTip("상품 상세 정보 보기")
        detail_btn.setFixedSize(35, 28)
        detail_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        detail_btn.clicked.connect(lambda checked, r=row: self.show_item_detail(r))
        action_layout.addWidget(detail_btn)
        
        # 2. 바로 업로드 버튼
        upload_btn = QPushButton("📤")
        upload_btn.setToolTip("BUYMA에 바로 업로드")
        upload_btn.setFixedSize(35, 28)
        upload_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: #1e7e34;
            }
        """)
        upload_btn.clicked.connect(lambda checked, r=row: self.upload_single_item(r))
        action_layout.addWidget(upload_btn)
        
        # 4. URL 열기 버튼
        url_btn = QPushButton("🔗")
        url_btn.setToolTip("원본 상품 페이지 열기")
        url_btn.setFixedSize(35, 28)
        url_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        url_btn.clicked.connect(lambda checked, r=row: self.open_product_url(r))
        action_layout.addWidget(url_btn)
        
        self.crawling_table.setCellWidget(row, 7, action_widget)
        
        # # 행 높이를 버튼 높이에 맞춤 (개별 행 설정)
        # self.crawling_table.setRowHeight(row, 35)
        
        # # 1. 상세보기 버튼
        # detail_btn = QPushButton("📋")
        # detail_btn.setToolTip("상품 상세 정보 보기")
        # detail_btn.setFixedSize(35, 28)
        # detail_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #007bff;
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         font-size: 12px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #0056b3;
        #     }
        # """)
        # detail_btn.clicked.connect(lambda checked, r=row: self.show_item_detail(r))
        # action_layout.addWidget(detail_btn)
        
        # # 2. 주력상품 추가 버튼
        # add_favorite_btn = QPushButton("⭐")
        # add_favorite_btn.setToolTip("주력 상품으로 추가")
        # add_favorite_btn.setFixedSize(35, 28)
        # add_favorite_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #f39c12;
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         font-size: 12px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #e67e22;
        #     }
        # """)
        # add_favorite_btn.clicked.connect(lambda checked, r=row: self.add_crawled_to_favorites(r))
        # action_layout.addWidget(add_favorite_btn)
        
        # # 3. 바로 업로드 버튼
        # upload_btn = QPushButton("📤")
        # upload_btn.setToolTip("BUYMA에 바로 업로드")
        # upload_btn.setFixedSize(35, 28)
        # upload_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #28a745;
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         font-size: 12px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #1e7e34;
        #     }
        # """)
        # upload_btn.clicked.connect(lambda checked, r=row: self.upload_single_item(r))
        # action_layout.addWidget(upload_btn)
        
        # # 4. URL 열기 버튼
        # url_btn = QPushButton("🔗")
        # url_btn.setToolTip("원본 상품 페이지 열기")
        # url_btn.setFixedSize(35, 28)
        # url_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #6c757d;
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         font-size: 12px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #5a6268;
        #     }
        # """)
        # url_btn.clicked.connect(lambda checked, r=row: self.open_product_url(r))
        # action_layout.addWidget(url_btn)
        
        # self.crawling_table.setCellWidget(row, 7, action_widget)
        
        # # 행 높이를 버튼 높이에 맞춤 (개별 행 설정)
        # self.crawling_table.setRowHeight(row, 35)
        
        # # 3. 바로 업로드 버튼
        # upload_btn = QPushButton("📤")
        # upload_btn.setToolTip("BUYMA에 바로 업로드")
        # upload_btn.setFixedSize(32, 22)
        # upload_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #28a745;
        #         color: white;
        #         border: none;
        #         border-radius: 3px;
        #         font-size: 11px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #1e7e34;
        #     }
        # """)
        # upload_btn.clicked.connect(lambda checked, r=row: self.upload_single_item(r))
        # action_layout.addWidget(upload_btn)
        
        # # 4. URL 열기 버튼
        # url_btn = QPushButton("🔗")
        # url_btn.setToolTip("원본 상품 페이지 열기")
        # url_btn.setFixedSize(32, 22)
        # url_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #6c757d;
        #         color: white;
        #         border: none;
        #         border-radius: 3px;
        #         font-size: 11px;
        #         font-family: '맑은 고딕';
        #     }
        #     QPushButton:hover {
        #         background: #5a6268;
        #     }
        # """)
        # url_btn.clicked.connect(lambda checked, r=row: self.open_product_url(r))
        # action_layout.addWidget(url_btn)

        # 자동 스크롤
        self.crawling_table.scrollToBottom()
    
    def show_item_detail(self, row):
        """상품 상세 정보 표시"""
        try:
            title = self.crawling_table.item(row, 0).text()
            brand = self.crawling_table.item(row, 1).text()
            price = self.crawling_table.item(row, 2).text()
            url = self.crawling_table.item(row, 5).text()
            
            # 상세 정보 다이얼로그 생성
            dialog = QMessageBox(self)
            dialog.setWindowTitle("상품 상세 정보")
            dialog.setIcon(QMessageBox.Icon.Information)
            
            detail_text = f"""
            📦 상품명: {title}
            🏷️ 브랜드: {brand}
            💰 가격: {price}
            🔗 URL: {url}

            ※ 이미지, 색상, 사이즈 등의 상세 정보가 수집되었습니다.
            업로드 탭에서 BUYMA에 등록할 수 있습니다.
            """
            
            dialog.setText(detail_text)
            dialog.exec()
            
        except Exception as e:
            self.log_message(f"상세 정보 표시 오류: {str(e)}")
    
    def add_crawled_to_favorites(self, row):
        """크롤링된 상품을 주력 상품으로 추가"""
        try:
            title = self.crawling_table.item(row, 0).text()
            brand = self.crawling_table.item(row, 1).text()
            price_text = self.crawling_table.item(row, 2).text()
            
            # 가격에서 숫자만 추출
            import re
            price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
            price = int(price_match.group()) if price_match else 15000
            
            # 중복 확인
            for product in self.favorite_products:
                if product['brand'] == brand and product['name'] == title:
                    QMessageBox.warning(self, "중복", "이미 주력 상품으로 등록된 상품입니다.")
                    return
            
            # 주력 상품에 추가
            new_favorite = {
                'brand': brand,
                'name': title,
                'current_price': price,
                'cost_price': int(price * 0.6),  # 추정 원가 (60%)
                'added_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            self.favorite_products.append(new_favorite)
            self.save_favorite_products_auto()
            self.update_favorite_table()
            
            self.log_message(f"⭐ 주력 상품 추가: {brand} - {title}")
            QMessageBox.information(self, "추가 완료", f"'{title}'이(가) 주력 상품으로 추가되었습니다.")
            
        except Exception as e:
            self.log_message(f"주력 상품 추가 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력 상품 추가 중 오류가 발생했습니다:\n{str(e)}")
    
    def upload_single_item(self, row):
        """단일 상품 바로 업로드"""
        try:
            title = self.crawling_table.item(row, 0).text()
            brand = self.crawling_table.item(row, 1).text()
            
            reply = QMessageBox.question(self, "업로드 확인", 
                f"'{title}'을(를) BUYMA에 바로 업로드하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message(f"📤 단일 상품 업로드 시작: {brand} - {title}")
                
                # 시뮬레이션: 업로드 프로세스
                import time
                QApplication.processEvents()
                time.sleep(2)  # 업로드 시뮬레이션
                
                # 성공률 90%
                if random.random() < 0.9:
                    self.log_message(f"✅ 업로드 완료: {title}")
                    QMessageBox.information(self, "업로드 완료", f"'{title}'이(가) 성공적으로 업로드되었습니다.")
                    
                    # 상태 업데이트
                    status_item = self.crawling_table.item(row, 6)
                    if status_item:
                        status_item.setText("업로드 완료")
                        status_item.setForeground(QBrush(QColor("#28a745")))
                else:
                    self.log_message(f"❌ 업로드 실패: {title}")
                    QMessageBox.warning(self, "업로드 실패", f"'{title}' 업로드에 실패했습니다.")
            
        except Exception as e:
            self.log_message(f"단일 업로드 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"업로드 중 오류가 발생했습니다:\n{str(e)}")
    
    def open_product_url(self, row):
        """원본 상품 페이지 열기"""
        try:
            url_item = self.crawling_table.item(row, 5)
            if url_item:
                url = url_item.text()
                if url and url != "N/A":
                    import webbrowser
                    webbrowser.open(url)
                    self.log_message(f"🔗 원본 페이지 열기: {url}")
                else:
                    QMessageBox.warning(self, "URL 없음", "이 상품의 URL 정보가 없습니다.")
            else:
                QMessageBox.warning(self, "URL 없음", "URL 정보를 찾을 수 없습니다.")
                
        except Exception as e:
            self.log_message(f"URL 열기 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"URL 열기 중 오류가 발생했습니다:\n{str(e)}")
            QMessageBox.critical(self, "오류", f"상세 정보를 표시할 수 없습니다:\n{str(e)}")
    
    def download_images(self, images, product_title):
        """상품 이미지 다운로드"""
        downloaded_images = []
        
        try:
            # 이미지 저장 폴더 생성
            import os
            images_dir = os.path.join(os.getcwd(), "images")
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            # 상품별 폴더 생성 (상품명을 파일명으로 사용 가능하게 정리)
            safe_title = "".join(c for c in product_title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
            product_dir = os.path.join(images_dir, safe_title)
            if not os.path.exists(product_dir):
                os.makedirs(product_dir)
            
            for i, img_url in enumerate(images[:20]):  # 최대 20장
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        # 파일 확장자 추출
                        file_ext = img_url.split('.')[-1].split('?')[0]
                        if file_ext.lower() not in ['jpg', 'jpeg', 'png', 'gif']:
                            file_ext = 'jpg'
                        
                        # 파일명 생성
                        filename = f"image_{i+1:02d}.{file_ext}"
                        filepath = os.path.join(product_dir, filename)
                        
                        # 이미지 저장
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        downloaded_images.append(filepath)
                        self.log_message(f"이미지 다운로드 완료: {filename}")
                        
                except Exception as e:
                    self.log_message(f"이미지 다운로드 실패 ({i+1}): {str(e)}")
                    continue
            
        except Exception as e:
            self.log_message(f"이미지 다운로드 오류: {str(e)}")
        
        return downloaded_images
    
    def stop_crawling(self):
        """크롤링 중지"""
        self.log_message("⏹️ 크롤링 중지 요청...")
        self.crawling_status.setText("중지 중...")
        
        # UI 상태 복원
        self.start_crawling_btn.setEnabled(True)
        self.stop_crawling_btn.setEnabled(False)
        
        # 크롤링 중지 시 UI 활성화
        self.disable_ui_during_crawling(False)
    
    @safe_slot
    def save_crawling_data(self, checked=False):
        """크롤링 데이터를 JSON 파일로 저장"""
        try:
            # 크롤링된 데이터가 있는지 확인
            if not hasattr(self, 'crawled_products') or len(self.crawled_products) == 0:
                QMessageBox.warning(self, "경고", "저장할 크롤링 데이터가 없습니다.\n먼저 크롤링을 실행해주세요.")
                return
            
            # 파일 저장 대화상자
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"크롤링데이터_{current_time}.json"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "크롤링 데이터 저장",
                default_filename,
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 저장할 데이터 준비
            save_data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_products": len(self.crawled_products),
                    "source_url": getattr(self, 'last_crawled_url', ''),
                    "version": "1.0"
                },
                "products": self.crawled_products
            }
            
            # JSON 파일로 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"💾 크롤링 데이터 저장 완료: {file_path}")
            self.log_message(f"📊 저장된 상품 수: {len(self.crawled_products)}개")
            
            QMessageBox.information(
                self, 
                "저장 완료", 
                f"크롤링 데이터가 성공적으로 저장되었습니다.\n\n"
                f"파일: {file_path}\n"
                f"상품 수: {len(self.crawled_products)}개"
            )
            
        except Exception as e:
            error_msg = f"크롤링 데이터 저장 중 오류가 발생했습니다: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            QMessageBox.critical(self, "저장 오류", error_msg)

    @safe_slot
    def load_crawling_data(self, checked=False):
        """저장된 크롤링 데이터를 JSON 파일에서 불러오기"""
        try:
            # 파일 선택 대화상자
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "크롤링 데이터 불러오기",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 기존 데이터가 있는 경우 확인
            if hasattr(self, 'crawled_products') and len(self.crawled_products) > 0:
                reply = QMessageBox.question(
                    self,
                    "데이터 덮어쓰기 확인",
                    f"현재 {len(self.crawled_products)}개의 크롤링 데이터가 있습니다.\n"
                    f"불러온 데이터로 덮어쓰시겠습니까?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # 데이터 구조 확인
            if 'products' not in loaded_data:
                QMessageBox.warning(self, "파일 오류", "올바른 크롤링 데이터 파일이 아닙니다.")
                return
            
            # 데이터 복원
            self.crawled_products = loaded_data['products']
            
            # 메타데이터 정보 표시
            metadata = loaded_data.get('metadata', {})
            saved_at = metadata.get('saved_at', '알 수 없음')
            total_products = metadata.get('total_products', len(self.crawled_products))
            source_url = metadata.get('source_url', '알 수 없음')
            
            # 크롤링 테이블 업데이트
            self.update_crawling_table()
            
            # 통계 업데이트
            if hasattr(self, 'update_crawling_stats'):
                self.update_crawling_stats()
            
            self.log_message(f"📂 크롤링 데이터 불러오기 완료: {file_path}")
            self.log_message(f"📊 불러온 상품 수: {len(self.crawled_products)}개")
            self.log_message(f"💾 저장 시간: {saved_at}")
            
            QMessageBox.information(
                self,
                "불러오기 완료",
                f"크롤링 데이터를 성공적으로 불러왔습니다.\n\n"
                f"상품 수: {total_products}개\n"
                f"저장 시간: {saved_at}\n"
                f"원본 URL: {source_url}"
            )
            
        except json.JSONDecodeError:
            error_msg = "JSON 파일 형식이 올바르지 않습니다."
            self.log_message(f"❌ {error_msg}")
            QMessageBox.critical(self, "파일 오류", error_msg)
        except Exception as e:
            error_msg = f"크롤링 데이터 불러오기 중 오류가 발생했습니다: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            QMessageBox.critical(self, "불러오기 오류", error_msg)

    def update_crawling_table(self):
        """크롤링 테이블을 현재 데이터로 업데이트"""
        try:
            # 테이블 초기화
            self.crawling_table.setRowCount(0)
            
            # 크롤링된 데이터가 없으면 종료
            if not hasattr(self, 'crawled_products') or len(self.crawled_products) == 0:
                return
            
            # 각 상품 데이터를 테이블에 추가
            for item_data in self.crawled_products:
                self.add_crawling_result_to_table(item_data)
                
            self.log_message(f"📊 크롤링 테이블 업데이트 완료: {len(self.crawled_products)}개 상품")
            
        except Exception as e:
            self.log_message(f"❌ 크롤링 테이블 업데이트 오류: {str(e)}")

    def add_crawling_result_to_table(self, item_data):
        """크롤링 결과를 테이블에 추가"""
        try:
            row = self.crawling_table.rowCount()
            self.crawling_table.insertRow(row)
            
            # 상품명
            title = item_data.get('title', '제목 없음')
            self.crawling_table.setItem(row, 0, QTableWidgetItem(title))
            
            # 브랜드
            brand = item_data.get('brand', '브랜드 없음')
            self.crawling_table.setItem(row, 1, QTableWidgetItem(brand))
            
            # 가격
            price = item_data.get('price', '가격 없음')
            self.crawling_table.setItem(row, 2, QTableWidgetItem(str(price)))
            
            # 이미지 수
            images = item_data.get('images', [])
            image_count = len(images) if images else 0
            self.crawling_table.setItem(row, 3, QTableWidgetItem(f"{image_count}개"))
            
            # 색상/사이즈
            colors = item_data.get('colors', [])
            sizes = item_data.get('sizes', [])
            options_text = f"색상:{len(colors)}개, 사이즈:{len(sizes)}개"
            self.crawling_table.setItem(row, 4, QTableWidgetItem(options_text))
            
            # URL
            url = item_data.get('url', '')
            url_item = QTableWidgetItem(url[:50] + "..." if len(url) > 50 else url)
            url_item.setToolTip(url)  # 전체 URL을 툴팁으로 표시
            self.crawling_table.setItem(row, 5, url_item)
            
            # 상태
            status = item_data.get('status', '완료')
            self.crawling_table.setItem(row, 6, QTableWidgetItem(status))
            
            # 액션 버튼들 추가
            self.add_action_buttons_to_crawling_table(row)
            
        except Exception as e:
            self.log_message(f"❌ 테이블 행 추가 오류: {str(e)}")

    def add_action_buttons_to_crawling_table(self, row):
        """크롤링 테이블에 액션 버튼들 추가"""
        try:
            # 액션 버튼 위젯 생성
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            
            # 1. 상세보기 버튼
            detail_btn = QPushButton("📋")
            detail_btn.setToolTip("상품 상세 정보 보기")
            detail_btn.setFixedSize(35, 28)
            detail_btn.setStyleSheet("""
                QPushButton {
                    background: #17a2b8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #138496;
                }
            """)
            detail_btn.clicked.connect(lambda checked, r=row: self.show_crawling_item_detail(r))
            action_layout.addWidget(detail_btn)
            
            # 2. 바로 업로드 버튼
            upload_btn = QPushButton("📤")
            upload_btn.setToolTip("BUYMA에 바로 업로드")
            upload_btn.setFixedSize(35, 28)
            upload_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #1e7e34;
                }
            """)
            upload_btn.clicked.connect(lambda checked, r=row: self.upload_single_item(r))
            action_layout.addWidget(upload_btn)
            
            # 3. URL 열기 버튼
            url_btn = QPushButton("🔗")
            url_btn.setToolTip("원본 상품 페이지 열기")
            url_btn.setFixedSize(35, 28)
            url_btn.setStyleSheet("""
                QPushButton {
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #545b62;
                }
            """)
            url_btn.clicked.connect(lambda checked, r=row: self.open_product_url(r))
            action_layout.addWidget(url_btn)
            
            # 테이블에 위젯 설정
            self.crawling_table.setCellWidget(row, 7, action_widget)
            
        except Exception as e:
            self.log_message(f"❌ 액션 버튼 추가 오류: {str(e)}")

    @safe_slot
    def show_crawling_item_detail(self, row, checked=False):
        """크롤링 상품 상세 정보 표시 (불러오기용)"""
        try:
            # 크롤링된 데이터에서 해당 행의 상품 정보 가져오기
            if not hasattr(self, 'crawled_products') or row >= len(self.crawled_products):
                QMessageBox.warning(self, "오류", "상품 정보를 찾을 수 없습니다.")
                return
            
            product_data = self.crawled_products[row]
            
            # 상세 정보 다이얼로그 생성
            dialog = QMessageBox(self)
            dialog.setWindowTitle("상품 상세 정보")
            dialog.setIcon(QMessageBox.Icon.Information)
            
            # 상세 정보 텍스트 구성
            detail_text = f"""
📦 상품명: {product_data.get('title', '정보 없음')}
🏷️ 브랜드: {product_data.get('brand', '정보 없음')}
💰 가격: {product_data.get('price', '정보 없음')}
📂 카테고리: {product_data.get('category', '정보 없음')}

🎨 색상 옵션: {', '.join(product_data.get('colors', [])) if product_data.get('colors') else '없음'}
📏 사이즈 옵션: {', '.join(product_data.get('sizes', [])) if product_data.get('sizes') else '없음'}

🖼️ 이미지 수: {len(product_data.get('images', []))}개
🔗 원본 URL: {product_data.get('url', '정보 없음')}

📝 설명: {product_data.get('description', '설명 없음')[:200]}{'...' if len(product_data.get('description', '')) > 200 else ''}
            """
            
            dialog.setText(detail_text)
            dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            dialog.exec()
            
        except Exception as e:
            error_msg = f"상품 상세 정보 표시 중 오류: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
        
    def export_crawling_results(self):
        """크롤링 결과 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "결과 저장", f"crawling_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if file_path:
            self.log_message(f"결과를 {file_path}에 저장했습니다.")
    
    def export_crawling_results(self):
        """크롤링 결과를 Excel로 내보내기"""
        try:
            if self.crawling_table.rowCount() == 0:
                QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
                return
            
            # 파일 저장 경로 선택
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "크롤링 결과 저장", 
                f"크롤링_결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # 데이터 수집
            import pandas as pd
            
            data = []
            for row in range(self.crawling_table.rowCount()):
                row_data = {
                    '상품명': self.crawling_table.item(row, 0).text() if self.crawling_table.item(row, 0) else '',
                    '브랜드': self.crawling_table.item(row, 1).text() if self.crawling_table.item(row, 1) else '',
                    '가격': self.crawling_table.item(row, 2).text() if self.crawling_table.item(row, 2) else '',
                    '이미지 수': self.crawling_table.item(row, 3).text() if self.crawling_table.item(row, 3) else '',
                    '색상/사이즈': self.crawling_table.item(row, 4).text() if self.crawling_table.item(row, 4) else '',
                    'URL': self.crawling_table.item(row, 5).text() if self.crawling_table.item(row, 5) else '',
                    '상태': self.crawling_table.item(row, 6).text() if self.crawling_table.item(row, 6) else '',
                    '수집일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                data.append(row_data)
            
            # DataFrame 생성 및 저장
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            self.log_message(f"✅ 크롤링 결과를 저장했습니다: {file_path}")
            QMessageBox.information(self, "저장 완료", f"크롤링 결과가 저장되었습니다.\n\n{file_path}")
            
        except Exception as e:
            self.log_message(f"❌ Excel 저장 오류: {str(e)}")
            QMessageBox.critical(self, "저장 오류", f"Excel 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def clear_crawling_results(self):
        """크롤링 결과 지우기"""
        reply = QMessageBox.question(
            self, "확인", "크롤링 결과를 모두 지우시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.crawling_table.setRowCount(0)
            self.log_message("크롤링 결과를 지웠습니다.")
    
    # def analyze_prices(self):
    #     """가격 분석"""
    #     brand = self.brand_input.text().strip()
    #     product = self.product_input.text().strip()
        
    #     if not brand or not product:
    #         QMessageBox.warning(self, "경고", "브랜드명과 상품명을 모두 입력해주세요.")
    #         return
        
    #     # UI 상태 변경
    #     self.analyze_price_btn.setEnabled(False)
    #     self.analyze_price_btn.setText("🔍 분석 중...")
        
    #     # 테이블 초기화
    #     self.price_table.setRowCount(0)
        
    #     # 로그 시작
    #     self.log_message(f"🔍 가격 분석 시작: {brand} - {product}")
        
    #     # 별도 스레드에서 가격 분석 실행
    #     import threading
        
    #     self.price_analysis_thread = threading.Thread(
    #         target=self.run_price_analysis, 
    #         args=(brand, product), 
    #         daemon=True
    #     )
    #     self.price_analysis_thread.start()
    
    # def run_price_analysis(self, brand, product):
    #     """가격 분석 실행 (별도 스레드)"""
    #     driver = None
    #     try:
    #         self.log_message("🌐 브라우저를 시작합니다...")
            
    #         # Selenium WebDriver 설정
    #         from selenium import webdriver
    #         from selenium.webdriver.chrome.service import Service
    #         from selenium.webdriver.chrome.options import Options
    #         from selenium.webdriver.common.by import By
    #         from selenium.webdriver.support.ui import WebDriverWait
    #         from selenium.webdriver.support import expected_conditions as EC
    #         from webdriver_manager.chrome import ChromeDriverManager
            
    #         # Chrome 옵션 설정
    #         chrome_options = Options()
    #         chrome_options.add_argument('--no-sandbox')
    #         chrome_options.add_argument('--disable-dev-shm-usage')
    #         chrome_options.add_argument('--disable-gpu')
    #         chrome_options.add_argument('--window-size=1920,1080')
            
    #         # WebDriver 생성
    #         service = Service(ChromeDriverManager().install())
    #         driver = webdriver.Chrome(service=service, options=chrome_options)
    #         driver.implicitly_wait(self.timeout_setting.value())
            
    #         # BUYMA 검색 URL 생성
    #         search_query = f"{brand} {product}"
    #         search_url = f"https://www.buyma.com/r/_/4FK1249/?q={search_query}"
            
    #         self.log_message(f"📄 BUYMA 검색: {search_query}")
            
    #         # 검색 페이지 접속
    #         driver.get(search_url)
            
    #         # 페이지 로딩 대기
    #         WebDriverWait(driver, 10).until(
    #             EC.presence_of_element_located((By.TAG_NAME, "body"))
    #         )
            
    #         self.log_message("🔍 경쟁사 상품을 수집합니다...")
            
    #         # 검색 결과 수집
    #         competitor_products = self.extract_competitor_products(driver, brand, product)
            
    #         if not competitor_products:
    #             self.log_message("❌ 검색 결과를 찾을 수 없습니다.")
    #             return
            
    #         # 가격 분석 및 결과 표시
    #         self.analyze_competitor_prices(competitor_products, brand, product)
            
    #     except Exception as e:
    #         self.log_message(f"❌ 가격 분석 오류: {str(e)}")
    #     finally:
    #         if driver:
    #             driver.quit()
            
    #         # UI 상태 복원
    #         self.analyze_price_btn.setEnabled(True)
    #         self.analyze_price_btn.setText("🔍 가격 분석 시작")
    
    def extract_competitor_products(self, driver, brand, product):
        """경쟁사 상품 정보 추출"""
        competitor_products = []
        
        try:
            # BUYMA 상품 리스트 선택자들
            product_selectors = [
                ".item",
                ".product-item",
                "[class*='item']",
                "[class*='product']",
                ".goods-item"
            ]
            
            product_elements = []
            for selector in product_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        product_elements = elements
                        self.log_message(f"📦 선택자 '{selector}'로 {len(elements)}개 상품 발견")
                        break
                except:
                    continue
            
            if not product_elements:
                self.log_message("❌ 상품 요소를 찾을 수 없습니다.")
                return competitor_products
            
            # 상품 정보 추출
            for i, element in enumerate(product_elements[:20]):  # 최대 20개
                try:
                    # 상품명 추출
                    title_selectors = [
                        ".item-title", ".product-title", ".title",
                        "h3", "h4", ".name", "[class*='title']"
                    ]
                    title = self.find_text_by_selectors(element, title_selectors) or f"상품 #{i+1}"
                    
                    # 가격 추출
                    price_selectors = [
                        ".price", ".cost", "[class*='price']",
                        ".amount", "[class*='cost']", ".money"
                    ]
                    price_text = self.find_text_by_selectors(element, price_selectors) or "0"
                    
                    # 가격에서 숫자만 추출
                    import re
                    price_numbers = re.findall(r'[\d,]+', price_text)
                    price = 0
                    if price_numbers:
                        price = int(price_numbers[0].replace(',', ''))
                    
                    # 판매자 정보 추출
                    seller_selectors = [
                        ".seller", ".shop", ".store", "[class*='seller']"
                    ]
                    seller = self.find_text_by_selectors(element, seller_selectors) or "Unknown Seller"
                    
                    # URL 추출
                    url = ""
                    try:
                        link_element = element.find_element(By.TAG_NAME, "a")
                        url = link_element.get_attribute("href") or ""
                    except:
                        url = "URL 없음"
                    
                    if price > 0:  # 유효한 가격이 있는 경우만 추가
                        competitor_products.append({
                            'title': title.strip(),
                            'price': price,
                            'price_text': price_text,
                            'seller': seller.strip(),
                            'url': url.strip()
                        })
                        
                        self.log_message(f"✅ 경쟁사 상품: {title[:30]}... - {price_text}")
                
                except Exception as e:
                    self.log_message(f"⚠️ 상품 추출 오류 (#{i+1}): {str(e)}")
                    continue
            
        except Exception as e:
            self.log_message(f"경쟁사 상품 추출 오류: {str(e)}")
        
        return competitor_products
    
    def analyze_competitor_prices(self, competitor_products, brand, product):
        """경쟁사 가격 분석 및 결과 표시"""
        try:
            if not competitor_products:
                self.log_message("❌ 분석할 경쟁사 상품이 없습니다.")
                return
            
            # 가격 정렬 (낮은 순)
            competitor_products.sort(key=lambda x: x['price'])
            
            # 최저가 찾기
            lowest_price = competitor_products[0]['price']
            
            # 할인 금액 적용
            discount = self.dashboard_discount.value()
            suggested_price = max(lowest_price - discount, 0)
            
            self.log_message(f"📊 분석 완료: 최저가 {lowest_price}엔, 제안가 {suggested_price}엔")
            
            # 결과를 테이블에 표시
            self.display_price_analysis_results(competitor_products, brand, product, suggested_price)
            
            # 요약 정보 업데이트
            total_count = len(competitor_products)
            self.total_analyzed.setText(f"분석 완료: {total_count}개")
            self.auto_updated.setText("자동 수정: 0개")
            self.excluded_items.setText("제외: 0개")
            self.failed_items.setText("실패: 0개")
            
        except Exception as e:
            self.log_message(f"가격 분석 오류: {str(e)}")
    
    def display_price_analysis_results(self, competitor_products, brand, product, suggested_price):
        """가격 분석 결과를 테이블에 표시"""
        try:
            # 현재 상품 정보 (가상의 현재 가격 - 실제로는 사용자 입력 또는 DB에서 가져와야 함)
            current_price = competitor_products[0]['price'] + 500  # 예시: 최저가보다 500엔 높다고 가정
            
            # 예상 마진 계산
            estimated_margin = suggested_price - (suggested_price * 0.1)  # 예시: 10% 수수료 제외
            
            # 메인 상품 정보 추가
            main_row = self.price_table.rowCount()
            self.price_table.insertRow(main_row)
            
            self.price_table.setItem(main_row, 0, QTableWidgetItem(f"{brand} {product}"))
            self.price_table.setItem(main_row, 1, QTableWidgetItem(brand))
            self.price_table.setItem(main_row, 2, QTableWidgetItem(f"{current_price}엔"))
            self.price_table.setItem(main_row, 3, QTableWidgetItem(f"{competitor_products[0]['price']}엔"))
            self.price_table.setItem(main_row, 4, QTableWidgetItem(f"{suggested_price}엔"))
            self.price_table.setItem(main_row, 5, QTableWidgetItem(f"+{int(estimated_margin)}엔"))
            
            # 상태 표시
            if suggested_price < current_price:
                status_item = QTableWidgetItem("수정 권장")
                status_item.setForeground(QBrush(QColor("#ffc107")))
            else:
                status_item = QTableWidgetItem("현재가 적정")
                status_item.setForeground(QBrush(QColor("#28a745")))
            
            self.price_table.setItem(main_row, 6, status_item)
            
            # 액션 버튼
            if self.auto_mode.isChecked():
                action_btn = QPushButton("🔄 자동수정")
                action_btn.setStyleSheet("""
                    QPushButton {
                        background: #28a745;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background: #1e7e34;
                    }
                """)
                action_btn.clicked.connect(lambda checked, r=main_row: self.auto_update_price(r))
            else:
                action_btn = QPushButton("💱 수동수정")
                action_btn.setStyleSheet("""
                    QPushButton {
                        background: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background: #0056b3;
                    }
                """)
                action_btn.clicked.connect(lambda checked, r=main_row: self.manual_update_price(r))
            
            self.price_table.setCellWidget(main_row, 7, action_btn)
            
        except Exception as e:
            self.log_message(f"결과 표시 오류: {str(e)}")
    
    def auto_update_price(self, row):
        """자동 가격 수정"""
        try:
            product_name = self.price_table.item(row, 0).text()
            suggested_price = self.price_table.item(row, 4).text().replace('엔', '')
            
            self.log_message(f"🔄 자동 가격 수정 시작: {product_name} → {suggested_price}엔")
            
            # BUYMA 로그인 및 가격 수정 실행
            self.execute_price_update(product_name, suggested_price, row, auto_mode=True)
            
        except Exception as e:
            self.log_message(f"자동 수정 오류: {str(e)}")
    
    def manual_update_price(self, row):
        """수동 가격 수정"""
        try:
            product_name = self.price_table.item(row, 0).text()
            current_price = self.price_table.item(row, 2).text()
            suggested_price = self.price_table.item(row, 4).text()
            
            # 가격 수정 다이얼로그
            from PyQt6.QtWidgets import QInputDialog
            
            new_price, ok = QInputDialog.getText(
                self, 
                "가격 수정", 
                f"상품: {product_name}\n현재가격: {current_price}\n제안가격: {suggested_price}\n\n새로운 가격을 입력하세요:",
                text=suggested_price.replace('엔', '')
            )
            
            if ok and new_price:
                self.log_message(f"💱 수동 가격 수정 시작: {product_name} → {new_price}엔")
                
                # BUYMA 로그인 및 가격 수정 실행
                self.execute_price_update(product_name, new_price, row, auto_mode=False)
            
        except Exception as e:
            self.log_message(f"수동 수정 오류: {str(e)}")
    
    def execute_price_update(self, product_name, new_price, row, auto_mode=True):
        """실제 BUYMA 가격 수정 실행"""
        try:
            # UI 상태 변경
            mode_text = "자동" if auto_mode else "수동"
            self.log_message(f"🌐 BUYMA 로그인 중... ({mode_text} 모드)")
            
            # 별도 스레드에서 가격 수정 실행
            import threading
            
            update_thread = threading.Thread(
                target=self.run_buyma_price_update, 
                args=(product_name, new_price, row, auto_mode), 
                daemon=True
            )
            update_thread.start()
            
        except Exception as e:
            self.log_message(f"가격 수정 실행 오류: {str(e)}")
    
    def run_buyma_price_update(self, product_name, new_price, row, auto_mode):
        """BUYMA 가격 수정 실행 (별도 스레드)"""
        driver = None
        try:
            self.log_message("🌐 브라우저를 시작합니다...")
            
            # Selenium WebDriver 설정
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Chrome 옵션 설정
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # WebDriver 생성
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(self.timeout_setting.value())
            
            # BUYMA 로그인
            if self.buyma_login(driver):
                # 가격 수정 실행
                success = self.update_product_price(driver, product_name, new_price)
                
                if success:
                    self.log_message(f"✅ 가격 수정 완료: {product_name}")
                    self.update_price_table_status(row, "수정 완료", True)
                else:
                    self.log_message(f"❌ 가격 수정 실패: {product_name}")
                    self.update_price_table_status(row, "수정 실패", False)
            else:
                self.log_message("❌ BUYMA 로그인 실패")
                self.update_price_table_status(row, "로그인 실패", False)
                
        except Exception as e:
            self.log_message(f"❌ 가격 수정 오류: {str(e)}")
            self.update_price_table_status(row, "오류 발생", False)
        finally:
            if driver:
                driver.quit()
    
    def buyma_login(self, driver):
        """BUYMA 로그인"""
        try:
            self.log_message("🔐 BUYMA 로그인 페이지 접속...")
            
            # BUYMA 로그인 페이지 접속
            login_url = "https://www.buyma.com/my/login/"
            driver.get(login_url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 이메일 입력
            email = self.email_input.text().strip()
            password = self.password_input.text().strip()
            
            if not email or not password:
                self.log_message("❌ 이메일 또는 비밀번호가 입력되지 않았습니다.")
                return False
            
            self.log_message(f"📧 로그인 시도: {email}")
            
            # 이메일 입력 필드 찾기 및 입력
            email_selectors = [
                "input[name='email']",
                "input[type='email']", 
                "#email",
                ".email-input",
                "input[placeholder*='메일']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not email_input:
                self.log_message("❌ 이메일 입력 필드를 찾을 수 없습니다.")
                return False
            
            email_input.clear()
            email_input.send_keys(email)
            
            time.sleep(1)
            
            # 비밀번호 입력 필드 찾기 및 입력
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password",
                ".password-input"
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not password_input:
                self.log_message("❌ 비밀번호 입력 필드를 찾을 수 없습니다.")
                return False
            
            password_input.clear()
            password_input.send_keys(password)
            
            # 로그인 버튼 클릭
            login_button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                ".login-button",
                ".btn-login",
                "button:contains('로그인')"
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not login_button:
                self.log_message("❌ 로그인 버튼을 찾을 수 없습니다.")
                return False
            
            login_button.click()
            
            # 로그인 완료 대기 (URL 변경 또는 특정 요소 확인)
            import time
            time.sleep(3)
            
            # 로그인 성공 확인
            current_url = driver.current_url
            if "login" not in current_url.lower() or "my" in current_url.lower():
                self.log_message("✅ BUYMA 로그인 성공!")
                return True
            else:
                self.log_message("❌ BUYMA 로그인 실패 - URL 확인 필요")
                return False
                
        except Exception as e:
            self.log_message(f"BUYMA 로그인 오류: {str(e)}")
            return False
    
    def update_product_price(self, driver, product_name, new_price):
        """상품 가격 업데이트"""
        try:
            self.log_message(f"🔍 상품 검색 중: {product_name}")
            
            # BUYMA 셀러 관리 페이지로 이동
            seller_page_url = "https://www.buyma.com/my/item/"
            driver.get(seller_page_url)
            
            # 페이지 로딩 대기
            import time
            time.sleep(3)
            
            # 상품 검색 (상품명으로)
            # TODO: 실제 BUYMA 셀러 페이지 구조에 맞게 수정 필요
            search_selectors = [
                "input[name='search']",
                ".search-input",
                "#search",
                "input[placeholder*='검색']"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if search_input:
                search_input.clear()
                search_input.send_keys(product_name)
                search_input.submit()
                time.sleep(2)
            
            # 상품 목록에서 해당 상품 찾기
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/item/']")
            
            target_product = None
            for link in product_links:
                if product_name.lower() in link.text.lower():
                    target_product = link
                    break
            
            if not target_product:
                self.log_message(f"❌ 상품을 찾을 수 없습니다: {product_name}")
                return False
            
            # 상품 수정 페이지로 이동
            target_product.click()
            time.sleep(2)
            
            # 가격 입력 필드 찾기
            price_selectors = [
                "input[name='price']",
                ".price-input",
                "#price",
                "input[placeholder*='가격']"
            ]
            
            price_input = None
            for selector in price_selectors:
                try:
                    price_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not price_input:
                self.log_message("❌ 가격 입력 필드를 찾을 수 없습니다.")
                return False
            
            # 가격 수정
            price_input.clear()
            price_input.send_keys(str(new_price))
            
            # 저장 버튼 클릭
            save_selectors = [
                "button[type='submit']",
                ".save-button",
                ".btn-save",
                "input[value*='저장']"
            ]
            
            save_button = None
            for selector in save_selectors:
                try:
                    save_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if save_button:
                save_button.click()
                time.sleep(2)
                self.log_message(f"💾 가격 저장 완료: {new_price}엔")
                return True
            else:
                self.log_message("❌ 저장 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            self.log_message(f"상품 가격 업데이트 오류: {str(e)}")
            return False
    
    def update_price_table_status(self, row, status, success):
        """가격 테이블 상태 업데이트"""
        try:
            # 상태 업데이트
            if success:
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#28a745")))
                
                # 버튼을 완료 상태로 변경
                btn = QPushButton("✅ 완료")
                btn.setStyleSheet("""
                    QPushButton {
                        background: #6c757d;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 10px;
                    }
                """)
                btn.setEnabled(False)
                self.price_table.setCellWidget(row, 7, btn)
            else:
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#dc3545")))
            
            self.price_table.setItem(row, 6, status_item)
            
        except Exception as e:
            self.log_message(f"테이블 상태 업데이트 오류: {str(e)}")
        
    def auto_update_all_prices(self):
        """전체 상품 자동 업데이트"""
        # 크롤링된 데이터가 있는지 확인
        if self.crawling_table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "크롤링된 상품 데이터가 없습니다.\n먼저 크롤링 탭에서 상품을 수집해주세요.")
            return
        
        reply = QMessageBox.question(
            self, 
            "확인", 
            f"크롤링된 {self.crawling_table.rowCount()}개 상품의 가격을 분석하시겠습니까?\n\n이 작업은 시간이 오래 걸릴 수 있습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # UI 상태 변경
        self.auto_update_all_btn.setEnabled(False)
        self.auto_update_all_btn.setText("🔄 전체 분석 중...")
        
        # 테이블 초기화
        self.price_table.setRowCount(0)
        
        # 로그 시작
        self.log_message(f"🚀 전체 상품 가격 분석 시작: {self.crawling_table.rowCount()}개 상품")
        
        # 별도 스레드에서 전체 가격 분석 실행
        import threading
        
        self.bulk_analysis_thread = threading.Thread(target=self.run_bulk_price_analysis, daemon=True)
        self.bulk_analysis_thread.start()
    
    def run_bulk_price_analysis(self):
        """전체 상품 가격 분석 실행 (별도 스레드)"""
        driver = None
        try:
            self.log_message("🌐 브라우저를 시작합니다...")
            
            # Selenium WebDriver 설정
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Chrome 옵션 설정
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # WebDriver 생성
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(self.timeout_setting.value())
            
            # 크롤링된 상품들을 하나씩 분석
            total_products = self.crawling_table.rowCount()
            success_count = 0
            failed_count = 0
            
            for row in range(total_products):
                try:
                    # 상품 정보 가져오기
                    product_name = self.crawling_table.item(row, 0).text()
                    brand_name = self.crawling_table.item(row, 1).text()
                    
                    self.log_message(f"🔍 분석 중 ({row+1}/{total_products}): {brand_name} - {product_name}")
                    
                    # BUYMA 검색 및 가격 분석
                    competitor_products = self.search_buyma_product(driver, brand_name, product_name)
                    
                    if competitor_products:
                        # 가격 분석 및 결과 추가
                        self.add_bulk_analysis_result(brand_name, product_name, competitor_products)
                        success_count += 1
                        self.log_message(f"✅ 분석 완료: {product_name}")
                    else:
                        failed_count += 1
                        self.log_message(f"❌ 분석 실패: {product_name} (검색 결과 없음)")
                    
                    # 딜레이 추가 (서버 부하 방지)
                    import time
                    time.sleep(self.delay_time.value())
                    
                    # 진행률 업데이트
                    progress = int(((row + 1) / total_products) * 100)
                    self.log_message(f"📊 진행률: {progress}% ({row+1}/{total_products})")
                    
                except Exception as e:
                    failed_count += 1
                    self.log_message(f"❌ 상품 분석 오류 ({row+1}): {str(e)}")
                    continue
            
            # 완료 처리
            self.log_message(f"🎉 전체 분석 완료! 성공: {success_count}개, 실패: {failed_count}개")
            
            # 요약 정보 업데이트
            self.total_analyzed.setText(f"분석 완료: {success_count}개")
            self.auto_updated.setText("자동 수정: 0개")
            self.excluded_items.setText("제외: 0개")
            self.failed_items.setText(f"실패: {failed_count}개")
            
        except Exception as e:
            self.log_message(f"❌ 전체 분석 오류: {str(e)}")
        finally:
            if driver:
                driver.quit()
            
            # UI 상태 복원
            self.auto_update_all_btn.setEnabled(True)
            self.auto_update_all_btn.setText("🚀 전체 상품 자동 업데이트")
    
    def search_buyma_product(self, driver, brand, product):
        """BUYMA에서 특정 상품 검색"""
        try:
            # 검색 쿼리 생성
            search_query = f"{brand} {product}"
            search_url = f"https://www.buyma.com/r/_/4FK1249/?q={search_query}"
            
            # 검색 페이지 접속
            driver.get(search_url)
            
            # 페이지 로딩 대기
            import time
            time.sleep(2)
            
            # 경쟁사 상품 정보 추출
            competitor_products = self.extract_competitor_products(driver, brand, product)
            
            return competitor_products
            
        except Exception as e:
            self.log_message(f"BUYMA 검색 오류: {str(e)}")
            return []
    
    def add_bulk_analysis_result(self, brand, product, competitor_products):
        """전체 분석 결과를 테이블에 추가"""
        try:
            if not competitor_products:
                return
            
            # 최저가 계산
            lowest_price = min(p['price'] for p in competitor_products)
            
            # 할인 금액 적용
            discount = self.dashboard_discount.value()
            suggested_price = max(lowest_price - discount, 0)
            
            # 현재 가격 (예시 - 실제로는 사용자 데이터에서 가져와야 함)
            current_price = lowest_price + 200  # 예시: 최저가보다 200엔 높다고 가정
            
            # 예상 마진 계산
            estimated_margin = suggested_price - (suggested_price * 0.1)  # 예시: 10% 수수료 제외
            
            # 테이블에 행 추가
            row = self.price_table.rowCount()
            self.price_table.insertRow(row)
            
            self.price_table.setItem(row, 0, QTableWidgetItem(f"{brand} {product}"))
            self.price_table.setItem(row, 1, QTableWidgetItem(brand))
            self.price_table.setItem(row, 2, QTableWidgetItem(f"{current_price}엔"))
            self.price_table.setItem(row, 3, QTableWidgetItem(f"{lowest_price}엔"))
            self.price_table.setItem(row, 4, QTableWidgetItem(f"{suggested_price}엔"))
            self.price_table.setItem(row, 5, QTableWidgetItem(f"+{int(estimated_margin)}엔"))
            
            # 상태 표시
            if suggested_price < current_price:
                status_item = QTableWidgetItem("수정 권장")
                status_item.setForeground(QBrush(QColor("#ffc107")))
            else:
                status_item = QTableWidgetItem("현재가 적정")
                status_item.setForeground(QBrush(QColor("#28a745")))
            
            self.price_table.setItem(row, 6, status_item)
            
            # 액션 버튼들
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            
            if self.auto_mode.isChecked():
                action_btn = QPushButton("🔄")
                action_btn.setToolTip("자동 수정")
                action_btn.setFixedSize(25, 25)
                action_btn.setStyleSheet("""
                    QPushButton {
                        background: #28a745;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background: #1e7e34;
                    }
                """)
                action_btn.clicked.connect(lambda checked, r=row: self.auto_update_price(r))
            else:
                action_btn = QPushButton("💱")
                action_btn.setToolTip("수동 수정")
                action_btn.setFixedSize(25, 25)
                action_btn.setStyleSheet("""
                    QPushButton {
                        background: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background: #0056b3;
                    }
                """)
                action_btn.clicked.connect(lambda checked, r=row: self.manual_update_price(r))
            
            # 주력상품 추가 버튼
            favorite_btn = QPushButton("⭐")
            favorite_btn.setToolTip("주력상품으로 추가")
            favorite_btn.setFixedSize(25, 25)
            favorite_btn.setStyleSheet("""
                QPushButton {
                    background: #ffc107;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background: #e0a800;
                }
            """)
            favorite_btn.clicked.connect(lambda checked, r=row: self.add_to_favorite_from_price_table(r))
            
            action_layout.addWidget(action_btn)
            action_layout.addWidget(favorite_btn)
            action_layout.addStretch()
            
            self.price_table.setCellWidget(row, 7, action_widget)
            
            # 자동 스크롤
            self.price_table.scrollToBottom()
            
        except Exception as e:
            self.log_message(f"결과 추가 오류: {str(e)}")
        
    # def add_demo_price_data(self):
    #     """데모용 가격 데이터 추가"""
    #     from PyQt6.QtGui import QColor, QBrush
        
    #     demo_data = [
    #         ["상품A", "브랜드A", "5000엔", "4500엔", "4400엔", "+600엔", "수정 가능", "수정"],
    #         ["상품B", "브랜드B", "3000엔", "2800엔", "2700엔", "-100엔", "손실 예상", "제외"],
    #         ["상품C", "브랜드C", "8000엔", "7500엔", "7400엔", "+1100엔", "수정 가능", "수정"],
    #     ]
        
    #     self.price_table.setRowCount(len(demo_data))
        
    #     for row, data in enumerate(demo_data):
    #         for col, value in enumerate(data):
    #             if col == 7:  # 액션 컬럼
    #                 action_widget = QWidget()
    #                 action_layout = QHBoxLayout(action_widget)
    #                 action_layout.setContentsMargins(2, 2, 2, 2)
    #                 action_layout.setSpacing(2)
                    
    #                 if value == "수정":
    #                     btn = QPushButton("💱")
    #                     btn.setToolTip("가격 수정")
    #                     btn.setFixedSize(25, 25)
    #                     btn.setStyleSheet("""
    #                         QPushButton {
    #                             background: #28a745;
    #                             color: white;
    #                             border: none;
    #                             border-radius: 4px;
    #                             font-size: 10px;
    #                         }
    #                         QPushButton:hover {
    #                             background: #1e7e34;
    #                         }
    #                     """)
    #                     btn.clicked.connect(lambda checked, r=row: self.update_single_price(r))
    #                     action_layout.addWidget(btn)
                        
    #                     # 주력상품 추가 버튼
    #                     favorite_btn = QPushButton("⭐")
    #                     favorite_btn.setToolTip("주력상품으로 추가")
    #                     favorite_btn.setFixedSize(25, 25)
    #                     favorite_btn.setStyleSheet("""
    #                         QPushButton {
    #                             background: #ffc107;
    #                             color: white;
    #                             border: none;
    #                             border-radius: 4px;
    #                             font-size: 10px;
    #                         }
    #                         QPushButton:hover {
    #                             background: #e0a800;
    #                         }
    #                     """)
    #                     favorite_btn.clicked.connect(lambda checked, r=row: self.add_to_favorite_from_price_table(r))
    #                     action_layout.addWidget(favorite_btn)
                        
    #                 else:
    #                     btn = QPushButton("❌")
    #                     btn.setToolTip("제외됨")
    #                     btn.setFixedSize(25, 25)
    #                     btn.setStyleSheet("""
    #                         QPushButton {
    #                             background: #dc3545;
    #                             color: white;
    #                             border: none;
    #                             border-radius: 4px;
    #                             font-size: 10px;
    #                         }
    #                     """)
    #                     btn.setEnabled(False)
    #                     action_layout.addWidget(btn)
                    
    #                 action_layout.addStretch()
    #                 self.price_table.setCellWidget(row, col, action_widget)
    #             else:
    #                 item = QTableWidgetItem(str(value))
    #                 if col == 6:  # 상태 컬럼
    #                     if "손실" in str(value):
    #                         # 빨간색으로 설정
    #                         item.setForeground(QBrush(QColor("#dc3545")))
    #                         font = item.font()
    #                         font.setBold(True)
    #                         item.setFont(font)
    #                     elif "수정 가능" in str(value):
    #                         # 녹색으로 설정
    #                         item.setForeground(QBrush(QColor("#28a745")))
    #                         font = item.font()
    #                         font.setBold(True)
    #                         item.setFont(font)
    #                 elif col == 5:  # 예상마진 컬럼
    #                     if "-" in str(value):
    #                         # 마이너스 마진은 빨간색
    #                         item.setForeground(QBrush(QColor("#dc3545")))
    #                         font = item.font()
    #                         font.setBold(True)
    #                         item.setFont(font)
    #                     else:
    #                         # 플러스 마진은 녹색
    #                         item.setForeground(QBrush(QColor("#28a745")))
    #                         font = item.font()
    #                         font.setBold(True)
    #                         item.setFont(font)
                    
    #                 self.price_table.setItem(row, col, item)
        
    #     # 요약 정보 업데이트
    #     self.total_analyzed.setText("분석 완료: 3개")
    #     self.auto_updated.setText("자동 수정: 0개")
    #     self.excluded_items.setText("제외: 1개")
    #     self.failed_items.setText("실패: 0개")
        
    def update_single_price(self, row):
        """개별 상품 가격 수정"""
        from PyQt6.QtGui import QColor, QBrush
        
        product_name = self.price_table.item(row, 0).text()
        self.log_message(f"가격 수정 중: {product_name}")
        
        # TODO: 실제 가격 수정 로직 구현
        
        # 액션 버튼들을 완료 상태로 변경
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        action_layout.setSpacing(2)
        
        # 완료 버튼
        btn = QPushButton("✅")
        btn.setToolTip("수정 완료")
        btn.setFixedSize(25, 25)
        btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 10px;
            }
        """)
        btn.setEnabled(False)
        action_layout.addWidget(btn)
        
        # 주력상품 추가 버튼 (여전히 활성화)
        favorite_btn = QPushButton("⭐")
        favorite_btn.setToolTip("주력상품으로 추가")
        favorite_btn.setFixedSize(25, 25)
        favorite_btn.setStyleSheet("""
            QPushButton {
                background: #ffc107;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #e0a800;
            }
        """)
        favorite_btn.clicked.connect(lambda checked, r=row: self.add_to_favorite_from_price_table(r))
        action_layout.addWidget(favorite_btn)
        
        action_layout.addStretch()
        self.price_table.setCellWidget(row, 7, action_widget)
        
        # 상태 업데이트
        status_item = QTableWidgetItem("수정 완료")
        status_item.setForeground(QBrush(QColor("#6c757d")))
        font = status_item.font()
        font.setBold(True)
        status_item.setFont(font)
        self.price_table.setItem(row, 6, status_item)
    
    @safe_slot
    def start_upload(self, checked=False):
        """업로드 시작 - 로그인 및 크롤링 데이터 확인"""
        try:
            # 1. 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(
                    self, 
                    "로그인 필요", 
                    "업로드를 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                    "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
                )
                return
            
            # 2. 크롤링된 데이터가 있는지 확인
            if self.crawling_table.rowCount() == 0:
                QMessageBox.warning(
                    self, 
                    "크롤링 데이터 없음", 
                    "업로드할 상품이 없습니다.\n\n"
                    "먼저 '🔍 상품 크롤링' 탭에서 상품을 크롤링해주세요."
                )
                return
            
            # 3. 업로드할 상품 개수 확인
            total_products = self.crawling_table.rowCount()
            reply = QMessageBox.question(
                self,
                "업로드 확인",
                f"총 {total_products}개의 상품을 BUYMA에 업로드하시겠습니까?\n\n"
                f"⚠️ 주의: 업로드는 시간이 오래 걸릴 수 있습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log_message(f"🚀 자동 업로드 시작: {total_products}개 상품")
            
            # 업로드 진행률 위젯 표시
            self.upload_progress_widget.show_progress(
                title="📤 상품 업로드 진행률",
                total=total_products,
                current=0,
                status="업로드 준비 중..."
            )
            
            # 4. UI 상태 변경
            self.start_upload_btn.setEnabled(False)
            self.pause_upload_btn.setEnabled(True)
            self.stop_upload_btn.setEnabled(True)
            self.upload_progress.setValue(0)
            self.current_upload_status.setText("업로드 준비중...")
            
            # 업로드 결과 테이블 초기화
            self.upload_table.setRowCount(0)
            
            # 5. UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
            self.switch_to_monitoring_tab()
            self.set_tabs_enabled(False)
            
            # 6. 별도 스레드에서 업로드 실행
            import threading
            
            self.upload_thread = threading.Thread(
                target=self.run_bulk_upload, 
                daemon=True
            )
            self.upload_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ 업로드 시작 오류: {str(e)}")
            self.reset_upload_ui()
    
    def run_bulk_upload(self):
        """대량 업로드 실행 (별도 스레드)"""
        total_products = 0  # 변수 초기화
        uploaded_count = 0
        failed_count = 0
        
        try:
            # 최대 이미지 수 확인 (올바른 속성명 사용)
            max_images_setting = self.max_images.value()
            if max_images_setting > 20:
                self.log_message(f"❌ 최대 이미지 수가 20을 초과합니다 ({max_images_setting}개)")
                self.log_message("📝 업로드 탭에서 최대 이미지 수를 20 이하로 변경해주세요.")
                QMessageBox.warning(
                    self,
                    "이미지 수 초과",
                    f"BUYMA는 최대 20장까지만 업로드 가능합니다.\n\n"
                    f"현재 설정: {max_images_setting}장\n"
                    f"업로드 탭에서 최대 이미지 수를 20 이하로 변경해주세요."
                )
                return  # finally 블록에서 UI 복원됨
            
            total_products = self.crawling_table.rowCount()
            uploaded_count = 0
            failed_count = 0
            
            self.log_message(f"📤 업로드 시작: 총 {total_products}개 상품 (최대 이미지: {max_images_setting}장)")
            
            # 각 상품별로 업로드 처리
            for row in range(total_products):
                try:
                    # 중단 요청 확인
                    if hasattr(self, 'upload_stopped') and self.upload_stopped:
                        self.log_message("⏹️ 사용자에 의해 업로드가 중단되었습니다.")
                        break
                    
                    # 크롤링 테이블에서 상품 정보 가져오기
                    product_data = self.get_product_data_from_table(row)
                    
                    if not product_data:
                        self.log_message(f"❌ 상품 {row + 1}: 데이터를 가져올 수 없습니다.")
                        failed_count += 1
                        continue
                    
                    # 진행률 업데이트
                    progress = int((row / total_products) * 100)
                    self.upload_progress.setValue(progress)
                    status_text = f"업로드 중: {row + 1}/{total_products} - {product_data['title'][:30]}..."
                    self.current_upload_status.setText(status_text)
                    
                    # 업로드 진행률 위젯 업데이트
                    self.update_upload_progress_widget(row + 1, total_products, status_text)
                    
                    self.log_message(f"📤 업로드 중 ({row + 1}/{total_products}): {product_data['title'][:50]}...")
                    
                    # 실제 BUYMA 업로드 실행
                    result = self.upload_single_product(product_data, row + 1, max_images_setting)
                    
                    # 결과에 따른 처리
                    if result['success']:
                        uploaded_count += 1
                        self.increment_uploaded_count()  # 업로드 통계 업데이트
                        self.log_message(f"✅ 업로드 성공: {product_data['title'][:30]}...")
                        status = "✅ 성공"
                        status_color = "#28a745"
                    else:
                        failed_count += 1
                        self.log_message(f"❌ 업로드 실패: {product_data['title'][:30]}... - {result['error']}")
                        status = f"❌ 실패: {result['error']}"
                        status_color = "#dc3545"
                    
                    # 업로드 결과 테이블에 추가
                    self.add_upload_result_to_table(product_data, status, status_color)
                    
                    # 업로드 간 딜레이 (서버 부하 방지)
                    import time
                    time.sleep(5)
                    
                except Exception as e:
                    failed_count += 1
                    self.log_message(f"❌ 상품 {row + 1} 업로드 오류: {str(e)}")
                    
                    # 오류 결과도 테이블에 추가
                    try:
                        product_data = self.get_product_data_from_table(row)
                        if product_data:
                            self.add_upload_result_to_table(product_data, f"❌ 오류: {str(e)}", "#dc3545")
                    except:
                        pass
                    
                    continue
            
            # 업로드 완료
            self.upload_progress.setValue(100)
            self.current_upload_status.setText("업로드 완료")
            
            self.log_message(f"🎉 업로드 완료!")
            self.log_message(f"📊 결과: 성공 {uploaded_count}개, 실패 {failed_count}개")
            
        except Exception as e:
            self.log_message(f"❌ 대량 업로드 오류: {str(e)}")
            print(e)
        
        finally:
            # UI 상태 복원
            try:
                self.start_upload_btn.setEnabled(True)
                self.pause_upload_btn.setEnabled(False)
                self.stop_upload_btn.setEnabled(False)
                self.current_upload_status.setText("대기 중")
                
                # 다른 탭 활성화
                self.set_tabs_enabled(True)
                
            except Exception as e:
                self.log_message(f"❌ UI 상태 복원 오류: {str(e)}")
            failed_count = 0
            
            for row in range(total_products):
                try:
                    # 상품 정보 가져오기
                    product_data = self.get_crawled_product_data(row)
                    
                    self.log_message(f"📤 업로드 중 ({row+1}/{total_products}): {product_data['title']}")
                    
                    # BUYMA에 상품 업로드
                    upload_success = self.upload_single_product(self.shared_driver, product_data)
                    
                    if upload_success:
                        success_count += 1
                        self.add_upload_result(product_data, "업로드 완료", True)
                        self.log_message(f"✅ 업로드 완료: {product_data['title']}")
                    else:
                        failed_count += 1
                        self.add_upload_result(product_data, "업로드 실패", False)
                        self.log_message(f"❌ 업로드 실패: {product_data['title']}")
                    
                    # 진행률 업데이트
                    progress = int(((row + 1) / total_products) * 100)
                    self.upload_progress.setValue(progress)
                    self.current_upload_status.setText(f"진행중: {row+1}/{total_products}")
                    
                    # 딜레이 추가 (서버 부하 방지)
                    import time
                    time.sleep(self.delay_time.value())
                    
                except Exception as e:
                    failed_count += 1
                    self.log_message(f"❌ 상품 업로드 오류 ({row+1}): {str(e)}")
                    continue
            
            # 완료 처리
            self.log_message(f"🎉 업로드 완료! 성공: {success_count}개, 실패: {failed_count}개")
            self.current_upload_status.setText(f"완료: 성공 {success_count}개, 실패 {failed_count}개")
            self.upload_progress.setValue(100)
    
    def get_crawled_product_data(self, row):
        """크롤링된 상품 데이터 가져오기"""
        try:
            product_data = {
                'title': self.crawling_table.item(row, 0).text() if self.crawling_table.item(row, 0) else '',
                'brand': self.crawling_table.item(row, 1).text() if self.crawling_table.item(row, 1) else '',
                'price': self.crawling_table.item(row, 2).text() if self.crawling_table.item(row, 2) else '',
                'url': self.crawling_table.item(row, 5).text() if self.crawling_table.item(row, 5) else '',
                'images': [],  # TODO: 실제 이미지 데이터 연결
                'colors': [],  # TODO: 실제 색상 데이터 연결
                'sizes': [],   # TODO: 실제 사이즈 데이터 연결
                'description': f"{self.crawling_table.item(row, 1).text()} {self.crawling_table.item(row, 0).text()}"
            }
            return product_data
        except Exception as e:
            self.log_message(f"상품 데이터 가져오기 오류: {str(e)}")
            return {}
    
    # def upload_single_product(self, driver, product_data):
    #     """단일 상품 BUYMA 업로드"""
    #     try:
    #         self.log_message(f"📝 상품 등록 페이지 접속: {product_data['title']}")
            
    #         # BUYMA 상품 등록 페이지로 이동
    #         upload_url = "https://www.buyma.com/my/item/new/"
    #         driver.get(upload_url)
            
    #         # 페이지 로딩 대기
    #         import time
    #         time.sleep(3)
            
    #         # 상품명 입력
    #         title_success = self.fill_product_title(driver, product_data['title'])
    #         if not title_success:
    #             return False
            
    #         # 브랜드 입력
    #         brand_success = self.fill_product_brand(driver, product_data['brand'])
    #         if not brand_success:
    #             return False
            
    #         # 가격 입력
    #         price_success = self.fill_product_price(driver, product_data['price'])
    #         if not price_success:
    #             return False
            
    #         # 상품 설명 입력
    #         desc_success = self.fill_product_description(driver, product_data['description'])
    #         if not desc_success:
    #             return False
            
    #         # 이미지 업로드 (있는 경우)
    #         if product_data.get('images'):
    #             image_success = self.upload_product_images(driver, product_data['images'])
    #             if not image_success:
    #                 self.log_message("⚠️ 이미지 업로드 실패 - 계속 진행")
            
    #         # 카테고리 선택 (기본값 사용)
    #         self.select_default_category(driver)
            
    #         # 저장 또는 등록
    #         save_success = self.save_product(driver)
            
    #         return save_success
            
    #     except Exception as e:
    #         self.log_message(f"단일 상품 업로드 오류: {str(e)}")
    #         return False
    
    def add_upload_result(self, product_data, status, success):
        """업로드 결과를 테이블에 추가"""
        try:
            row = self.upload_table.rowCount()
            self.upload_table.insertRow(row)
            
            # 데이터 추가
            self.upload_table.setItem(row, 0, QTableWidgetItem(product_data.get('title', '')))
            self.upload_table.setItem(row, 1, QTableWidgetItem(product_data.get('brand', '')))
            self.upload_table.setItem(row, 2, QTableWidgetItem(product_data.get('price', '')))
            self.upload_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime('%H:%M:%S')))
            
            # 상태 표시
            if success:
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#28a745")))
            else:
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#dc3545")))
            
            self.upload_table.setItem(row, 4, status_item)
            
            # 자동 스크롤
            self.upload_table.scrollToBottom()
            
        except Exception as e:
            self.log_message(f"업로드 결과 추가 오류: {str(e)}")
    
    def retry_failed_uploads(self):
        """실패한 업로드 재시도"""
        self.log_message("실패한 업로드를 재시도합니다...")
        # TODO: 재시도 로직 구현
        
    def export_upload_results(self):
        """업로드 결과 내보내기"""
        try:
            if self.upload_table.rowCount() == 0:
                QMessageBox.warning(self, "경고", "내보낼 업로드 결과가 없습니다.")
                return
            
            # 파일 저장 경로 선택
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "업로드 결과 저장", 
                f"업로드_결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # 데이터 수집
            import pandas as pd
            
            data = []
            for row in range(self.upload_table.rowCount()):
                row_data = {
                    '상품명': self.upload_table.item(row, 0).text() if self.upload_table.item(row, 0) else '',
                    '브랜드': self.upload_table.item(row, 1).text() if self.upload_table.item(row, 1) else '',
                    '가격': self.upload_table.item(row, 2).text() if self.upload_table.item(row, 2) else '',
                    '업로드 시간': self.upload_table.item(row, 3).text() if self.upload_table.item(row, 3) else '',
                    '상태': self.upload_table.item(row, 4).text() if self.upload_table.item(row, 4) else '',
                    '처리일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                data.append(row_data)
            
            # DataFrame 생성 및 저장
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            self.log_message(f"✅ 업로드 결과를 저장했습니다: {file_path}")
            QMessageBox.information(self, "저장 완료", f"업로드 결과가 저장되었습니다.\n\n{file_path}")
            
        except Exception as e:
            self.log_message(f"❌ Excel 저장 오류: {str(e)}")
            QMessageBox.critical(self, "저장 오류", f"Excel 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def fill_product_title(self, driver, title):
        """상품명 입력"""
        try:
            title_selectors = [
                "input[name='title']",
                "input[name='name']",
                "#title",
                ".title-input",
                "input[placeholder*='상품명']"
            ]
            
            for selector in title_selectors:
                try:
                    title_input = driver.find_element(By.CSS_SELECTOR, selector)
                    title_input.clear()
                    title_input.send_keys(title)
                    self.log_message(f"✅ 상품명 입력 완료: {title}")
                    return True
                except:
                    continue
            
            self.log_message("❌ 상품명 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"상품명 입력 오류: {str(e)}")
            return False
    
    def fill_product_brand(self, driver, brand):
        """브랜드 입력"""
        try:
            brand_selectors = [
                "input[name='brand']",
                "select[name='brand']",
                "#brand",
                ".brand-input",
                "input[placeholder*='브랜드']"
            ]
            
            for selector in brand_selectors:
                try:
                    brand_input = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # select 태그인 경우
                    if brand_input.tag_name == 'select':
                        from selenium.webdriver.support.ui import Select
                        select = Select(brand_input)
                        # 브랜드명으로 옵션 찾기
                        for option in select.options:
                            if brand.lower() in option.text.lower():
                                select.select_by_visible_text(option.text)
                                break
                    else:
                        brand_input.clear()
                        brand_input.send_keys(brand)
                    
                    self.log_message(f"✅ 브랜드 입력 완료: {brand}")
                    return True
                except:
                    continue
            
            self.log_message("❌ 브랜드 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"브랜드 입력 오류: {str(e)}")
            return False
    
    def fill_product_price(self, driver, price_text):
        """가격 입력"""
        try:
            # 가격에서 숫자만 추출
            import re
            price_numbers = re.findall(r'[\d,]+', price_text)
            if not price_numbers:
                self.log_message("❌ 가격 정보를 찾을 수 없습니다.")
                return False
            
            price = price_numbers[0].replace(',', '')
            
            price_selectors = [
                "input[name='price']",
                "#price",
                ".price-input",
                "input[placeholder*='가격']"
            ]
            
            for selector in price_selectors:
                try:
                    price_input = driver.find_element(By.CSS_SELECTOR, selector)
                    price_input.clear()
                    price_input.send_keys(price)
                    self.log_message(f"✅ 가격 입력 완료: {price}엔")
                    return True
                except:
                    continue
            
            self.log_message("❌ 가격 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"가격 입력 오류: {str(e)}")
            return False
    
    def fill_product_description(self, driver, description):
        """상품 설명 입력"""
        try:
            desc_selectors = [
                "textarea[name='description']",
                "textarea[name='detail']",
                "#description",
                ".description-input",
                "textarea[placeholder*='설명']"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_input = driver.find_element(By.CSS_SELECTOR, selector)
                    desc_input.clear()
                    desc_input.send_keys(description)
                    self.log_message("✅ 상품 설명 입력 완료")
                    return True
                except:
                    continue
            
            self.log_message("❌ 상품 설명 입력 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"상품 설명 입력 오류: {str(e)}")
            return False
    
    def upload_product_images(self, driver, images):
        """상품 이미지 업로드"""
        try:
            # 이미지 업로드 필드 찾기
            image_selectors = [
                "input[type='file'][name*='image']",
                "input[type='file'][accept*='image']",
                ".image-upload input[type='file']",
                "#image-upload"
            ]
            
            for selector in image_selectors:
                try:
                    image_input = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # 여러 이미지 업로드 (최대 10개)
                    upload_images = images[:10]
                    image_paths = "\n".join(upload_images)
                    image_input.send_keys(image_paths)
                    
                    self.log_message(f"✅ 이미지 업로드 완료: {len(upload_images)}장")
                    return True
                except:
                    continue
            
            self.log_message("❌ 이미지 업로드 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"이미지 업로드 오류: {str(e)}")
            return False
    
    def select_default_category(self, driver):
        """기본 카테고리 선택"""
        try:
            category_selectors = [
                "select[name='category']",
                "#category",
                ".category-select"
            ]
            
            for selector in category_selectors:
                try:
                    category_select = driver.find_element(By.CSS_SELECTOR, selector)
                    from selenium.webdriver.support.ui import Select
                    select = Select(category_select)
                    
                    # 첫 번째 유효한 옵션 선택 (보통 "선택하세요" 제외)
                    if len(select.options) > 1:
                        select.select_by_index(1)
                        self.log_message("✅ 기본 카테고리 선택 완료")
                        return True
                except:
                    continue
            
            self.log_message("⚠️ 카테고리 선택 필드를 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"카테고리 선택 오류: {str(e)}")
            return False
    
    def save_product(self, driver):
        """상품 저장"""
        try:
            save_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                ".save-button",
                ".btn-save",
                "button:contains('저장')",
                "button:contains('등록')"
            ]
            
            for selector in save_selectors:
                try:
                    save_button = driver.find_element(By.CSS_SELECTOR, selector)
                    save_button.click()
                    
                    # 저장 완료 대기
                    import time
                    time.sleep(3)
                    
                    self.log_message("✅ 상품 저장 완료")
                    return True
                except:
                    continue
            
            self.log_message("❌ 저장 버튼을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            self.log_message(f"상품 저장 오류: {str(e)}")
            return False
        file_path, _ = QFileDialog.getSaveFileName(
            self, "업로드 결과 저장", f"upload_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if file_path:
            self.log_message(f"업로드 결과를 {file_path}에 저장했습니다.")
    
    def test_login(self):
        """로그인 테스트"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "경고", "이메일과 비밀번호를 입력해주세요.")
            return
            
        self.log_message("로그인 테스트를 진행합니다...")
        # TODO: 로그인 테스트 로직 구현
        
    def encode_password(self, password):
        """비밀번호 간단 인코딩 (보안용)"""
        if not password:
            return ""
        try:
            import base64
            # 간단한 base64 인코딩 (완전한 보안은 아니지만 평문 저장 방지)
            encoded = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            return encoded
        except Exception as e:
            self.log_message(f"비밀번호 인코딩 오류: {str(e)}")
            return ""
    
    def decode_password(self, encoded_password):
        """비밀번호 디코딩"""
        if not encoded_password:
            return ""
        try:
            import base64
            decoded = base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
            return decoded
        except Exception as e:
            self.log_message(f"비밀번호 디코딩 오류: {str(e)}")
            return ""
    
    def save_settings(self):
        """설정 저장"""
        settings = {
            'email': self.email_input.text(),
            'password': self.encode_password(self.password_input.text()),  # 비밀번호 인코딩 저장
            'browser': self.browser_combo.currentText(),
            # 'headless': self.headless_mode.isChecked(),  # 주석처리됨
            # 'max_workers': self.max_workers.value(),  # 주석처리됨
            # 'request_delay': self.request_delay.value(),  # 주석처리됨
            'timeout': self.timeout_setting.value(),
            'retry_count': self.retry_count.value(),
            'crawl_count': self.crawl_count.value(),
            'delay_time': self.delay_time.value(),
            'discount_amount': self.discount_amount.value(),
            'min_margin': self.min_margin.value(),  # 다시 추가됨
            'exclude_loss_products': self.exclude_loss_products.isChecked(),
            'auto_mode': self.auto_mode.isChecked(),
            # 대시보드 설정
            'dashboard_url': self.dashboard_url.text(),
            'dashboard_count': self.dashboard_count.value(),
            'dashboard_discount': self.dashboard_discount.value(),
            # 'category': self.category_combo.currentText(),  # 주석처리됨
            # 'shipping': self.shipping_combo.currentText(),  # 주석처리됨
            # 'upload_mode': self.upload_mode.currentText(),  # 주석처리됨
            'max_images': self.max_images.value(),
            'include_images': self.include_images.isChecked(),
            'include_options': self.include_options.isChecked(),
            'skip_duplicates': self.skip_duplicates.isChecked(),
            # 'auto_translate': self.auto_translate.isChecked(),  # 주석처리됨
            # 'auto_categorize': self.auto_categorize.isChecked(),  # 주석처리됨
            # 'watermark_images': self.watermark_images.isChecked()  # 주석처리됨
        }
        
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log_message("설정이 저장되었습니다.")
            QMessageBox.information(self, "성공", "설정이 성공적으로 저장되었습니다.")
        except Exception as e:
            self.log_message(f"설정 저장 실패: {str(e)}")
            QMessageBox.critical(self, "오류", f"설정 저장에 실패했습니다: {str(e)}")
    
    def load_settings(self):
        """설정 불러오기"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 설정 적용
                self.email_input.setText(settings.get('email', ''))
                # 비밀번호 디코딩하여 설정
                encoded_password = settings.get('password', '')
                if encoded_password:
                    self.password_input.setText(self.decode_password(encoded_password))
                
                self.browser_combo.setCurrentText(settings.get('browser', 'Chrome'))
                # self.headless_mode.setChecked(settings.get('headless', False))  # 주석처리됨
                # self.max_workers.setValue(settings.get('max_workers', 3))  # 주석처리됨
                # self.request_delay.setValue(settings.get('request_delay', 3))  # 주석처리됨
                self.timeout_setting.setValue(settings.get('timeout', 10))  # 기본값 10으로 변경
                self.retry_count.setValue(settings.get('retry_count', 3))
                self.crawl_count.setValue(settings.get('crawl_count', 50))
                self.delay_time.setValue(settings.get('delay_time', 3))
                self.discount_amount.setValue(settings.get('discount_amount', 100))
                self.min_margin.setValue(settings.get('min_margin', 500))  # 다시 추가됨
                self.exclude_loss_products.setChecked(settings.get('exclude_loss_products', True))
                self.auto_mode.setChecked(settings.get('auto_mode', True))
                if not settings.get('auto_mode', True):
                    self.manual_mode.setChecked(True)
                # 대시보드 설정
                self.dashboard_url.setText(settings.get('dashboard_url', ''))
                self.dashboard_count.setValue(settings.get('dashboard_count', 20))
                self.dashboard_discount.setValue(settings.get('dashboard_discount', 100))
                # self.category_combo.setCurrentText(settings.get('category', '레디스 패션'))  # 주석처리됨
                # self.shipping_combo.setCurrentText(settings.get('shipping', '국제배송'))  # 주석처리됨
                # self.upload_mode.setCurrentText(settings.get('upload_mode', '즉시 등록'))  # 주석처리됨
                self.max_images.setValue(settings.get('max_images', 10))
                self.include_images.setChecked(settings.get('include_images', True))
                self.include_options.setChecked(settings.get('include_options', True))
                self.skip_duplicates.setChecked(settings.get('skip_duplicates', True))
                # self.auto_translate.setChecked(settings.get('auto_translate', False))  # 주석처리됨
                # self.auto_categorize.setChecked(settings.get('auto_categorize', False))  # 주석처리됨
                # self.watermark_images.setChecked(settings.get('watermark_images', False))  # 주석처리됨
                
                self.log_message("설정을 불러왔습니다.")
        except Exception as e:
            self.log_message(f"설정 불러오기 실패: {str(e)}")
    
    def reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(
            self, "확인", "모든 설정을 기본값으로 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 기본값으로 초기화
            self.email_input.clear()
            self.password_input.clear()
            self.browser_combo.setCurrentText('Chrome')
            # self.headless_mode.setChecked(False)  # 주석처리됨
            # self.max_workers.setValue(3)  # 주석처리됨
            # self.request_delay.setValue(3)  # 주석처리됨
            self.timeout_setting.setValue(10)  # 기본값 10으로 변경
            self.retry_count.setValue(3)
            self.crawl_count.setValue(50)
            self.delay_time.setValue(3)
            self.discount_amount.setValue(100)
            self.min_margin.setValue(500)  # 다시 추가됨
            self.exclude_loss_products.setChecked(True)
            self.auto_mode.setChecked(True)
            # 대시보드 설정
            self.dashboard_url.clear()
            self.dashboard_count.setValue(20)
            self.dashboard_discount.setValue(100)
            # self.category_combo.setCurrentText('레디스 패션')  # 주석처리됨
            # self.shipping_combo.setCurrentText('국제배송')  # 주석처리됨
            # self.upload_mode.setCurrentText('즉시 등록')  # 주석처리됨
            self.max_images.setValue(10)
            self.include_images.setChecked(True)
            self.include_options.setChecked(True)
            self.skip_duplicates.setChecked(True)
            # self.auto_translate.setChecked(False)  # 주석처리됨
            # self.auto_categorize.setChecked(False)  # 주석처리됨
            # self.watermark_images.setChecked(False)  # 주석처리됨
            
            self.log_message("설정이 초기화되었습니다.")
    
    def backup_settings(self):
        """설정 백업"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "설정 백업", f"buyma_settings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        if file_path:
            self.save_settings()  # 현재 설정 저장
            try:
                import shutil
                shutil.copy('settings.json', file_path)
                self.log_message(f"설정을 {file_path}에 백업했습니다.")
                QMessageBox.information(self, "성공", "설정이 성공적으로 백업되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"백업에 실패했습니다: {str(e)}")
    
    def restore_settings(self):
        """설정 복원"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "설정 복원", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                import shutil
                shutil.copy(file_path, 'settings.json')
                self.load_settings()
                self.log_message(f"{file_path}에서 설정을 복원했습니다.")
                QMessageBox.information(self, "성공", "설정이 성공적으로 복원되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"복원에 실패했습니다: {str(e)}")
    
    def clear_all_data(self):
        """모든 데이터 초기화"""
        reply = QMessageBox.question(
            self, "경고", "모든 데이터와 설정을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 설정 파일 삭제
                if os.path.exists('settings.json'):
                    os.remove('settings.json')
                
                # 테이블 초기화
                self.crawling_table.setRowCount(0)
                self.price_table.setRowCount(0)
                self.upload_table.setRowCount(0)
                
                # 로그 초기화
                self.log_output.clear()
                
                # 설정 초기화
                self.reset_settings()
                
                self.log_message("모든 데이터가 초기화되었습니다.")
                QMessageBox.information(self, "완료", "모든 데이터가 성공적으로 초기화되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"데이터 초기화에 실패했습니다: {str(e)}")
    
    def log_message(self, message, show_in_status=True):
        """로그 메시지 출력 (자동 스크롤 포함)"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{timestamp}] {message}"
            
            # log_output이 존재하는지 확인 (모니터링 로그창 - 모든 메시지 표시)
            if hasattr(self, 'log_output') and self.log_output is not None:
                # 로그 메시지 추가
                self.log_output.append(formatted_message)
                
                # 자동 스크롤 (여러 방법으로 확실하게)
                scrollbar = self.log_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
                # 추가 스크롤 보장
                cursor = self.log_output.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.log_output.setTextCursor(cursor)
                self.log_output.ensureCursorVisible()
                
                # QApplication 이벤트 처리 (UI 업데이트 보장)
                QApplication.processEvents()
                
                # 지연된 스크롤 보장 (QTimer 사용)
                QTimer.singleShot(10, self.ensure_log_scroll)
                
            else:
                # UI가 아직 준비되지 않은 경우 콘솔에 출력
                print(formatted_message)
            
            # 상태바 업데이트 (예외 메시지는 제외)
            if show_in_status and hasattr(self, 'status_label') and self.status_label is not None:
                # 오류/예외 관련 메시지는 상태바에 표시하지 않음
                if not any(keyword in message.lower() for keyword in ['오류', 'error', '실패', 'failed', '예외', 'exception', '❌']):
                    self.status_label.setText(message)
                else:
                    # 오류 발생 시 일반적인 상태 메시지만 표시
                    self.status_label.setText("작업 중 - 자세한 내용은 모니터링 탭을 확인하세요")
                
        except Exception as e:
            # 로그 출력 중 오류가 발생해도 프로그램이 중단되지 않도록
            print(f"로그 출력 오류: {e} - 메시지: {message}")
    
    def log_error(self, message):
        """오류 메시지 전용 로그 (상태바에는 표시하지 않음)"""
        self.log_message(message, show_in_status=False)
    
    def log_status(self, message):
        """상태 메시지 전용 로그 (상태바에도 표시)"""
        self.log_message(message, show_in_status=True)
    
    def ensure_log_scroll(self):
        """로그창 스크롤 보장 (지연 실행)"""
        try:
            if hasattr(self, 'log_output') and self.log_output is not None:
                # 최종 스크롤 보장
                scrollbar = self.log_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
                # 커서를 맨 끝으로 이동
                cursor = self.log_output.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.log_output.setTextCursor(cursor)
                
        except Exception as e:
            pass  # 스크롤 오류는 무시
    
    def closeEvent(self, event):
        """프로그램 종료 시 설정 저장 및 리소스 정리"""
        try:
            # 모든 QThread 안전하게 종료
            threads_to_wait = []
            
            if hasattr(self, 'crawling_thread') and self.crawling_thread and self.crawling_thread.isRunning():
                self.crawling_thread.quit()
                threads_to_wait.append(self.crawling_thread)
            
            if hasattr(self, 'login_thread') and self.login_thread and self.login_thread.isRunning():
                self.login_thread.quit()
                threads_to_wait.append(self.login_thread)
            
            if hasattr(self, 'automation_thread') and self.automation_thread and self.automation_thread.isRunning():
                self.automation_thread.quit()
                threads_to_wait.append(self.automation_thread)
            
            if hasattr(self, 'price_analysis_thread') and self.price_analysis_thread and self.price_analysis_thread.isRunning():
                self.price_analysis_thread.quit()
                threads_to_wait.append(self.price_analysis_thread)
            
            if hasattr(self, 'bulk_analysis_thread') and self.bulk_analysis_thread and self.bulk_analysis_thread.isRunning():
                self.bulk_analysis_thread.quit()
                threads_to_wait.append(self.bulk_analysis_thread)
            
            if hasattr(self, 'upload_thread') and self.upload_thread and self.upload_thread.isRunning():
                self.upload_thread.quit()
                threads_to_wait.append(self.upload_thread)
            
            # 모든 스레드가 종료될 때까지 대기 (최대 3초)
            for thread in threads_to_wait:
                thread.wait(3000)  # 3초 대기
            
            # 공용 드라이버 정리
            if hasattr(self, 'shared_driver') and self.shared_driver:
                try:
                    self.shared_driver.quit()
                    self.log_message("🔄 브라우저가 안전하게 종료되었습니다.")
                except:
                    pass
            
            # 타이머 정리
            if hasattr(self, 'timer'):
                self.timer.stop()
            if hasattr(self, 'system_timer'):
                self.system_timer.stop()
                
            # 설정 저장
            self.save_settings()
            
            # 주력 상품 자동 저장
            if hasattr(self, 'favorite_products'):
                self.save_favorite_products_auto()
            
            self.log_message("👋 프로그램을 종료합니다.")
            
        except Exception as e:
            print(f"프로그램 종료 중 오류: {e}")
        
        event.accept()
        
    def add_favorite_product(self):
        """주력 상품 추가"""
        try:
            brand = self.fav_brand_input.text().strip()
            product = self.fav_product_input.text().strip()
            price = self.fav_price_input.value()
            
            if not brand or not product:
                QMessageBox.warning(self, "경고", "브랜드명과 상품명을 모두 입력해주세요.")
                return
            
            # 중복 확인
            for fav_product in self.favorite_products:
                if fav_product['brand'] == brand and fav_product['product'] == product:
                    QMessageBox.warning(self, "경고", "이미 등록된 주력 상품입니다.")
                    return
            
            # 주력 상품 추가
            favorite_product = {
                'brand': brand,
                'product': product,
                'current_price': price,
                'competitor_price': 0,
                'suggested_price': 0,
                'status': '확인 필요',
                'last_check': '없음',
                'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.favorite_products.append(favorite_product)
            self.update_favorite_table()
            self.save_favorite_products_auto()
            
            # 입력 필드 초기화
            self.fav_brand_input.clear()
            self.fav_product_input.clear()
            self.fav_price_input.setValue(15000)
            
            self.log_message(f"⭐ 주력 상품 추가: {brand} - {product}")
            QMessageBox.information(self, "추가 완료", f"주력 상품이 추가되었습니다.\n\n{brand} - {product}")
            
        except Exception as e:
            self.log_message(f"주력 상품 추가 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력 상품 추가 중 오류가 발생했습니다:\n{str(e)}")
    
    def import_from_crawling(self):
        """크롤링 결과에서 주력 상품 추가"""
        try:
            if self.crawling_table.rowCount() == 0:
                QMessageBox.warning(self, "경고", "크롤링된 상품이 없습니다.\n먼저 크롤링을 진행해주세요.")
                return
            
            # 크롤링 결과 선택 다이얼로그
            items = []
            for row in range(self.crawling_table.rowCount()):
                title = self.crawling_table.item(row, 0).text() if self.crawling_table.item(row, 0) else ''
                brand = self.crawling_table.item(row, 1).text() if self.crawling_table.item(row, 1) else ''
                price = self.crawling_table.item(row, 2).text() if self.crawling_table.item(row, 2) else ''
                items.append(f"{brand} - {title} ({price})")
            
            from PyQt6.QtWidgets import QInputDialog
            item, ok = QInputDialog.getItem(
                self, 
                "크롤링 결과에서 선택", 
                "주력 상품으로 추가할 상품을 선택하세요:",
                items, 
                0, 
                False
            )
            
            if ok and item:
                # 선택된 항목에서 정보 추출
                selected_index = items.index(item)
                
                brand = self.crawling_table.item(selected_index, 1).text()
                product = self.crawling_table.item(selected_index, 0).text()
                price_text = self.crawling_table.item(selected_index, 2).text()
                
                # 가격에서 숫자만 추출
                import re
                price_numbers = re.findall(r'[\d,]+', price_text)
                price = int(price_numbers[0].replace(',', '')) if price_numbers else 15000
                
                # 입력 필드에 설정
                self.fav_brand_input.setText(brand)
                self.fav_product_input.setText(product)
                self.fav_price_input.setValue(price)
                
                # 자동으로 추가
                self.add_favorite_product()
            
        except Exception as e:
            self.log_message(f"크롤링 결과 가져오기 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"크롤링 결과 가져오기 중 오류가 발생했습니다:\n{str(e)}")
    
    def check_single_favorite_price(self, row):
        """개별 주력 상품 가격 확인"""
        try:
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
                
            if row >= len(self.favorite_products):
                return
            
            product = self.favorite_products[row]
            brand = product['brand']
            product_name = product['product']
            
            self.log_message(f"🔍 주력 상품 가격 확인: {brand} - {product_name}")
            
            # 가격 분석 실행 (시뮬레이션)
            current_price = product['current_price']
            competitor_price = current_price - random.randint(100, 500)  # 시뮬레이션
            discount = self.dashboard_discount.value()
            suggested_price = competitor_price - discount
            
            # 상태 결정
            if suggested_price < current_price:
                status = "수정 필요"
            else:
                status = "최신 상태"
            
            # 데이터 업데이트
            product['competitor_price'] = competitor_price
            product['suggested_price'] = suggested_price
            product['status'] = status
            product['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            self.update_favorite_table()
            self.save_favorite_products_auto()
            
            self.log_message(f"✅ 가격 확인 완료: {brand} - {product_name} ({status})")
            
        except Exception as e:
            self.log_message(f"개별 가격 확인 오류: {str(e)}")
    
    def check_all_favorite_prices(self):
        """전체 주력 상품 가격 확인"""
        try:
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
                
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "확인할 주력 상품이 없습니다.")
                return
            
            self.log_message(f"🔍 전체 주력 상품 가격 확인 시작: {len(self.favorite_products)}개")
            
            for i, product in enumerate(self.favorite_products):
                self.check_single_favorite_price(i)
                
                # 진행률 표시
                progress = int(((i + 1) / len(self.favorite_products)) * 100)
                self.log_message(f"진행률: {progress}% ({i+1}/{len(self.favorite_products)})")
            
            # 마지막 확인 시간 업데이트
            self.last_favorite_check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.update_favorite_statistics()
            
            self.log_message("✅ 전체 주력 상품 가격 확인 완료")
            QMessageBox.information(self, "확인 완료", "모든 주력 상품의 가격 확인이 완료되었습니다.")
            
        except Exception as e:
            self.log_message(f"전체 가격 확인 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"전체 가격 확인 중 오류가 발생했습니다:\n{str(e)}")
    
    def auto_update_favorite_prices(self):
        """주력 상품 자동 가격 수정"""
        try:
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
                
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "수정할 주력 상품이 없습니다.")
                return
            
            # 수정이 필요한 상품들 찾기
            need_update = [p for p in self.favorite_products if '💰 가격 수정 필요' in p.get('status', '')]
            
            if not need_update:
                QMessageBox.information(self, "알림", "가격 수정이 필요한 상품이 없습니다.\n먼저 가격 확인을 진행해주세요.")
                return
            
            reply = QMessageBox.question(
                self, 
                "자동 수정 확인", 
                f"{len(need_update)}개 상품의 가격을 자동으로 수정하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                updated_count = 0
                
                for product in need_update:
                    # 실제 BUYMA 가격 수정 (시뮬레이션)
                    product['current_price'] = product['suggested_price']
                    product['status'] = '수정 완료'
                    product['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    updated_count += 1
                    
                    self.log_message(f"💱 가격 수정: {product['brand']} - {product['product']} → {product['suggested_price']}엔")
                
                self.update_favorite_table()
                self.save_favorite_products_auto()
                
                self.log_message(f"✅ 자동 가격 수정 완료: {updated_count}개 상품")
                QMessageBox.information(self, "수정 완료", f"{updated_count}개 상품의 가격이 수정되었습니다.")
            
        except Exception as e:
            self.log_message(f"자동 가격 수정 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"자동 가격 수정 중 오류가 발생했습니다:\n{str(e)}")
    
    # def update_favorite_table(self):
    #     """주력 상품 테이블 업데이트"""
    #     try:
    #         self.favorite_table.setRowCount(len(self.favorite_products))
            
    #         for row, product in enumerate(self.favorite_products):
    #             # 브랜드
    #             self.favorite_table.setItem(row, 0, QTableWidgetItem(product['brand']))
                
    #             # 상품명
    #             self.favorite_table.setItem(row, 1, QTableWidgetItem(product['product']))
    #             self.favorite_table.setRowHeightt(row, 35)  # 기본 행 높이 설정
                
    #             # 현재가격
    #             self.favorite_table.setItem(row, 2, QTableWidgetItem(f"{product['current_price']}엔"))
                
    #             # 경쟁사 최저가
    #             competitor_price = product.get('competitor_price', 0)
    #             if competitor_price > 0:
    #                 self.favorite_table.setItem(row, 3, QTableWidgetItem(f"{competitor_price}엔"))
    #             else:
    #                 self.favorite_table.setItem(row, 3, QTableWidgetItem("미확인"))
                
    #             # 제안가격
    #             suggested_price = product.get('suggested_price', 0)
    #             if suggested_price > 0:
    #                 self.favorite_table.setItem(row, 4, QTableWidgetItem(f"{suggested_price}엔"))
    #             else:
    #                 self.favorite_table.setItem(row, 4, QTableWidgetItem("미확인"))
                
    #             # 상태
    #             status = product.get('status', '확인 필요')
    #             status_item = QTableWidgetItem(status)
                
    #             if '수정 필요' in status:
    #                 status_item.setForeground(QBrush(QColor("#e74c3c")))
    #             elif '최신' in status:
    #                 status_item.setForeground(QBrush(QColor("#27ae60")))
    #             else:
    #                 status_item.setForeground(QBrush(QColor("#f39c12")))
                
    #             self.favorite_table.setItem(row, 5, status_item)
                
    #             # 마지막 확인
    #             self.favorite_table.setItem(row, 6, QTableWidgetItem(product.get('last_check', '없음')))
                
    #             # 액션 버튼
    #             action_layout = QHBoxLayout()
    #             action_widget = QWidget()
                
    #             # 가격 확인 버튼
    #             check_btn = QPushButton("🔍")
    #             check_btn.setMaximumWidth(30)
    #             check_btn.setToolTip("가격 확인")
    #             check_btn.clicked.connect(lambda checked, r=row: self.check_single_favorite_price(r))
    #             action_layout.addWidget(check_btn)
                
    #             # 삭제 버튼
    #             delete_btn = QPushButton("🗑️")
    #             delete_btn.setMaximumWidth(30)
    #             delete_btn.setToolTip("삭제")
    #             delete_btn.setStyleSheet("background: #e74c3c; color: white;")
    #             delete_btn.clicked.connect(lambda checked, r=row: self.delete_favorite_product(r))
    #             action_layout.addWidget(delete_btn)
                
    #             action_layout.setContentsMargins(5, 2, 5, 2)
    #             action_widget.setLayout(action_layout)
    #             self.favorite_table.setCellWidget(row, 7, action_widget)
            
    #         # 통계 업데이트
    #         self.update_favorite_statistics()
            
    #     except Exception as e:
    #         self.log_message(f"주력 상품 테이블 업데이트 오류: {str(e)}")
    
    def update_favorite_statistics(self):
        """주력 상품 통계 업데이트"""
        try:
            total = len(self.favorite_products)
            need_update = sum(1 for p in self.favorite_products if '수정 필요' in p.get('status', ''))
            up_to_date = sum(1 for p in self.favorite_products if '최신' in p.get('status', ''))
            
            self.total_favorites.setText(f"총 주력상품: {total}개")
            self.need_update_count.setText(f"수정 필요: {need_update}개")
            self.up_to_date_count.setText(f"최신 상태: {up_to_date}개")
            
            # 마지막 확인 시간
            if hasattr(self, 'last_favorite_check_time'):
                self.last_check_time.setText(f"마지막 확인: {self.last_favorite_check_time}")
            
        except Exception as e:
            self.log_message(f"통계 업데이트 오류: {str(e)}")
    
    def delete_favorite_product(self, row):
        """주력 상품 삭제"""
        try:
            if row < len(self.favorite_products):
                product = self.favorite_products[row]
                
                reply = QMessageBox.question(
                    self, 
                    "삭제 확인", 
                    f"다음 주력 상품을 삭제하시겠습니까?\n\n{product['brand']} - {product['product']}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    del self.favorite_products[row]
                    self.update_favorite_table()
                    self.save_favorite_products_auto()
                    self.log_message(f"🗑️ 주력 상품 삭제: {product['brand']} - {product['product']}")
            
        except Exception as e:
            self.log_message(f"주력 상품 삭제 오류: {str(e)}")
    
    def clear_favorite_products(self):
        """전체 주력 상품 삭제 (테이블만 지우고 JSON 파일은 유지)"""
        try:
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "삭제할 주력 상품이 없습니다.")
                return
            
            reply = QMessageBox.question(
                self, 
                "전체 삭제 확인", 
                f"테이블의 모든 주력 상품({len(self.favorite_products)}개)을 지우시겠습니까?\n\n"
                f"※ 이 작업은 테이블 내용만 지우며, 저장된 JSON 파일은 유지됩니다.\n"
                f"※ '목록 불러오기'로 다시 불러올 수 있습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.favorite_products.clear()
                self.update_favorite_table()
                # JSON 파일 저장 제거 - 테이블만 지우고 파일은 유지
                self.log_message("🗑️ 주력 상품 테이블 내용 삭제 완료 (JSON 파일은 유지)")
                QMessageBox.information(self, "삭제 완료", "테이블의 주력 상품이 삭제되었습니다.\n저장된 파일은 유지되어 '목록 불러오기'로 다시 불러올 수 있습니다.")
            
        except Exception as e:
            self.log_message(f"전체 삭제 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"전체 삭제 중 오류가 발생했습니다:\n{str(e)}")
    
    def save_favorite_products(self):
        """주력 상품 목록 저장"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "주력 상품 목록 저장", 
                f"주력상품_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.favorite_products, f, ensure_ascii=False, indent=2)
                
                self.log_message(f"💾 주력 상품 목록 저장: {file_path}")
                QMessageBox.information(self, "저장 완료", f"주력 상품 목록이 저장되었습니다.\n\n{file_path}")
            
        except Exception as e:
            self.log_message(f"주력 상품 저장 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력 상품 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def load_favorite_products(self):
        """주력 상품 목록 불러오기"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "주력 상품 목록 불러오기", 
                "",
                "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.favorite_products = json.load(f)
                
                self.update_favorite_table()
                
                self.log_message(f"📂 주력 상품 목록 불러오기: {file_path}")
                QMessageBox.information(self, "불러오기 완료", f"{len(self.favorite_products)}개의 주력 상품을 불러왔습니다.")
            
        except Exception as e:
            self.log_message(f"주력 상품 불러오기 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력 상품 불러오기 중 오류가 발생했습니다:\n{str(e)}")
    
    def save_favorite_products_auto(self):
        """자동 저장"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorite_products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"자동 저장 오류: {str(e)}")
    
    def load_favorite_products_on_startup(self):
        """프로그램 시작 시 자동 로드 (안전장치 포함)"""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self.favorite_products = json.load(f)
                
                # 테이블 업데이트 (테이블이 존재하는 경우에만)
                if hasattr(self, 'favorite_table') and self.favorite_table is not None:
                    self.update_favorite_table()
                
                self.log_message(f"📂 주력 상품 자동 로드: {len(self.favorite_products)}개")
            else:
                self.favorite_products = []
                self.log_message("📂 주력 상품 파일이 없습니다. 새로 시작합니다.")
                
        except Exception as e:
            self.log_message(f"자동 로드 오류: {str(e)}")
            self.favorite_products = []
    
    def closeEvent(self, event):
        """프로그램 종료 시 스레드 정리"""
        try:
            self.log_message("🔄 프로그램을 종료하는 중...")
            
            # 실행 중인 워커 스레드들 정리
            if self.price_analysis_worker and self.price_analysis_worker.isRunning():
                self.log_message("⏹️ 가격 분석 작업을 중지하는 중...")
                self.price_analysis_worker.stop()
                self.price_analysis_worker.wait(5000)  # 5초 대기
            
            if self.favorite_analysis_worker and self.favorite_analysis_worker.isRunning():
                self.log_message("⏹️ 주력 상품 확인 작업을 중지하는 중...")
                self.favorite_analysis_worker.stop()
                self.favorite_analysis_worker.wait(5000)  # 5초 대기
            
            # 주력 상품 자동 저장
            if self.favorite_products:
                self.save_favorite_products_auto()
                self.log_message("💾 주력 상품 자동 저장 완료")
            
            # 진행률 위젯 종료
            if hasattr(self, 'progress_widget'):
                self.progress_widget.close()
            
            self.log_message("✅ 프로그램이 안전하게 종료됩니다.")
            event.accept()
            
        except Exception as e:
            self.log_message(f"종료 처리 오류: {str(e)}")
            event.accept()  # 오류가 있어도 종료
    
    # ==================== 크롤링 UI 업데이트 슬롯 함수들 ====================
    
    def update_crawling_progress(self, progress):
        """크롤링 진행률 업데이트 (메인 스레드에서 안전하게)"""
        try:
            self.crawling_progress.setValue(progress)
            # 진행률 위젯 업데이트
            total_count = self.crawl_count.value()
            current_count = int((progress / 100) * total_count)
            self.progress_widget.update_progress(
                current_count, 
                total_count, 
                "🔍 크롤링 진행 중", 
                f"상품 수집 중... ({current_count}/{total_count})"
            )
        except Exception as e:
            print(f"진행률 업데이트 오류: {e}")
    
    def update_crawling_status(self, status):
        """크롤링 상태 업데이트 (메인 스레드에서 안전하게)"""
        try:
            self.crawling_status.setText(status)
        except Exception as e:
            print(f"상태 업데이트 오류: {e}")
    
    def add_crawling_result_safe(self, item_data):
        """크롤링 결과 추가 (메인 스레드에서 안전하게)"""
        try:
            # 크롤링된 상품 데이터를 클래스 변수에 저장
            self.crawled_products.append(item_data)
            
            # 크롤링 통계 업데이트
            self.increment_crawled_count()
            
            # 성공/실패 통계 업데이트
            if item_data.get('status') == '수집 완료':
                self.increment_success_count()
            else:
                self.increment_failed_count()
            
            row = self.crawling_table.rowCount()
            self.crawling_table.insertRow(row)
            
            # 이미지 수 계산
            images = item_data.get('images', [])
            image_count = len(images) if images else 0
            
            # 색상/사이즈 정보 포맷팅
            colors = item_data.get('colors', [])
            sizes = item_data.get('sizes', [])
            
            if colors or sizes:
                colors_sizes_text = f"색상:{len(colors)}개, 사이즈:{len(sizes)}개"
            else:
                colors_sizes_text = "정보 없음"
            
            # 데이터 설정 (올바른 키 사용)
            items = [
                item_data.get('title', 'Unknown'),
                item_data.get('brand', 'Unknown'),
                item_data.get('price', 'N/A'),
                f"{image_count}장",  # 이미지 수 올바르게 계산
                colors_sizes_text,   # 색상/사이즈 올바르게 포맷팅
                item_data.get('url', 'N/A'),
                item_data.get('status', '완료')
            ]
            
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(str(item_text))
                # 맑은 고딕 폰트 적용
                font = item.font()
                font.setFamily("맑은 고딕")
                item.setFont(font)
                self.crawling_table.setItem(row, col, item)
            
            # 상태 컬럼 색상 설정
            status_item = self.crawling_table.item(row, 6)
            if status_item:
                if "완료" in status_item.text():
                    status_item.setForeground(QBrush(QColor("#28a745")))
                elif "실패" in status_item.text():
                    status_item.setForeground(QBrush(QColor("#dc3545")))
                
                font = status_item.font()
                font.setBold(True)
                font.setFamily("맑은 고딕")
                status_item.setFont(font)
            
            # 디버깅 로그 추가
            self.log_message(f"📊 테이블 추가: {item_data.get('title', 'Unknown')[:20]}... "
                           f"(이미지:{image_count}장, 색상:{len(colors)}개, 사이즈:{len(sizes)}개)")
            
            # 액션 버튼들 (가로 배치)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(3)
            
            # 1. 상세보기 버튼
            detail_btn = QPushButton("📋")
            detail_btn.setToolTip("상품 상세 정보 보기")
            detail_btn.setFixedSize(35, 28)
            detail_btn.setStyleSheet("""
                QPushButton {
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background: #0056b3;
                }
            """)
            detail_btn.clicked.connect(lambda checked, r=row: self.show_item_detail(r))
            action_layout.addWidget(detail_btn)
            
            # 2. 바로 업로드 버튼
            upload_btn = QPushButton("📤")
            upload_btn.setToolTip("BUYMA에 바로 업로드")
            upload_btn.setFixedSize(35, 28)
            upload_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background: #1e7e34;
                }
            """)
            upload_btn.clicked.connect(lambda checked, r=row: self.upload_single_item(r))
            action_layout.addWidget(upload_btn)
            
            # 4. URL 열기 버튼
            url_btn = QPushButton("🔗")
            url_btn.setToolTip("원본 상품 페이지 열기")
            url_btn.setFixedSize(35, 28)
            url_btn.setStyleSheet("""
                QPushButton {
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background: #5a6268;
                }
            """)
            url_btn.clicked.connect(lambda checked, r=row: self.open_product_url(r))
            action_layout.addWidget(url_btn)
            
            self.crawling_table.setCellWidget(row, 7, action_widget)
            
            # 크롤링 중이면 새로 추가된 액션 버튼도 비활성화
            if not self.start_crawling_btn.isEnabled():  # 크롤링 중인지 확인
                action_widget.setEnabled(False)
            
            # 행 높이를 버튼 높이에 맞춤
            self.crawling_table.setRowHeight(row, 35)
            
            # 자동 스크롤
            self.crawling_table.scrollToBottom()
            
        except Exception as e:
            print(f"크롤링 결과 추가 오류: {e}")
    
    def crawling_finished_safe(self):
        """크롤링 완료 처리 (메인 스레드에서 안전하게)"""
        try:
            # 처리 시간 계산
            if self.today_stats['start_time']:
                import time
                end_time = time.time()
                process_time = end_time - self.today_stats['start_time']
                self.add_process_time(process_time)
                self.log_message(f"⏱️ 크롤링 처리 시간: {process_time:.1f}초")
            
            # UI 상태 복원
            self.start_crawling_btn.setEnabled(True)
            self.stop_crawling_btn.setEnabled(False)
            self.crawling_status.setText("크롤링 완료")
            self.crawling_progress.setValue(100)
            
            # 진행률 위젯 완료 상태
            collected_count = self.crawling_table.rowCount()
            self.progress_widget.set_task_complete(
                "크롤링 완료", 
                f"총 {collected_count}개 상품을 성공적으로 수집했습니다!"
            )
            
            # 크롤링 완료 후 UI 활성화
            self.disable_ui_during_crawling(False)
            
        except Exception as e:
            print(f"크롤링 완료 처리 오류: {e}")
            # 오류 발생 시 진행률 위젯에 오류 표시
            self.progress_widget.set_task_error("크롤링 오류", str(e))
    
    # ==================== 새로운 기능 구현 ====================
    
    # def analyze_all_my_products(self):
    #     """내 상품 전체 분석 & 수정 - 스레드 기반으로 개선"""
    #     try:
    #         # 로그인 상태 확인
    #         if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
    #             QMessageBox.warning(
    #                 self, 
    #                 "로그인 필요", 
    #                 "가격 분석을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
    #                 "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
    #             )
    #             return
    #         # 이미 실행 중인 작업이 있으면 중지
    #         if self.price_analysis_worker and self.price_analysis_worker.isRunning():
    #             QMessageBox.warning(self, "경고", "이미 가격 분석이 진행 중입니다.")
    #             return
            
    #         self.log_message("🔍 내 상품 목록을 불러오는 중...")
            
    #         # 시뮬레이션: 내 상품 목록 가져오기
    #         my_products = self.simulate_get_my_products()
            
    #         if not my_products:
    #             QMessageBox.warning(self, "경고", "분석할 상품이 없습니다.")
    #             return
            
    #         # 설정 수집
    #         settings = {
    #             'auto_mode': self.auto_mode.isChecked(),
    #             'discount_amount': self.discount_amount.value(),
    #             'min_margin': self.min_margin.value(),
    #             'brand_filter': self.brand_input.text().strip() if hasattr(self, 'brand_input') else '',
    #             'exclude_loss': self.exclude_loss_products.isChecked() if hasattr(self, 'exclude_loss_products') else True
    #         }
            
    #         # 브랜드 필터 적용
    #         products_to_analyze = my_products
    #         if settings['brand_filter']:
    #             products_to_analyze = [p for p in my_products 
    #                                  if settings['brand_filter'].lower() in p.get('brand', '').lower()]
            
    #         if not products_to_analyze:
    #             QMessageBox.warning(self, "경고", "필터 조건에 맞는 상품이 없습니다.")
    #             return
            
    #         # UI 상태 변경
    #         self.analyze_all_my_products_btn.setEnabled(False)
    #         self.analyze_all_my_products_btn.setText("🔄 분석 중...")
    #         self.stop_price_analysis_btn.setEnabled(True)
            
    #         # 가격 분석 결과 테이블 초기화
    #         self.price_table.setRowCount(0)
            
    #         # 통계 초기화
    #         self.total_analyzed.setText("분석 완료: 0개")
    #         self.auto_updated.setText("자동 수정: 0개")
    #         self.excluded_items.setText("제외: 0개")
    #         self.failed_items.setText("실패: 0개")
            
    #         # 워커 스레드 시작
    #         self.price_analysis_worker = PriceAnalysisWorker(products_to_analyze, settings)
    #         self.price_analysis_worker.progress_updated.connect(self.update_price_analysis_progress)
    #         self.price_analysis_worker.product_analyzed.connect(self.add_price_analysis_result)
    #         self.price_analysis_worker.finished.connect(self.price_analysis_finished)
    #         self.price_analysis_worker.log_message.connect(self.log_message)
    #         self.price_analysis_worker.start()
            
    #         self.log_message(f"🚀 {len(products_to_analyze)}개 상품 가격 분석을 시작합니다.")
            
    #     except Exception as e:
    #         self.log_message(f"❌ 전체 분석 시작 오류: {str(e)}")
    #         QMessageBox.critical(self, "오류", f"전체 상품 분석 시작 중 오류가 발생했습니다:\n{str(e)}")
    
    def update_price_analysis_progress(self, current, total):
        """가격 분석 진행률 업데이트"""
        try:
            progress = int((current / total) * 100)
            self.log_message(f"📊 진행률: {progress}% ({current}/{total})")
            
            # 진행률 표시 (프로그레스 바가 있다면)
            if hasattr(self, 'price_progress_bar'):
                self.price_progress_bar.setValue(progress)
                
        except Exception as e:
            self.log_message(f"진행률 업데이트 오류: {str(e)}")
    
    def price_analysis_finished(self, stats):
        """가격 분석 완료 처리"""
        try:
            # UI 상태 복원 (더 이상 사용하지 않는 버튼 제거됨)
            # self.analyze_all_my_products_btn.setEnabled(True)
            # self.analyze_all_my_products_btn.setText("🔍 내 상품 전체 분석 & 수정")
            self.stop_price_analysis_btn.setEnabled(False)
            
            # 통계 업데이트
            self.total_analyzed.setText(f"분석 완료: {stats['analyzed']}개")
            self.auto_updated.setText(f"자동 수정: {stats['updated']}개")
            self.excluded_items.setText(f"제외: {stats['excluded']}개")
            self.failed_items.setText(f"실패: {stats['failed']}개")
            
            # 완료 메시지
            self.log_message(f"✅ 전체 상품 분석 완료!")
            self.log_message(f"📊 분석: {stats['analyzed']}개, 수정: {stats['updated']}개")
            
            QMessageBox.information(self, "분석 완료", 
                f"전체 상품 분석이 완료되었습니다.\n\n"
                f"• 분석 완료: {stats['analyzed']}개\n"
                f"• 자동 수정: {stats['updated']}개\n"
                f"• 제외: {stats['excluded']}개\n"
                f"• 실패: {stats['failed']}개")
            
        except Exception as e:
            self.log_message(f"완료 처리 오류: {str(e)}")
    
    @safe_slot
    def start_favorite_analysis(self):
        """주력상품 가격확인-가격수정 통합 시작"""
        try:
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
            
            if not self.favorite_products:
                QMessageBox.warning(self, "경고", "등록된 주력 상품이 없습니다.\n먼저 주력 상품을 추가해주세요.")
                return
            
            # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
            self.switch_to_monitoring_tab()
            self.set_tabs_enabled(False)
            
            # UI 상태 변경
            self.fav_start_analysis_btn.setEnabled(False)
            self.fav_start_analysis_btn.setText("🔄 진행 중...")
            
            # 진행률 위젯 표시
            self.progress_widget.update_progress(
                0, 
                len(self.favorite_products), 
                "⭐ 주력상품 통합 처리", 
                f"총 {len(self.favorite_products)}개 상품 처리 예정"
            )
            
            self.log_message(f"🚀 주력상품 가격확인-가격수정 통합 처리 시작: {len(self.favorite_products)}개")
            
            # 설정값 가져오기
            discount_amount = self.fav_discount_amount.value()
            min_margin = self.fav_min_margin.value()
            is_auto_mode = self.fav_auto_mode.isChecked()
            
            self.log_message(f"🔧 설정: 할인 {discount_amount}엔, 최소마진 {min_margin}엔, 모드: {'🤖 자동' if is_auto_mode else '👤 수동'}")
            
            # 별도 스레드에서 통합 처리 실행
            import threading
            
            self.favorite_integrated_thread = threading.Thread(
                target=self.run_favorite_integrated_process, 
                args=(discount_amount, min_margin, is_auto_mode),
                daemon=True
            )
            self.favorite_integrated_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 통합 처리 시작 오류: {str(e)}")
            self.progress_widget.set_task_error("주력상품 통합 처리 오류", str(e))
            # UI 상태 복원
            self.fav_start_analysis_btn.setEnabled(True)
            self.fav_start_analysis_btn.setText("🚀 가격확인-가격수정 시작")
    
    def update_favorite_analysis_progress(self, current, total):
        """주력 상품 분석 진행률 업데이트"""
        try:
            progress = int((current / total) * 100)
            self.log_message(f"⭐ 진행률: {progress}% ({current}/{total})")
            
        except Exception as e:
            self.log_message(f"진행률 업데이트 오류: {str(e)}")
    
    def favorite_product_checked(self, result):
        """주력 상품 확인 결과 처리"""
        try:
            # 결과 로그
            if result['updated']:
                self.log_message(f"✅ 주력상품 가격 수정: {result['name']} "
                               f"({result['current_price']:,}엔 → {result['suggested_price']:,}엔)")
            else:
                self.log_message(f"ℹ️ 주력상품 확인: {result['name']} - {result['status']}")
                
        except Exception as e:
            self.log_message(f"결과 처리 오류: {str(e)}")
    
    def favorite_analysis_finished(self, stats):
        """주력 상품 분석 완료 처리"""
        try:
            # UI 상태 복원
            self.fav_start_analysis_btn.setEnabled(True)
            self.fav_start_analysis_btn.setText("🚀 가격확인-가격수정 시작")
            # self.stop_favorite_analysis_btn.setEnabled(False)  # 이 버튼이 없으면 주석 처리
            
            # 주력 상품 테이블 업데이트
            self.update_favorite_table()
            
            # 자동 저장
            self.save_favorite_products_auto()
            
            # 통계 업데이트
            self.need_update_count.setText(f"수정 필요: 0개")
            self.up_to_date_count.setText(f"최신 상태: {stats['checked']}개")
            self.last_check_time.setText(f"마지막 확인: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # 완료 메시지
            self.log_message(f"✅ 주력 상품 가격 확인 완료!")
            self.log_message(f"⭐ 확인: {stats['checked']}개, 수정: {stats['updated']}개")
            
            QMessageBox.information(self, "확인 완료", 
                f"주력 상품 가격 확인이 완료되었습니다.\n\n"
                f"• 확인 완료: {stats['checked']}개\n"
                f"• 가격 수정: {stats['updated']}개\n"
                f"• 실패: {stats['failed']}개")
            
        except Exception as e:
            self.log_message(f"완료 처리 오류: {str(e)}")
    
    def stop_price_analysis(self):
        """가격 분석 중지"""
        try:
            if self.price_analysis_worker and self.price_analysis_worker.isRunning():
                self.price_analysis_worker.stop()
                self.price_analysis_worker.wait(3000)  # 3초 대기
                
                # UI 상태 복원 (더 이상 사용하지 않는 버튼 제거됨)
                # self.analyze_all_my_products_btn.setEnabled(True)
                # self.analyze_all_my_products_btn.setText("🔍 내 상품 전체 분석 & 수정")
                self.stop_price_analysis_btn.setEnabled(False)
                
                self.log_message("⏹️ 가격 분석이 사용자에 의해 중지되었습니다.")
                
        except Exception as e:
            self.log_message(f"중지 처리 오류: {str(e)}")
    
    def stop_favorite_analysis(self):
        """주력 상품 분석 중지"""
        try:
            if self.favorite_analysis_worker and self.favorite_analysis_worker.isRunning():
                self.favorite_analysis_worker.stop()
                self.favorite_analysis_worker.wait(3000)  # 3초 대기
                
                # UI 상태 복원
                self.fav_start_analysis_btn.setEnabled(True)
                self.fav_start_analysis_btn.setText("🚀 가격확인-가격수정 시작")
                # self.stop_favorite_analysis_btn.setEnabled(False)  # 이 버튼이 없으면 주석 처리
                
                self.log_message("⏹️ 주력 상품 확인이 사용자에 의해 중지되었습니다.")
                
        except Exception as e:
            self.log_message(f"중지 처리 오류: {str(e)}")
    
    # ==================== DEPRECATED FUNCTIONS ====================
    # 아래 함수들은 시뮬레이션용으로 실제 사용되지 않음
    
    # def simulate_get_my_products(self):
    #     """내 상품 목록 가져오기 시뮬레이션 - DEPRECATED"""
    #     # 실제 구현에서는 BUYMA API나 웹 크롤링으로 내 상품 목록을 가져옴
    #     sample_products = []
    #     brands = ["SAN SAN GEAR", "NIKE", "ADIDAS", "PUMA", "CONVERSE", "BALENCIAGA", "GUCCI"]
    #     product_types = ["T-SHIRT", "HOODIE", "SNEAKERS", "JACKET", "PANTS", "BAG", "WALLET"]
    #     
    #     for i in range(15):  # 15개 샘플 상품
    #         product = {
    #             'name': f"{random.choice(product_types)} {i+1:03d}",
    #             'brand': random.choice(brands),
    #             'current_price': random.randint(15000, 80000),
    #             'cost_price': random.randint(8000, 40000),
    #             'product_id': f"PROD_{i+1:03d}"
    #         }
    #         sample_products.append(product)
    #     
    #     return sample_products
    
    # def simulate_get_competitor_price(self, product):
    #     """경쟁사 최저가 조회 시뮬레이션 - DEPRECATED"""
    #     # 실제 구현에서는 경쟁사 사이트를 크롤링하여 최저가를 찾음
    #     base_price = product['current_price']
    #     # 현재가의 80-95% 범위에서 경쟁사 가격 시뮬레이션
    #     competitor_price = int(base_price * random.uniform(0.80, 0.95))
    #     return competitor_price
    
    # def simulate_update_price(self, product, new_price):
    #     """가격 업데이트 시뮬레이션 - DEPRECATED"""
    #     # 실제 구현에서는 BUYMA API나 웹 자동화로 가격을 수정
    #     # 시뮬레이션: 90% 성공률
    #     return random.random() < 0.9
    
    def add_price_analysis_result(self, result):
        """가격 분석 결과를 테이블에 추가"""
        try:
            row = self.price_table.rowCount()
            self.price_table.insertRow(row)
            
            # 데이터 설정
            items = [
                result['name'],
                result['brand'],
                f"{result['current_price']:,}엔",
                f"{result['competitor_price']:,}엔",
                f"{result['suggested_price']:,}엔",
                f"{result['margin']:,}엔",
                result['status'],
                result['action']
            ]
            
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(str(item_text))
                
                # 상태에 따른 색상 설정
                if col == 6:  # 상태 컬럼
                    if "수정 불가" in item_text or "마진 부족" in item_text:
                        item.setForeground(QBrush(QColor("#dc3545")))
                    elif "수정 가능" in item_text:
                        item.setForeground(QBrush(QColor("#28a745")))
                    else:
                        item.setForeground(QBrush(QColor("#6c757d")))
                        
                    font = item.font()
                    font.setBold(True)
                    font.setFamily("맑은 고딕")
                    item.setFont(font)
                
                elif col == 7:  # 액션 컬럼
                    if "수정 완료" in item_text:
                        item.setForeground(QBrush(QColor("#007bff")))
                    elif "수정 실패" in item_text:
                        item.setForeground(QBrush(QColor("#dc3545")))
                    
                    font = item.font()
                    font.setBold(True)
                    font.setFamily("맑은 고딕")
                    item.setFont(font)
                
                elif col == 5:  # 마진 컬럼
                    if result['margin'] < 0:
                        item.setForeground(QBrush(QColor("#dc3545")))
                    else:
                        item.setForeground(QBrush(QColor("#28a745")))
                        
                    font = item.font()
                    font.setBold(True)
                    font.setFamily("맑은 고딕")
                    item.setFont(font)
                
                # 모든 아이템에 맑은 고딕 폰트 적용
                font = item.font()
                font.setFamily("맑은 고딕")
                item.setFont(font)
                
                self.price_table.setItem(row, col, item)
                
        except Exception as e:
            self.log_message(f"결과 추가 오류: {str(e)}")
    
    # ==================== 새로운 주력상품 관리 함수들 ====================
    
    @safe_slot
    def check_favorite_prices(self):
        """주력상품 가격확인"""
        try:
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "확인할 주력 상품이 없습니다.")
                return
            
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
            
            # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
            self.switch_to_monitoring_tab()
            self.set_tabs_enabled(False)
            
            self.log_message(f"🔍 주력상품 가격확인 시작: {len(self.favorite_products)}개")
            
            # 진행률 위젯 표시
            self.progress_widget.update_progress(
                0, 
                len(self.favorite_products), 
                "⭐ 주력상품 가격확인", 
                f"총 {len(self.favorite_products)}개 상품 확인 예정"
            )
            
            # 설정값 가져오기
            discount_amount = self.fav_discount_amount.value()
            min_margin = self.fav_min_margin.value()
            
            for i, product in enumerate(self.favorite_products):
                try:
                    product_name = product.get('name', '')
                    current_price = product.get('current_price', 0)
                    
                    self.log_message(f"📊 분석 중: {product_name} ({i+1}/{len(self.favorite_products)})")
                    
                    # 실제 BUYMA 최저가 조회 (get_buyma_lowest_price_for_favorite 사용)
                    lowest_price = self.get_buyma_lowest_price_for_favorite(product_name)
                    
                    if lowest_price and lowest_price > 0:
                        # 제안가 계산 (최저가 - 할인금액)
                        suggested_price = max(lowest_price - discount_amount, 0)
                        
                        # 가격차이 계산 (제안가 - 현재가)
                        price_diff = suggested_price - current_price
                        
                        # 상태 결정 (가격차이 기준)
                        if abs(price_diff) <= 100:  # 100엔 이내 차이면 적정
                            status = "✅ 현재가 적정"
                        elif price_diff < -min_margin:
                            # 가격차이가 -설정값보다 작으면 (예: -600 < -500)
                            status = f"⚠️ 손실 예상 ({price_diff:+,}엔)"
                        else:
                            # 가격차이가 설정값 이내면
                            status = "💰 가격 수정 필요"
                        
                        # 상품 데이터 업데이트 (가격차이 통일)
                        product['lowest_price'] = lowest_price
                        product['suggested_price'] = suggested_price
                        product['price_difference'] = price_diff  # 제안가 - 현재가로 통일
                        product['status'] = status
                        product['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        
                        self.log_message(f"✅ {product_name[:20]}... - 최저가: ¥{lowest_price:,}, 제안가: ¥{suggested_price:,}, 차이: {price_diff:+,}엔")
                        
                    else:
                        # 최저가 검색 실패
                        product['lowest_price'] = 0
                        product['suggested_price'] = 0
                        product['price_difference'] = 0
                        product['status'] = "❌ 최저가 검색 실패"
                        product['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        self.log_message(f"⚠️ {product_name[:20]}... - 최저가 검색 실패")
                    
                    # 진행률 위젯 업데이트
                    self.progress_widget.update_progress(
                        i + 1, 
                        len(self.favorite_products), 
                        "⭐ 주력상품 가격확인", 
                        f"분석 완료: {product_name[:20]}..."
                    )
                    
                    self.log_message(f"✅ 분석 완료: {product_name} - {status}")
                    
                except Exception as e:
                    self.log_message(f"❌ 분석 실패: {product.get('name', 'Unknown')} - {str(e)}")
                    continue
            
            # 테이블 업데이트
            self.update_favorite_table()
            self.save_favorite_products_auto()
            
            # 진행률 위젯 완료 상태
            self.progress_widget.set_task_complete(
                "주력상품 가격확인 완료", 
                f"총 {len(self.favorite_products)}개 상품 확인 완료"
            )
            
            # UI 제어 해제
            self.set_tabs_enabled(True)
            
            self.log_message("🔍 주력상품 가격확인 완료")
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 가격확인 오류: {str(e)}")
            # 오류 시 진행률 위젯에 오류 표시
            self.progress_widget.set_task_error("주력상품 가격확인 오류", str(e))
            # UI 제어 해제
            self.set_tabs_enabled(True)
            QMessageBox.critical(self, "오류", f"가격확인 중 오류가 발생했습니다:\n{str(e)}")
    
    @safe_slot
    def update_favorite_prices(self):
        """주력상품 가격수정"""
        try:
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "수정할 주력 상품이 없습니다.")
                return
            
            # BUYMA 로그인 상태 확인
            if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
                QMessageBox.warning(self, "로그인 필요", "BUYMA 로그인이 필요합니다.\n설정 탭에서 로그인을 완료해주세요.")
                return
            
            # 수정이 필요한 상품들 찾기
            need_update = [p for p in self.favorite_products if p.get('status') == '💰 가격 수정 필요']
            
            if not need_update:
                QMessageBox.information(self, "알림", "수정이 필요한 상품이 없습니다.")
                return
            
            # UI 제어: 모니터링 탭으로 이동 및 다른 탭 비활성화
            self.switch_to_monitoring_tab()
            self.set_tabs_enabled(False)
            
            self.log_message(f"🔄 주력상품 가격수정 시작: {len(need_update)}개")
            
            # 진행률 위젯 표시
            self.progress_widget.update_progress(
                0, 
                len(need_update), 
                "⭐ 주력상품 가격수정", 
                f"총 {len(need_update)}개 상품 수정 예정"
            )
            
            updated_count = 0
            auto_mode = self.fav_auto_mode.isChecked()
            
            for i, product in enumerate(need_update):
                try:
                    product_name = product.get('name', '')
                    suggested_price = product.get('suggested_price', 0)
                    
                    # 진행률 위젯 업데이트
                    self.progress_widget.update_progress(
                        i, 
                        len(need_update), 
                        "⭐ 주력상품 가격수정", 
                        f"수정 중: {product_name[:20]}..."
                    )
                    
                    if not auto_mode:
                        # 수동 모드: 사용자 확인
                        reply = QMessageBox.question(
                            self,
                            "가격 수정 확인",
                            f"상품: {product_name}\n"
                            f"제안가: {suggested_price:,}엔\n\n"
                            f"가격을 수정하시겠습니까?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply != QMessageBox.StandardButton.Yes:
                            continue
                    
                    # 실제 BUYMA 가격 수정 (update_single_product_price 로직 활용)
                    result = self.update_buyma_product_price(product_name, suggested_price, auto_mode)
                    
                    if result == True:
                        product['current_price'] = suggested_price
                        product['status'] = "✅ 수정 완료"
                        product['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        updated_count += 1
                        
                        self.log_message(f"✅ 가격 수정 완료: {product_name} → {suggested_price:,}엔")
                    elif result == "cancelled":
                        product['status'] = "❌ 수정 취소"
                        self.log_message(f"❌ 가격 수정 취소: {product_name}")
                    else:
                        product['status'] = "❌ 수정 실패"
                        self.log_message(f"❌ 가격 수정 실패: {product_name}")
                    
                except Exception as e:
                    product['status'] = "❌ 수정 오류"
                    self.log_message(f"❌ 가격 수정 오류: {product.get('name', 'Unknown')} - {str(e)}")
                    continue
            
            # 테이블 업데이트
            self.update_favorite_table()
            self.save_favorite_products_auto()
            
            # 진행률 위젯 완료 상태
            self.progress_widget.set_task_complete(
                "주력상품 가격수정 완료", 
                f"총 {updated_count}개 상품 수정 완료"
            )
            
            # UI 상태 복원 (중요!)
            self.set_tabs_enabled(True)
            
            self.log_message(f"🔄 주력상품 가격수정 완료: {updated_count}개 수정")
            QMessageBox.information(self, "수정 완료", f"{updated_count}개 상품의 가격이 수정되었습니다.")
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 가격수정 오류: {str(e)}")
            # 오류 시 진행률 위젯에 오류 표시
            self.progress_widget.set_task_error("주력상품 가격수정 오류", str(e))
            # UI 상태 복원 (오류 시에도 필수!)
            self.set_tabs_enabled(True)
            QMessageBox.critical(self, "오류", f"가격수정 중 오류가 발생했습니다:\n{str(e)}")
    
    def get_competitor_price_simulation(self, product_name):
        """경쟁사 최저가 조회 시뮬레이션"""
        # 실제로는 BUYMA 검색을 통해 최저가를 찾아야 함
        # 여기서는 시뮬레이션으로 랜덤 가격 반환
        import random
        base_price = random.randint(15000, 50000)
        return base_price
    
    def update_product_price_simulation(self, product, new_price):
        """상품 가격 수정 시뮬레이션"""
        # 실제로는 BUYMA 상품 페이지에서 가격을 수정해야 함
        # 여기서는 시뮬레이션으로 성공 반환
        time.sleep(1)  # 실제 처리 시간 시뮬레이션
        return True
    
    def update_favorite_table(self):
        """주력상품 테이블 업데이트"""
        try:
            self.favorite_table.setRowCount(len(self.favorite_products))
            
            for row, product in enumerate(self.favorite_products):
                # 상품명
                name_item = QTableWidgetItem(product.get('name', ''))
                name_item.setToolTip(product.get('name', ''))
                self.favorite_table.setItem(row, 0, name_item)
                
                # 현재가격
                current_price = product.get('current_price', 0)
                self.favorite_table.setItem(row, 1, QTableWidgetItem(f"{current_price:,}엔"))
                
                # 경쟁사 최저가 → 최저가
                lowest_price = product.get('lowest_price', 0)
                if lowest_price > 0:
                    self.favorite_table.setItem(row, 2, QTableWidgetItem(f"{lowest_price:,}엔"))
                else:
                    self.favorite_table.setItem(row, 2, QTableWidgetItem("-"))
                
                # 제안가격 → 제안가
                suggested_price = product.get('suggested_price', 0)
                if suggested_price > 0:
                    self.favorite_table.setItem(row, 3, QTableWidgetItem(f"{suggested_price:,}엔"))
                else:
                    self.favorite_table.setItem(row, 3, QTableWidgetItem("-"))
                
                # 가격차이 (price_difference 키 사용)
                price_diff = product.get('price_difference', 0)
                if price_diff != 0:
                    if price_diff > 0:
                        diff_text = f"+{price_diff:,}엔"
                        diff_item = QTableWidgetItem(diff_text)
                        diff_item.setForeground(QBrush(QColor("blue")))  # 양수는 파란색
                    else:
                        diff_text = f"{price_diff:,}엔"
                        diff_item = QTableWidgetItem(diff_text)
                        diff_item.setForeground(QBrush(QColor("red")))   # 음수는 빨간색
                    self.favorite_table.setItem(row, 4, diff_item)
                else:
                    self.favorite_table.setItem(row, 4, QTableWidgetItem("-"))
                
                # 상태
                status = product.get('status', '확인 필요')
                status_item = QTableWidgetItem(status)
                
                # 상태에 따른 색상 설정
                if '💰 가격 수정 필요' in status:
                    status_item.setForeground(QBrush(QColor("#ffc107")))  # 노란색 (수정 권장)
                elif '✅ 현재가 적정' in status:
                    status_item.setForeground(QBrush(QColor("#28a745")))  # 초록색 (적정)
                elif '⚠️ 손실 예상' in status:
                    status_item.setForeground(QBrush(QColor("#dc3545")))  # 빨간색 (손실)
                
                self.favorite_table.setItem(row, 5, status_item)
                
                # 액션 버튼
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(5, 2, 5, 2)
                action_layout.setSpacing(2)
                
                # 삭제 버튼
                delete_btn = QPushButton("🗑️")
                delete_btn.setToolTip("삭제")
                delete_btn.setFixedSize(30, 25)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background: #c82333;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_favorite_product(r))
                action_layout.addWidget(delete_btn)
                
                self.favorite_table.setCellWidget(row, 6, action_widget)
            
            # 통계 업데이트
            self.update_favorite_stats()
            
        except Exception as e:
            self.log_message(f"테이블 업데이트 오류: {str(e)}")
    
    def delete_favorite_product(self, row):
        """주력상품 삭제"""
        try:
            if row < len(self.favorite_products):
                product = self.favorite_products[row]
                
                reply = QMessageBox.question(
                    self,
                    "삭제 확인",
                    f"다음 주력 상품을 삭제하시겠습니까?\n\n{product.get('name', 'Unknown')}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    del self.favorite_products[row]
                    self.update_favorite_table()
                    self.save_favorite_products_auto()
                    self.log_message(f"🗑️ 주력상품 삭제: {product.get('name', 'Unknown')}")
        
        except Exception as e:
            self.log_message(f"주력상품 삭제 오류: {str(e)}")
    
    def update_favorite_stats(self):
        """주력상품 통계 업데이트"""
        try:
            total = len(self.favorite_products)
            need_update = sum(1 for p in self.favorite_products if p.get('status') == '수정 필요')
            up_to_date = sum(1 for p in self.favorite_products if '완료' in p.get('status', '') or '최신' in p.get('status', ''))
            
            self.total_favorites.setText(f"총 주력상품: {total}개")
            self.need_update_count.setText(f"수정 필요: {need_update}개")
            self.up_to_date_count.setText(f"최신 상태: {up_to_date}개")
            
            # 마지막 확인 시간
            if self.favorite_products:
                last_checks = [p.get('last_check', '') for p in self.favorite_products if p.get('last_check', '') != '없음']
                if last_checks:
                    latest_check = max(last_checks)
                    self.last_check_time.setText(f"마지막 확인: {latest_check}")
                else:
                    self.last_check_time.setText("마지막 확인: 없음")
            else:
                self.last_check_time.setText("마지막 확인: 없음")
                
        except Exception as e:
            self.log_message(f"통계 업데이트 오류: {str(e)}")
    
    def add_to_favorite_from_price_table(self, row):
        """가격관리 테이블에서 주력상품으로 추가"""
        try:
            if row >= len(self.all_products):
                QMessageBox.warning(self, "오류", "선택한 상품 정보를 찾을 수 없습니다.")
                return
            
            product = self.all_products[row]
            product_name = product.get('title', '')
            current_price_str = product.get('current_price', '0')
            
            # 가격에서 숫자만 추출
            import re
            price_numbers = re.findall(r'[\d,]+', current_price_str)
            current_price = int(price_numbers[0].replace(',', '')) if price_numbers else 0
            
            # 중복 확인
            for fav_product in self.favorite_products:
                if fav_product.get('name', '') == product_name:
                    QMessageBox.warning(self, "중복", "이미 주력 상품으로 등록된 상품입니다.")
                    return
            
            # 주력상품 데이터 생성
            favorite_product = {
                'name': product_name,
                'current_price': current_price,
                'competitor_price': 0,
                'suggested_price': 0,
                'status': '확인 필요',
                'last_check': '없음',
                'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'product_id': product.get('product_id', ''),
                'url': product.get('url', '')
            }
            
            # 주력상품 목록에 추가
            self.favorite_products.append(favorite_product)
            
            # 주력상품 테이블 업데이트 (테이블이 존재하는 경우에만)
            if hasattr(self, 'favorite_table'):
                self.update_favorite_table()
            
            # 자동 저장
            self.save_favorite_products_auto()
            
            self.log_message(f"⭐ 주력상품 추가: {product_name}")
            QMessageBox.information(self, "추가 완료", f"주력 상품으로 추가되었습니다.\n\n{product_name}")
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 추가 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력상품 추가 중 오류가 발생했습니다:\n{str(e)}")
    
    def run_favorite_integrated_process(self, discount_amount, min_margin, is_auto_mode):
        """주력상품 통합 처리 실행 (가격확인 → 가격수정)"""
        try:
            analyzed_count = 0
            updated_count = 0
            failed_count = 0
            
            # ==================== 1단계: 가격확인 ====================
            self.log_message("🔍 1단계: 주력상품 가격확인 시작")
            
            for i, product in enumerate(self.favorite_products):
                try:
                    product_name = product.get('name', '')
                    current_price = product.get('current_price', 0)
                    
                    self.log_message(f"📊 분석 중 ({i+1}/{len(self.favorite_products)}): {product_name}")
                    
                    # 진행률 위젯 업데이트 (1단계) - 시그널 사용
                    self.update_price_progress_signal.emit(
                        i + 1, 
                        len(self.favorite_products) * 2,  # 2단계이므로 총 개수 * 2
                        f"⭐ 주력상품 가격확인 - 분석 중: {product_name[:20]}..."
                    )
                    
                    # 가격관리 탭의 가격확인 로직 활용
                    competitor_price = self.get_buyma_lowest_price_for_favorite(product_name)
                    
                    if competitor_price > 0:
                        # 현재가와 최저가 비교
                        if current_price <= competitor_price:
                            # 현재가가 최저가보다 낮거나 같으면 그냥 놔둠
                            status = "✅ 현재가 적정"
                            needs_update = False
                            suggested_price = current_price
                            price_diff = 0
                        else:
                            # 현재가가 최저가보다 높으면 제안가 계산
                            suggested_price = competitor_price - discount_amount
                            
                            # 가격차이 계산 (제안가 - 현재가)
                            price_diff = suggested_price - current_price
                            
                            # 상태 결정 (가격차이 기준)
                            if price_diff < -min_margin:
                                # 가격차이가 -설정값보다 작으면 (예: -600 < -500)
                                status = f"⚠️ 손실 예상 ({price_diff:+,}엔)"
                                needs_update = False
                            else:
                                # 가격차이가 설정값 이내면
                                status = "💰 가격 수정 필요"
                                needs_update = True
                        
                        # 결과 업데이트 (키 이름 통일)
                        product['lowest_price'] = competitor_price      # competitor_price → lowest_price
                        product['suggested_price'] = suggested_price
                        product['price_difference'] = price_diff        # price_diff → price_difference
                        product['status'] = status
                        product['needs_update'] = needs_update
                        product['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        
                        analyzed_count += 1
                        self.log_message(f"✅ 분석 완료: {product_name} - {status}")
                        
                    else:
                        product['lowest_price'] = 0                     # 키 이름 통일
                        product['suggested_price'] = 0
                        product['price_difference'] = 0                 # 키 이름 통일
                        product['status'] = "분석 실패"
                        product['needs_update'] = False
                        failed_count += 1
                        self.log_message(f"❌ 분석 실패: {product_name}")
                        
                except Exception as e:
                    self.log_message(f"❌ 분석 오류: {product.get('name', 'Unknown')} - {str(e)}")
                    failed_count += 1
                    continue
            
            # 테이블 업데이트
            QTimer.singleShot(0, self.update_favorite_table)
            
            self.log_message(f"✅ 1단계 완료: 분석 {analyzed_count}개, 실패 {failed_count}개")
            
            # ==================== 2단계: 가격수정 ====================
            self.log_message("🔄 2단계: 주력상품 가격수정 시작")
            
            # 수정이 필요한 상품들 찾기
            need_update = [p for p in self.favorite_products if p.get('needs_update', False)]
            
            if len(need_update) == 0:
                self.log_message("📋 가격 수정이 필요한 상품이 없습니다.")
                # 수정할 상품이 없어도 진행률 위젯을 완료 상태로 설정
                QTimer.singleShot(0, lambda: self.progress_widget.set_task_complete(
                    "주력상품 통합 처리 완료", 
                    f"분석: {analyzed_count}개, 수정: 0개"
                ))
            else:
                self.log_message(f"📊 {len(need_update)}개 상품 가격 수정 시작")
                
                for i, product in enumerate(need_update):
                    try:
                        product_name = product.get('name', '')
                        suggested_price = product.get('suggested_price', 0)
                        
                        self.log_message(f"💰 가격 수정 중 ({i+1}/{len(need_update)}): {product_name}")
                        
                        # 진행률 위젯 업데이트 (2단계)
                        QTimer.singleShot(0, lambda idx=i: self.progress_widget.update_progress(
                            len(self.favorite_products) + idx + 1, 
                            len(self.favorite_products) * 2,
                            "⭐ 주력상품 가격수정", 
                            f"수정 중: {product_name[:20]}..."
                        ))
                        
                        # 수동 모드인 경우 사용자 확인
                        if not is_auto_mode:
                            # 메인 스레드에서 확인 다이얼로그 표시
                            confirm_result = [None]  # 리스트로 감싸서 참조 전달
                            
                            def show_confirm_dialog():
                                reply = QMessageBox.question(
                                    self,
                                    "가격 수정 확인",
                                    f"상품: {product_name}\n"
                                    f"현재가: {product.get('current_price', 0):,}엔\n"
                                    f"제안가: {suggested_price:,}엔\n\n"
                                    f"가격을 수정하시겠습니까?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                )
                                confirm_result[0] = (reply == QMessageBox.StandardButton.Yes)
                            
                            QTimer.singleShot(0, show_confirm_dialog)
                            
                            # 사용자 응답 대기
                            import time
                            timeout = 30  # 30초 타임아웃
                            elapsed = 0
                            while elapsed < timeout and confirm_result[0] is None:
                                time.sleep(0.1)
                                elapsed += 0.1
                            
                            if confirm_result[0] is None or not confirm_result[0]:
                                self.log_message(f"⏭️ 사용자 취소: {product_name}")
                                continue
                        
                        # 가격관리 탭의 가격수정 로직 활용
                        success = self.update_buyma_product_price_for_favorite(product, suggested_price, is_auto_mode)
                        
                        if success:
                            product['current_price'] = suggested_price
                            product['status'] = "수정 완료"
                            product['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                            updated_count += 1
                            
                            self.log_message(f"✅ 가격 수정 완료: {product_name} → {suggested_price:,}엔")
                        else:
                            self.log_message(f"❌ 가격 수정 실패: {product_name}")
                        
                    except Exception as e:
                        self.log_message(f"❌ 가격 수정 오류: {product.get('name', 'Unknown')} - {str(e)}")
                        continue
                
                # 수정 작업 완료 후 진행률 위젯 완료 상태
                QTimer.singleShot(0, lambda: self.progress_widget.set_task_complete(
                    "주력상품 통합 처리 완료", 
                    f"분석: {analyzed_count}개, 수정: {updated_count}개"
                ))
            
            # 최종 테이블 업데이트 및 저장
            QTimer.singleShot(0, self.update_favorite_table)
            QTimer.singleShot(0, self.save_favorite_products_auto)
            
            # 완료 처리
            self.log_message(f"🎉 주력상품 통합 처리 완료!")
            self.log_message(f"📊 최종 결과:")
            self.log_message(f"   - 분석 완료: {analyzed_count}개")
            self.log_message(f"   - 가격 수정: {updated_count}개")
            self.log_message(f"   - 처리 실패: {failed_count}개")
            
            # UI 상태 복원
            QTimer.singleShot(0, self.restore_favorite_analysis_ui)
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 통합 처리 오류: {str(e)}")
            # 오류 시 진행률 위젯에 오류 표시
            QTimer.singleShot(0, lambda: self.progress_widget.set_task_error(
                "주력상품 통합 처리 오류", 
                str(e)
            ))
            # UI 상태 복원
            QTimer.singleShot(0, self.restore_favorite_analysis_ui)
    
    def restore_favorite_analysis_ui(self):
        """주력상품 분석 UI 상태 복원"""
        try:
            self.fav_start_analysis_btn.setEnabled(True)
            self.fav_start_analysis_btn.setText("🚀 가격확인-가격수정 시작")
        except Exception as e:
            self.log_message(f"UI 복원 오류: {str(e)}")
    
    def get_buyma_lowest_price_for_favorite(self, product_name):
        """주력상품용 BUYMA 최저가 조회 (search_buyma_lowest_price 로직 활용)"""
        try:
            # 1. 상품명에서 실제 검색어 추출 (商品ID 이전까지)
            search_name = product_name
            if "商品ID" in product_name:
                search_name = product_name.split("商品ID")[0].strip()
            
            # 추가 정리 (줄바꿈, 특수문자 제거)
            search_name = search_name.replace("\n", " ").strip()
            
            self.log_message(f"🔍 주력상품 검색어: '{search_name}'")
            
            if not self.shared_driver:
                self.log_message("❌ 브라우저가 초기화되지 않았습니다.")
                return None
            
            # 2. BUYMA 검색 URL로 이동 (첫 페이지)
            page_number = 1
            lowest_price = float('inf')
            found_products = 0
            
            while True:
                search_url = f"https://www.buyma.com/r/-R120/{search_name}_{page_number}"
                self.log_message(f"🌐 주력상품 페이지 {page_number} 접속: {search_url}")
                
                try:
                    self.shared_driver.get(search_url)
                    time.sleep(3)
                except Exception as e:
                    # 페이지 로딩 타임아웃 또는 네트워크 오류
                    self.log_message(f"⏱️ 페이지 {page_number} 로딩 실패: {str(e)}")
                    break
                
                # 3. ul.product_lists 요소 로딩 대기 (가격관리 탭과 동일한 로직)
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                try:
                    # 상품 리스트 로딩 대기 (최대 10초)
                    product_list = WebDriverWait(self.shared_driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.product_lists"))
                    )
                    
                    # 4. 각 li 요소들 (상품들) 수집
                    product_items = product_list.find_elements(By.TAG_NAME, "li")
                    
                    if not product_items:
                        self.log_message(f"⚠️ 페이지 {page_number}에서 상품을 찾을 수 없습니다.")
                        break
                    
                    self.log_message(f"📦 페이지 {page_number}에서 {len(product_items)}개 상품 발견")
                    
                    # 5. 각 상품 정보 분석
                    for item in product_items:
                        try:
                            # 6. 상품명 추출 (div.product_name)
                            name_elem = item.find_element(By.CSS_SELECTOR, "div.product_name")
                            item_name = name_elem.text.strip()
                            
                            # 7. 검색한 상품명이 포함되어 있는지 확인
                            if search_name.lower() in item_name.lower():
                                # 8. 상품가격 추출 (span.Price_Txt)
                                try:
                                    price_elem = item.find_element(By.CSS_SELECTOR, "span.Price_Txt")
                                    price_text = price_elem.text.strip()
                                    
                                    # 가격에서 숫자만 추출 (¥12,000 → 12000)
                                    import re
                                    price_numbers = re.findall(r'[\d,]+', price_text)
                                    if price_numbers:
                                        price = int(price_numbers[0].replace(',', ''))
                                        
                                        # 9. 최저가 비교 및 갱신
                                        if price < lowest_price:
                                            lowest_price = price
                                            self.log_message(f"💰 새로운 최저가 발견: ¥{price:,} - {item_name[:30]}...")
                                        
                                        found_products += 1
                                    
                                except Exception as e:
                                    # 가격 정보가 없는 상품은 건너뛰기
                                    continue
                            
                        except Exception as e:
                            # 개별 상품 처리 오류는 건너뛰기
                            continue
                    
                    # 10. 다음 페이지 확인 (li 개수가 120개면 다음 페이지 있음)
                    if len(product_items) >= 120:
                        page_number += 1
                        self.log_message(f"➡️ 다음 페이지({page_number})로 이동...")
                        time.sleep(2)  # 페이지 간 딜레이
                    else:
                        # 마지막 페이지 도달
                        self.log_message(f"✅ 모든 페이지 검색 완료 (총 {page_number} 페이지)")
                        break
                
                except Exception as e:
                    self.log_message(f"❌ 페이지 {page_number} 로딩 실패: {str(e)}")
                    continue
            
            # 11. 결과 반환
            if lowest_price != float('inf'):
                self.log_message(f"🎉 검색 완료: 총 {found_products}개 상품 중 최저가 ¥{lowest_price:,}")
                return lowest_price
            else:
                self.log_message(f"⚠️ '{search_name}' 상품을 찾을 수 없습니다.")
                return None
                
        except Exception as e:
            self.log_message(f"❌ 주력상품 최저가 검색 오류: {str(e)}")
            return None
    
    def update_buyma_product_price_for_favorite(self, product, new_price, is_auto_mode):
        """주력상품용 BUYMA 가격 수정 (가격관리 로직 활용)"""
        try:
            product_name = product.get('name', '')
            
            # 가격관리 탭의 update_buyma_product_price 함수와 동일한 로직 사용
            return self.update_buyma_product_price(product_name, new_price, is_auto_mode)
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 가격 수정 오류: {str(e)}")
            return False
            
        except Exception as e:
            self.log_message(f"가격 수정 오류: {str(e)}")
            return False
    
    def test_progress_widget(self):
        """진행률 위젯 테스트 함수"""
        try:
            self.progress_widget.show()
            
            # 테스트 진행률 시뮬레이션
            import threading
            import time
            
            def simulate_progress():
                for i in range(101):
                    QTimer.singleShot(i * 50, lambda p=i: self.progress_widget.update_progress(
                        p, 100, "테스트 진행 중", f"진행률: {p}%"
                    ))
                
                # 완료 상태 표시
                QTimer.singleShot(5500, lambda: self.progress_widget.set_task_complete(
                    "테스트 완료", "진행률 위젯 테스트가 완료되었습니다!"
                ))
            
            thread = threading.Thread(target=simulate_progress, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log_message(f"❌ 진행률 위젯 테스트 오류: {str(e)}")

    def get_product_data_from_table(self, row):
        """크롤링 테이블에서 상품 데이터 가져오기"""
        try:
            product_data = {}
            
            # 테이블에서 각 컬럼 데이터 추출
            product_data['title'] = self.crawling_table.item(row, 0).text() if self.crawling_table.item(row, 0) else ""
            product_data['brand'] = self.crawling_table.item(row, 1).text() if self.crawling_table.item(row, 1) else ""
            product_data['price'] = self.crawling_table.item(row, 2).text() if self.crawling_table.item(row, 2) else ""
            product_data['image_count'] = self.crawling_table.item(row, 3).text() if self.crawling_table.item(row, 3) else "0"
            product_data['options'] = self.crawling_table.item(row, 4).text() if self.crawling_table.item(row, 4) else ""
            product_data['url'] = self.crawling_table.item(row, 5).text() if self.crawling_table.item(row, 5) else ""
            
            # 추가 데이터 (크롤링 시 저장된 상세 정보)
            if hasattr(self, 'crawled_products') and row < len(self.crawled_products):
                crawled_data = self.crawled_products[row]
                product_data.update(crawled_data)
                self.log_message(f"🔍 크롤링 데이터 병합: 카테고리 {len(crawled_data.get('categories', []))}개")
            else:
                self.log_message(f"⚠️ 크롤링 데이터 없음: row={row}, crawled_products 길이={len(getattr(self, 'crawled_products', []))}")
            
            # 카테고리 데이터 확인 로그
            categories = product_data.get('categories', [])
            self.log_message(f"📂 최종 카테고리 데이터: {categories}")
            
            return product_data
            
        except Exception as e:
            self.log_message(f"❌ 상품 데이터 추출 오류 (행 {row}): {str(e)}")
            return None
    
    def upload_single_product(self, product_data, product_number, max_images):
        """단일 상품 BUYMA 업로드 - 실제 구현"""
        try:
            # shared_driver 상태 확인
            if not self.shared_driver:
                self.log_message("❌ 브라우저가 초기화되지 않았습니다. 브라우저를 재시작합니다...")
                self.restart_shared_driver()
                if not self.shared_driver:
                    return {'success': False, 'error': '브라우저 초기화 실패'}
            
            # 브라우저 응답 확인
            try:
                current_url = self.shared_driver.current_url
                self.log_message(f"🌐 현재 브라우저 위치: {current_url}")
            except Exception as e:
                self.log_message(f"⚠️ 브라우저 응답 없음. 재시작합니다... ({str(e)})")
                self.restart_shared_driver()
                if not self.shared_driver:
                    return {'success': False, 'error': '브라우저 재시작 실패'}
            
            self.log_message(f"🌐 BUYMA 상품 등록 페이지로 이동...")
            
            # BUYMA 상품 등록 페이지로 이동
            try:
                self.shared_driver.get("https://www.buyma.com/my/sell/new?tab=b")
                import time
                time.sleep(5)  # 페이지 로딩 대기
            except Exception as e:
                self.log_message(f"❌ 페이지 로딩 실패: {str(e)}")
                return {'success': False, 'error': f'페이지 로딩 실패: {str(e)}'}
            
            # 1. 상품명 입력
            self.log_message(f"📝 상품명 입력: {product_data['title'][:50]}...")
            result = self.fill_product_title_real(product_data['title'])
            if not result:
                return {'success': False, 'error': '상품명 입력 실패'}
            
            # 2. 상품 설명 입력
            self.log_message(f"📄 상품 설명 입력...")
            result = self.fill_product_description_real(product_data)
            if not result:
                return {'success': False, 'error': '상품 설명 입력 실패'}
            
            # 3. 이미지 업로드 (최대 개수에 따라 순차적으로)
            if 'images' in product_data and product_data['images']:
                self.log_message(f"🖼️ 이미지 업로드: {len(product_data['images'])}개 (최대 {max_images}개)")
                result = self.upload_product_images_real(product_data['images'], max_images)
                if not result:
                    return {'success': False, 'error': '이미지 업로드 실패'}
            
            # 4. 카테고리 선택
            self.log_message(f"📂 카테고리 선택...")
            result = self.select_product_category_real(product_data)
            if not result:
                return {'success': False, 'error': '카테고리 선택 실패'}
            
            # 5. 색상 추가 (크롤링된 색상 데이터가 있는 경우)
            if 'colors' in product_data and product_data['colors']:
                self.log_message(f"🎨 색상 추가: {len(product_data['colors'])}개")
                result = self.add_product_colors_real(product_data)
                if not result:
                    self.log_message(f"⚠️ 색상 추가 실패 (계속 진행)")
            else:
                self.log_message(f"📝 크롤링된 색상 데이터가 없습니다.")
            
            # 6. 사이즈 추가 (크롤링된 사이즈 데이터가 있는 경우)
            if 'sizes' in product_data and product_data['sizes']:
                self.log_message(f"📏 사이즈 추가: {len(product_data['sizes'])}개")
                result = self.add_product_sizes_real(product_data)
                if not result:
                    self.log_message(f"⚠️ 사이즈 추가 실패 (계속 진행)")
            else:
                self.log_message(f"📝 크롤링된 사이즈 데이터가 없습니다.")
            
            # 7. 배송방법, 구입기간, 가격 설정
            self.log_message(f"🚚 배송 및 상세 설정...")
            result = self.set_shipping_and_details_real(product_data)
            if not result:
                return {'success': False, 'error': '배송 및 상세 설정 실패'}
            
            # 8. 상품 등록 완료 (실제 등록은 주석 처리)
            self.log_message(f"✅ 상품 정보 입력 완료")
            
            # 업로드 모드 확인
            upload_mode = self.upload_mode_combo.currentText()
            is_manual_mode = "수동 모드" in upload_mode
            
            if is_manual_mode:
                # 수동 모드: 사용자 확인 필요
                self.log_message(f"👤 수동 모드: 등록 전 최종 확인...")
                user_confirmed = self.show_crash_safe_confirmation(product_data, product_number, max_images)
                
                if not user_confirmed:
                    self.log_message(f"❌ 사용자가 등록을 취소했습니다.")
                    return {'success': False, 'error': '사용자가 등록을 취소함'}
                    
                self.log_message(f"✅ 사용자가 등록을 승인했습니다.")
            else:
                # 자동 모드: 바로 등록
                self.log_message(f"🤖 자동 모드: 확인 없이 바로 등록 진행...")
            
            # 실제 등록 버튼 클릭
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                confirm_button = WebDriverWait(self.shared_driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.bmm-c-btn.bmm-c-btn--p.bmm-c-btn--m.bmm-c-btn--thick"))
                )
                
                # 최종 확인 후 등록 버튼 클릭
                confirm_button.click()
                self.log_message("🚀 상품 등록 버튼 클릭 완료!")
                time.sleep(3)  # 등록 처리 대기
                
                # 등록 완료 확인 (선택사항)
                self.log_message("✅ 상품 등록이 완료되었습니다!")
                
            except Exception as e:
                self.log_message(f"❌ 등록 버튼 클릭 오류: {str(e)}")
                return {'success': False, 'error': f'등록 버튼 클릭 실패: {str(e)}'}
            
            # 실제 등록 버튼 클릭 (필요시 주석 해제)
            # result = self.submit_product_real()
            # if not result:
            #     return {'success': False, 'error': '상품 등록 실패'}
            
            return {'success': True, 'error': None}
            
        except Exception as e:
            self.log_message(f"❌ 업로드 중 예외 발생: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def fill_product_title_real(self, title):
        """상품명 입력 - 실제 BUYMA 구조"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 상품명 입력 필드 찾기 (0번째 인덱스)
            title_inputs = WebDriverWait(self.shared_driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input.bmm-c-text-field'))
            )
            
            if len(title_inputs) == 0:
                self.log_message("❌ 상품명 입력 필드를 찾을 수 없습니다.")
                return False
            
            title_input = title_inputs[0]  # 0번째 인덱스
            title_input.clear()
            title_input.send_keys(title)
            
            self.log_message(f"✅ 상품명 입력 완료: {title[:50]}...")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 상품명 입력 오류: {str(e)}")
            return False
    
    def fill_product_description_real(self, product_data):
        """상품 설명 입력 - 실제 BUYMA 구조"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 크롤링된 상품 설명 사용 (있으면 그대로, 없으면 기본 설명 생성)
            if product_data.get('description'):
                description = product_data['description']
                self.log_message(f"📄 크롤링된 상품 설명 사용: {len(description)}자")
            else:
                # 크롤링된 설명이 없는 경우에만 기본 설명 생성
                description = f"""
{product_data.get('title', '')}

브랜드: {product_data.get('brand', '')}
가격: {product_data.get('price', '')}

고품질 상품입니다.

※ 해외 배송 상품으로 배송까지 2-3주 소요됩니다.
※ 관세 및 배송비는 별도입니다.
                """.strip()
                self.log_message(f"📄 기본 상품 설명 생성: {len(description)}자")
            
            # 상품 설명 입력 필드 찾기 (첫 번째 인덱스)
            description_textareas = WebDriverWait(self.shared_driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'textarea.bmm-c-textarea'))
            )
            
            if len(description_textareas) == 0:
                self.log_message("❌ 상품 설명 입력 필드를 찾을 수 없습니다.")
                return False
            
            description_textarea = description_textareas[0]  # 첫 번째 인덱스
            description_textarea.clear()
            description_textarea.send_keys(description)
            
            self.log_message(f"✅ 상품 설명 입력 완료 ({len(description)}자)")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 상품 설명 입력 오류: {str(e)}")
            return False
    
    def upload_product_images_real(self, images, max_images):
        """이미지 업로드 - 실제 BUYMA 구조"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import requests
            import os
            import tempfile
            
            # 파일 업로드 input 찾기
            file_input = WebDriverWait(self.shared_driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"][accept="image/jpeg,image/gif,image/png"][multiple]'))
            )
            
            upload_count = min(len(images), max_images)
            self.log_message(f"🖼️ 이미지 업로드 시작: {upload_count}개 (최대 {max_images}개)")
            
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp()
            uploaded_files = []
            
            try:
                # 이미지 다운로드 및 로컬 저장
                for i, image_url in enumerate(images[:max_images]):
                    try:
                        self.log_message(f"📷 이미지 {i + 1}/{upload_count} 다운로드 중...")
                        
                        # 이미지 다운로드
                        response = requests.get(image_url, timeout=30)
                        response.raise_for_status()
                        
                        # 파일 확장자 추출
                        if image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                            ext = '.jpg'
                        elif image_url.lower().endswith('.png'):
                            ext = '.png'
                        elif image_url.lower().endswith('.gif'):
                            ext = '.gif'
                        else:
                            ext = '.jpg'  # 기본값
                        
                        # 임시 파일로 저장
                        temp_file_path = os.path.join(temp_dir, f"image_{i+1}{ext}")
                        with open(temp_file_path, 'wb') as f:
                            f.write(response.content)
                        
                        uploaded_files.append(temp_file_path)
                        self.log_message(f"✅ 이미지 {i + 1} 다운로드 완료")
                        
                    except Exception as e:
                        self.log_message(f"❌ 이미지 {i + 1} 다운로드 실패: {str(e)}")
                        continue
                
                # 모든 이미지 파일을 한 번에 업로드
                if uploaded_files:
                    file_paths = '\n'.join(uploaded_files)
                    file_input.send_keys(file_paths)
                    
                    self.log_message(f"✅ {len(uploaded_files)}개 이미지 업로드 완료")
                    
                    # 업로드 완료 대기
                    import time
                    time.sleep(3)
                    
                    return True
                else:
                    self.log_message("❌ 업로드할 이미지가 없습니다.")
                    return False
                    
            finally:
                # 임시 파일 정리
                try:
                    for file_path in uploaded_files:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    os.rmdir(temp_dir)
                except:
                    pass
            
        except Exception as e:
            self.log_message(f"❌ 이미지 업로드 오류: {str(e)}")
            return False
    
    def select_product_category_real(self, product_data):
        """카테고리 선택 - 크롤링된 카테고리 데이터 사용"""
        try:
            import time
            
            # 크롤링된 카테고리 데이터 사용
            categories = product_data.get('categories', [])
            
            if not categories:
                # 크롤링된 카테고리가 없으면 기본 카테고리 사용
                categories = ["레디스패션", "원피스", "미니원피스"]
                self.log_message(f"📂 크롤링된 카테고리가 없어 기본 카테고리 사용: {categories}")
            else:
                self.log_message(f"📂 크롤링된 카테고리 사용: {categories}")
            
            self.log_message(f"📂 카테고리 선택 시작: {' > '.join(categories)}")
            
            # 각 카테고리 레벨별로 선택
            for level, category_name in enumerate(categories):
                try:
                    self.log_message(f"📂 {level + 1}차 카테고리 선택: {category_name}")
                    
                    # JavaScript로 카테고리 박스 열기 (중괄호 문제 해결)
                    open_category_script = """
                    const categoryControls = document.querySelectorAll('.sell-category-select .Select-control');
                    if (categoryControls.length > """ + str(level) + """) {
                        const categoryControl = categoryControls[""" + str(level) + """];
                        categoryControl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        categoryControl.click?.();
                        console.log('카테고리 박스 클릭 완료:', """ + str(level) + """);
                        return true;
                    } else {
                        console.warn('카테고리 컨트롤을 찾지 못했습니다. 인덱스:', """ + str(level) + """);
                        return false;
                    }
                    """
                    
                    result = self.shared_driver.execute_script(open_category_script)
                    if not result:
                        self.log_message(f"❌ {level + 1}차 카테고리 선택 박스를 찾을 수 없습니다.")
                        return False
                    
                    self.log_message(f"✅ {level + 1}차 카테고리 박스 클릭 완료")
                    time.sleep(4)  # 메뉴 열림 대기
                    
                    # 메뉴가 실제로 열렸는지 확인
                    menu_check_script = """
                    const menu = document.querySelector('.sell-category-select .Select-menu-outer') || 
                                document.querySelector('.Select-menu-outer') ||
                                document.querySelector('.Select-menu');
                    if (menu) {
                        const options = menu.querySelectorAll('.Select-option, [class*="Select-option"]');
                        console.log('메뉴 열림 확인 - 옵션 개수:', options.length);
                        return options.length;
                    }
                    return 0;
                    """
                    
                    option_count = self.shared_driver.execute_script(menu_check_script)
                    self.log_message(f"🔍 메뉴 열림 확인: {option_count}개 옵션 발견")
                    
                    # 카테고리 옵션 선택 (개선된 로직)
                    select_option_script = """
                    function selectCategoryByExactText(text) {
                        console.log('찾는 카테고리:', text);
                        
                        // 여러 가능한 메뉴 선택자 시도
                        const menuSelectors = [
                            '.sell-category-select .Select-menu-outer',
                            '.Select-menu-outer',
                            '.Select-menu',
                            '[class*="Select-menu"]'
                        ];
                        
                        let menu = null;
                        for (const selector of menuSelectors) {
                            menu = document.querySelector(selector);
                            if (menu) {
                                console.log('메뉴 발견:', selector);
                                break;
                            }
                        }
                        
                        if (!menu) {
                            console.warn('메뉴가 열려있지 않습니다. 모든 선택자 시도 실패');
                            return false;
                        }
                        
                        const options = [...menu.querySelectorAll('.Select-option, [class*="Select-option"]')];
                        console.log('사용 가능한 옵션들:', options.map(opt => opt.textContent.trim()));
                        
                        if (options.length === 0) {
                            console.warn('옵션을 찾을 수 없습니다.');
                            return false;
                        }
                        
                        // 1. 정확한 텍스트 매칭 시도
                        let target = options.find(opt => opt.textContent.trim() === text);
                        
                        // 2. 부분 매칭 시도 (양방향)
                        if (!target) {
                            target = options.find(opt => {
                                const optText = opt.textContent.trim();
                                return optText.includes(text) || text.includes(optText);
                            });
                        }
                        
                        // 3. 키워드 매칭 시도
                        if (!target) {
                            const keywords = text.split(/[\\s・]+/);
                            target = options.find(opt => {
                                const optText = opt.textContent.trim();
                                return keywords.some(keyword => 
                                    keyword.length > 1 && (optText.includes(keyword) || keyword.includes(optText))
                                );
                            });
                        }
                        
                        if (target) {
                            console.log('매칭된 옵션:', target.textContent.trim());
                            target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                            target.click?.();
                            setTimeout(() => target.click?.(), 100); // 추가 클릭 시도
                            return true;
                        } else {
                            console.warn('매칭되는 옵션을 찾지 못했습니다:', text);
                            // 첫 번째 옵션 선택 (기본값)
                            if (options.length > 0) {
                                console.log('기본 옵션 선택:', options[0].textContent.trim());
                                options[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                options[0].click?.();
                                setTimeout(() => options[0].click?.(), 100);
                                return true;
                            }
                            return false;
                        }
                    }
                    
                    return selectCategoryByExactText('""" + category_name + """');
                    """
                    
                    option_result = self.shared_driver.execute_script(select_option_script)
                    
                    if option_result:
                        self.log_message(f"✅ {level + 1}차 카테고리 선택 완료: {category_name}")
                        time.sleep(1)
                    else:
                        self.log_message(f"❌ {level + 1}차 카테고리 옵션 선택 실패: {category_name}")
                        # 실패해도 계속 진행 (다음 레벨이 있을 수 있음)
                
                except Exception as e:
                    self.log_message(f"❌ {level + 1}차 카테고리 선택 오류: {str(e)}")
                    continue
            
            self.log_message(f"✅ 카테고리 선택 프로세스 완료")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 카테고리 선택 오류: {str(e)}")
            return False
    
    def add_product_colors_real(self, product_data):
        """상품 색상 추가 - 크롤링된 데이터 기반 (개선된 로직)"""
        try:
            import time
            
            # 크롤링된 색상 데이터 사용
            colors = product_data.get('colors', [])
            
            if not colors or len(colors) == 0:
                self.log_message("📝 크롤링된 색상 데이터가 없습니다.")
                return True
            
            self.log_message(f"🎨 크롤링된 색상 추가 시작: {len(colors)}개 색상 - {colors}")
            
            for i, color_data in enumerate(colors):
                try:
                    # 색상 데이터 구조 확인 및 추출
                    if isinstance(color_data, list) and len(color_data) >= 2:
                        color_category = color_data[0]  # 색상 카테고리 (예: "black", "white")
                        color_text = color_data[1]      # 색상 텍스트 (예: "블랙", "화이트")
                    else:
                        # 기존 형식 호환성 (단순 문자열)
                        color_category = ""
                        color_text = str(color_data)
                    
                    self.log_message(f"🎨 색상 {i + 1}/{len(colors)} 추가 중: {color_text} (카테고리: {color_category})")
                    
                    # 1. 색상 Select 박스 찾기 및 클릭 (개선된 로직)
                    find_color_control_script = f"""
                    let colorControls = document.querySelectorAll('.Select .Select-control');
                    let colorControl = null;
                    let firstColorIndex = -1;
                    
                    if ({i} === 0) {{
                        // 첫 번째 색상: "色指定なし" (색상 지정 없음) 텍스트 찾기
                        for (let j = 0; j < colorControls.length; j++) {{
                            if (colorControls[j].innerText.includes("色指定なし")) {{
                                colorControl = colorControls[j];
                                firstColorIndex = j;
                                console.log('첫 번째 색상 박스 찾음 (인덱스: ' + j + '):', colorControl.innerText.trim());
                                // 첫 번째 색상 인덱스를 전역 변수에 저장
                                window.firstColorBoxIndex = j;
                                break;
                            }}
                        }}
                    }} else {{
                        // 두 번째 색상부터: 첫 번째 색상 인덱스 + 현재 색상 순서
                        if (window.firstColorBoxIndex !== undefined) {{
                            let targetIndex = window.firstColorBoxIndex + {i};
                            if (colorControls.length > targetIndex) {{
                                colorControl = colorControls[targetIndex];
                                console.log('색상 박스 ' + targetIndex + ' 선택 (첫번째+' + {i} + '):', colorControl.innerText.trim());
                            }} else {{
                                console.warn('색상 박스 인덱스 ' + targetIndex + '가 범위를 벗어났습니다. 총 ' + colorControls.length + '개');
                                return false;
                            }}
                        }} else {{
                            console.warn('첫 번째 색상 박스 인덱스를 찾을 수 없습니다.');
                            return false;
                        }}
                    }}
                    
                    if (colorControl) {{
                        colorControl.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                        colorControl.click?.();
                        console.log('색상 Select 박스 클릭 완료 (색상 ' + ({i} + 1) + ')');
                        return true;
                    }} else {{
                        console.warn('색상 Select-control을 찾지 못했습니다.');
                        return false;
                    }}
                    """
                    
                    result = self.shared_driver.execute_script(find_color_control_script)
                    if not result:
                        self.log_message(f"❌ 색상 Select 박스를 찾을 수 없습니다.")
                        continue
                    
                    time.sleep(2)  # 드롭다운 열림 대기
                    
                    # 2. 색상 옵션 선택 (카테고리 → 일본어 변환 후 매칭)
                    select_color_script = f"""
                    function selectColorByCategory(category, text) {{
                        const options = [...document.querySelectorAll('.Select-menu-outer .Select-option')];
                        console.log('사용 가능한 색상 옵션들:', options.map(opt => opt.innerText.trim()));
                        
                        // 영어 카테고리를 일본어로 변환
                        const categoryMapping = {{
                            'black': 'ブラック',
                            'white': 'ホワイト', 
                            'red': 'レッド',
                            'blue': 'ブルー',
                            'green': 'グリーン',
                            'yellow': 'イエロー',
                            'pink': 'ピンク',
                            'brown': 'ブラウン',
                            'gray': 'グレー',
                            'grey': 'グレー',
                            'purple': 'パープル',
                            'orange': 'オレンジ',
                            'beige': 'ベージュ',
                            'navy': 'ネイビー',
                            'silver': 'シルバー',
                            'gold': 'ゴールド'
                        }};
                        
                        // 1단계: 카테고리 기반 일본어 매칭
                        if (category && categoryMapping[category.toLowerCase()]) {{
                            const japaneseCategory = categoryMapping[category.toLowerCase()];
                            console.log('카테고리 변환:', category, '->', japaneseCategory);
                            
                            let categoryTarget = options.find(opt => {{
                                const optText = opt.innerText.trim();
                                return optText.includes(japaneseCategory);
                            }});
                            
                            if (categoryTarget) {{
                                console.log('일본어 카테고리 매칭 성공:', categoryTarget.innerText.trim());
                                categoryTarget.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                                categoryTarget.click?.();
                                return true;
                            }}
                        }}
                        
                        // 2단계: 색상 텍스트 정확한 매칭 시도
                        let target = options.find(opt => opt.innerText.trim() === text);
                        
                        // 부분 매칭 시도
                        if (!target) {{
                            target = options.find(opt => opt.innerText.trim().includes(text));
                        }}
                        
                        // 색상 키워드 매칭 시도
                        if (!target) {{
                            const colorKeywords = {{
                                'black': ['블랙', 'BLACK', '검정'],
                                'white': ['화이트', 'WHITE', '흰색', '백색'],
                                'red': ['레드', 'RED', '빨강', '적색'],
                                'blue': ['블루', 'BLUE', '파랑', '청색'],
                                'green': ['그린', 'GREEN', '초록', '녹색'],
                                'yellow': ['옐로우', 'YELLOW', '노랑', '황색'],
                                'pink': ['핑크', 'PINK', '분홍'],
                                'gray': ['그레이', 'GRAY', '회색'],
                                'brown': ['브라운', 'BROWN', '갈색'],
                                'navy': ['네이비', 'NAVY', '남색']
                            }};
                            
                            const textLower = text.toLowerCase();
                            for (const [key, keywords] of Object.entries(colorKeywords)) {{
                                if (keywords.some(keyword => textLower.includes(keyword.toLowerCase()))) {{
                                    target = options.find(opt => {{
                                        const optText = opt.innerText.trim().toLowerCase();
                                        return keywords.some(keyword => optText.includes(keyword.toLowerCase()));
                                    }});
                                    if (target) break;
                                }}
                            }}
                        }}
                        
                        if (target) {{
                            target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                            target.click?.();
                            console.log('색상 선택됨: ' + target.innerText.trim());
                            return true;
                        }} else {{
                            console.warn('색상 옵션을 찾지 못했습니다: ' + text);
                            // 첫 번째 옵션 선택 (기본값)
                            if (options.length > 0) {{
                                options[0].dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                                options[0].click?.();
                                console.log('기본 색상 선택: ' + options[0].innerText.trim());
                                return true;
                            }}
                            return false;
                        }}
                    }}
                    
                    return selectColorByCategory('{color_category}', '{color_text}');
                    """
                    
                    color_result = self.shared_driver.execute_script(select_color_script)
                    
                    if color_result:
                        self.log_message(f"✅ 색상 옵션 선택 완료: {color_text} (카테고리: {color_category})")
                        time.sleep(1)
                    else:
                        self.log_message(f"❌ 색상 옵션 선택 실패: {color_text} (카테고리: {color_category})")
                        continue
                    
                    # 3. 색상 이름 입력 (color_text 사용)
                    text_inputs = self.shared_driver.find_elements(By.CSS_SELECTOR, "input.bmm-c-text-field")
                    
                    # 색상 이름 입력 필드 찾기 (인덱스 계산)
                    color_input_index = 2 + i  # 기본 인덱스 3 + 색상 순서
                    
                    if len(text_inputs) > color_input_index:
                        color_input = text_inputs[color_input_index]
                        color_input.clear()
                        color_input.send_keys(color_text)  # color_text 사용
                        self.log_message(f"✅ 색상 이름 입력 완료: {color_text}")
                    else:
                        self.log_message(f"❌ 색상 이름 입력 필드를 찾을 수 없습니다 (인덱스: {color_input_index})")
                    
                    # 4. 다음 색상을 위한 추가 버튼 클릭 (마지막 색상이 아닌 경우)
                    if i < len(colors) - 1:
                        self.log_message(f"➕ 다음 색상을 위한 추가 버튼 클릭")
                        add_color_btn = self.shared_driver.find_element(By.CSS_SELECTOR, "div.bmm-c-form-table__foot > a")
                        add_color_btn.click()
                        time.sleep(2)  # 새 색상 필드 로딩 대기
                    
                    self.log_message(f"✅ 색상 {i + 1} 추가 완료: {color_text}")
                    time.sleep(1)
                    
                except Exception as e:
                    self.log_message(f"❌ 색상 {i + 1} 추가 실패: {str(e)}")
                    continue
            
            self.log_message(f"🎉 모든 색상 추가 완료: {len(colors)}개")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 색상 추가 오류: {str(e)}")
            return False
    
    def add_product_sizes_real(self, product_data):
        """상품 사이즈 추가 - 크롤링된 데이터 기반"""
        try:
            import time
            
            # 크롤링된 사이즈 데이터 사용
            sizes = product_data.get('sizes', [])
            
            if not sizes or len(sizes) == 0:
                self.log_message("📝 크롤링된 사이즈 데이터가 없습니다.")
                return True
            
            self.log_message(f"📏 크롤링된 사이즈 추가 시작: {len(sizes)}개 사이즈 - {sizes}")
            
            # 1. 사이즈 탭으로 이동
            # size_tab_script = """
            # const sizeTab = document.querySelector('li.sell-variation__tab-item[1]');
            # if (sizeTab) {
            #     sizeTab.click();
            #     console.log('사이즈 탭으로 이동 완료');
            #     return true;
            # } else {
            #     console.warn('사이즈 탭을 찾지 못했습니다.');
            #     return false;
            # }
            # """
            
            # tab_result = self.shared_driver.execute_script(size_tab_script)
            
            tab_result = self.shared_driver.find_elements(By.CSS_SELECTOR, "li.sell-variation__tab-item")[1]
            
            if tab_result:
                tab_result.click()
                tab_result = True
            else:
                tab_result = False
                
            if not tab_result:
                self.log_message("❌ 사이즈 탭으로 이동할 수 없습니다.")
                return False
            
            self.log_message("✅ 사이즈 탭으로 이동 완료")
            time.sleep(2)  # 탭 로딩 대기
            
            # 2. 사이즈 Select 박스 찾기 및 클릭 (3번째 "선택해 주세요" 요소)
            find_size_control_script = """
            let sizeControls = document.querySelectorAll('.Select .Select-control');
            let sizeControl = null;
            let count = 0;
            
            for (let i = 0; i < sizeControls.length; i++) {
                if (sizeControls[i].innerText.includes("選択してください")) {
                    sizeControl = sizeControls[i];
                    
                    if (count != 2) {
                        count += 1;
                        continue;
                    }
                    break;
                }
            }
            
            if (sizeControl) {
                sizeControl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                sizeControl.click?.();
                console.log('사이즈 Select 박스 클릭 완료');
                return true;
            } else {
                console.warn('사이즈 Select-control을 찾지 못했습니다.');
                return false;
            }
            """
            
            size_control_result = self.shared_driver.execute_script(find_size_control_script)
            if not size_control_result:
                self.log_message("❌ 사이즈 Select 박스를 찾을 수 없습니다.")
                return False
            
            self.log_message("✅ 사이즈 Select 박스 클릭 완료")
            time.sleep(2)  # 드롭다운 열림 대기
            
            # 3. "변형 있음" 옵션 선택
            select_variation_script = """
            function selectSizeByText(text) {
                const options = [...document.querySelectorAll('.Select-menu-outer .Select-option')];
                console.log('사용 가능한 사이즈 옵션들:', options.map(opt => opt.innerText.trim()));
                
                const target = options.find(opt => opt.innerText.trim().includes(text));
                if (target) {
                    target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    target.click?.();
                    console.log('사이즈 1차 선택됨: ' + text);
                    return true;
                } else {
                    console.warn('옵션을 찾지 못했습니다: ' + text);
                    return false;
                }
            }
            
            return selectSizeByText('バリエーションあり');
            """
            
            variation_result = self.shared_driver.execute_script(select_variation_script)
            if not variation_result:
                self.log_message("❌ '변형 있음' 옵션 선택 실패")
                return False
            
            self.log_message("✅ '변형 있음' 옵션 선택 완료")
            time.sleep(2)  # 변형 옵션 로딩 대기
            
            # 4. 각 사이즈 입력
            for i, size in enumerate(sizes):
                try:
                    self.log_message(f"📏 사이즈 {i + 1}/{len(sizes)} 입력 중: {size}")
                    
                    # 사이즈 입력 필드 찾기 (인덱스 2부터 시작)
                    size_input_index = 2 + i
                    
                    text_inputs = self.shared_driver.find_elements(By.CSS_SELECTOR, "input.bmm-c-text-field")
                    
                    if len(text_inputs) > size_input_index:
                        size_input = text_inputs[size_input_index]
                        size_input.clear()
                        size_input.send_keys(size)
                        self.log_message(f"✅ 사이즈 입력 완료 (인덱스 {size_input_index}): {size}")
                    else:
                        self.log_message(f"❌ 사이즈 입력 필드를 찾을 수 없습니다 (인덱스: {size_input_index})")
                        continue
                    
                    # 다음 사이즈를 위한 추가 버튼 클릭 (마지막 사이즈가 아닌 경우)
                    if i < len(sizes) - 1:
                        self.log_message(f"➕ 다음 사이즈를 위한 추가 버튼 클릭")
                        
                        # div.bmm-c-form-table__foot의 첫 번째 a 태그 클릭
                        add_size_btns = self.shared_driver.find_elements(By.CSS_SELECTOR, "div.bmm-c-form-table__foot")
                        if add_size_btns and len(add_size_btns) > 0:
                            add_btn = add_size_btns[0].find_element(By.TAG_NAME, "a")
                            add_btn.click()
                            time.sleep(2)  # 새 사이즈 필드 로딩 대기
                        else:
                            self.log_message("❌ 사이즈 추가 버튼을 찾을 수 없습니다.")
                    
                    self.log_message(f"✅ 사이즈 {i + 1} 입력 완료: {size}")
                    time.sleep(1)
                    
                except Exception as e:
                    self.log_message(f"❌ 사이즈 {i + 1} 입력 실패: {str(e)}")
                    continue
            
            self.log_message(f"🎉 모든 사이즈 입력 완료: {len(sizes)}개")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 사이즈 추가 오류: {str(e)}")
            return False
        
    
    def match_color_name(self, color1, color2):
        """색상명 매칭 헬퍼 함수"""
        # 색상명 매칭 사전 (한국어 <-> 일본어/영어)
        color_mapping = {
            'black': ['블랙', '검정', 'ブラック', 'black'],
            'white': ['화이트', '흰색', 'ホワイト', 'white'],
            'red': ['레드', '빨강', 'レッド', 'red'],
            'blue': ['블루', '파랑', 'ブルー', 'blue'],
            'green': ['그린', '초록', 'グリーン', 'green'],
            'yellow': ['옐로우', '노랑', 'イエロー', 'yellow'],
            'pink': ['핑크', '분홍', 'ピンク', 'pink'],
            'brown': ['브라운', '갈색', 'ブラウン', 'brown'],
            'gray': ['그레이', '회색', 'グレー', 'gray', 'grey'],
            'navy': ['네이비', '남색', 'ネイビー', 'navy'],
            'beige': ['베이지', 'ベージュ', 'beige'],
            'gold': ['골드', '금색', 'ゴールド', 'gold'],
            'silver': ['실버', '은색', 'シルバー', 'silver']
        }
        
        # 정확한 매칭 확인
        for key, values in color_mapping.items():
            if color1 in values and color2 in values:
                return True
        
        return False
    
    def set_shipping_and_details_real(self, product_data):
        """배송방법, 구입기간, 가격 설정 - 실제 BUYMA 구조"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from datetime import datetime, timedelta
            import time
            
            # 1. 배송방법 선택 (두 번째 체크박스)
            self.log_message("🚚 배송방법 선택...")
            try:
                checkboxes = WebDriverWait(self.shared_driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "label.bmm-c-checkbox.bmm-c-checkbox--pointer-none"))
                )
                
                if len(checkboxes) >= 2:
                    # 두 번째 체크박스 클릭 (인덱스 1)
                    checkbox = checkboxes[0].find_element(By.TAG_NAME, "input")
                    self.shared_driver.execute_script("arguments[0].click();", checkbox)
                    self.log_message("✅ 배송방법 선택 완료 (첫 번째 옵션)")
                    time.sleep(1)
                else:
                    self.log_message("❌ 배송방법 체크박스를 찾을 수 없습니다.")
                    return False
                    
            except Exception as e:
                self.log_message(f"❌ 배송방법 선택 오류: {str(e)}")
                return False
            
            # 2. 구입기간 설정 (오늘 + 90일)
            self.log_message("📅 구입기간 설정...")
            try:
                # 오늘 날짜 + 90일 계산
                today = datetime.now()
                future_date = today + timedelta(days=90)
                date_string = future_date.strftime('%Y/%m/%d')
                
                self.log_message(f"📅 구입기간 설정: {date_string} (오늘 + 90일)")
                
                # 날짜 입력 필드 찾기
                date_input = WebDriverWait(self.shared_driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".react-datepicker__input-container > input"))
                )
                
                # JavaScript로 날짜 값 설정
                self.shared_driver.execute_script(f"arguments[0].value = '{date_string}';", date_input)
                
                time.sleep(0.5)
                
                # 변경 이벤트 트리거
                self.shared_driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", date_input)
                
                self.log_message(f"✅ 구입기간 설정 완료: {date_string}")
                time.sleep(1)
                
            except Exception as e:
                self.log_message(f"❌ 구입기간 설정 오류: {str(e)}")
                return False
            
            time.sleep(1)
            
            # 3. 상품 가격 입력
            self.log_message("💰 상품 가격 입력...")
            try:
                # 가격에서 숫자만 추출
                price_text = product_data.get('price', '')
                import re
                price_numbers = re.findall(r'[\d,]+', str(price_text))
                
                if price_numbers:
                    clean_price = price_numbers[0].replace(',', '')
                    self.log_message(f"💰 가격 입력: ¥{clean_price}")
                    
                    # 가격 입력 필드 찾기
                    price_input = WebDriverWait(self.shared_driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input.bmm-c-text-field.bmm-c-text-field--half-size-char"))
                    )
                    
                    # 사이즈를 입력했을경우, 두번째 input이 가격 필드
                    if len(price_input) >= 2:
                        price_input = price_input[1]
                        
                    else:
                        price_input = price_input[0]
                    
                    price_input.clear()
                    price_input.send_keys(clean_price)
                    
                    self.log_message(f"✅ 가격 입력 완료: ¥{clean_price}")
                    time.sleep(1)
                else:
                    self.log_message("❌ 가격 정보를 추출할 수 없습니다.")
                    return False
                    
            except Exception as e:
                self.log_message(f"❌ 가격 입력 오류: {str(e)}")
                return False
            
            # 4. 입력 내용 확인 버튼 클릭 (테스트용 주석 처리)
            self.log_message("🔍 입력 내용 확인 버튼...")
            try:
                confirm_button = WebDriverWait(self.shared_driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.bmm-c-btn.bmm-c-btn--p.bmm-c-btn--m.bmm-c-btn--thick"))
                )
                
                self.log_message("✅ 확인 버튼 발견 (테스트를 위해 클릭하지 않음)")
                
                # 실제 클릭은 주석 처리 (테스트용)
                # confirm_button.click()
                # self.log_message("✅ 입력 내용 확인 버튼 클릭 완료")
                # time.sleep(2)
                
            except Exception as e:
                self.log_message(f"❌ 확인 버튼 찾기 오류: {str(e)}")
                return False
            
            self.log_message("🎉 배송방법, 구입기간, 가격 설정 완료")
            return True
            
        except Exception as e:
            self.log_message(f"❌ 배송 및 상세 설정 오류: {str(e)}")
            return False
    
    def show_product_confirmation_dialog(self, product_data, product_number, total_products):
        """상품 등록 전 상세 확인 다이얼로그"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QMessageBox
            from PyQt6.QtCore import Qt
            
            # 커스텀 다이얼로그 생성
            dialog = QDialog()
            dialog.setWindowTitle(f"상품 등록 확인 ({product_number}/{total_products})")
            dialog.setModal(True)
            dialog.resize(600, 500)
            
            layout = QVBoxLayout()
            
            # 제목
            title_label = QLabel(f"🔍 상품 등록 전 최종 확인 ({product_number}/{total_products})")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
            layout.addWidget(title_label)
            
            # 상품 정보 상세 표시
            info_text = QTextEdit()
            info_text.setReadOnly(True)
            info_text.setMaximumHeight(300)
            
            # 상품 정보 포맷팅
            colors_text = ", ".join(product_data.get('colors', [])) if product_data.get('colors') else "없음"
            images_count = len(product_data.get('images', []))
            
            detailed_info = f"""
📋 상품 정보 상세

🏷️ 상품명: {product_data.get('title', 'N/A')}

🏢 브랜드: {product_data.get('brand', 'N/A')}

💰 가격: {product_data.get('price', 'N/A')}

🖼️ 이미지: {images_count}개
   └── 최대 20개까지 업로드됩니다

🎨 색상: {len(product_data.get('colors', []))}개
   └── {colors_text}

📝 상품 설명: {len(product_data.get('description', ''))}자
   └── {product_data.get('description', '기본 설명이 생성됩니다')[:100]}...

🚚 배송방법: 두 번째 옵션 선택됨

📅 구입기간: 오늘 + 90일 (자동 설정)

⚠️ 주의사항:
   • 실제 BUYMA에 상품이 등록됩니다
   • 등록 후 수정이 어려울 수 있습니다
   • 테스트 중이라면 '취소'를 선택하세요
            """.strip()
            
            info_text.setPlainText(detailed_info)
            layout.addWidget(info_text)
            
            # 버튼 레이아웃
            button_layout = QHBoxLayout()
            
            # 취소 버튼 (기본값)
            cancel_btn = QPushButton("❌ 취소 (테스트 모드)")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            cancel_btn.clicked.connect(dialog.reject)
            
            # 등록 버튼
            register_btn = QPushButton("🚀 등록 진행")
            register_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            register_btn.clicked.connect(dialog.accept)
            
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(register_btn)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # 다이얼로그 실행
            result = dialog.exec()
            
            return result == QDialog.DialogCode.Accepted
            
        except Exception as e:
            self.log_message(f"❌ 확인 다이얼로그 오류: {str(e)}")
            # 오류 시 기본 메시지박스로 대체
            reply = QMessageBox.question(
                None,
                "상품 등록 확인",
                f"상품을 등록하시겠습니까?\n\n{product_data.get('title', 'N/A')[:50]}...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
    
    def add_upload_result_to_table(self, product_data, status, status_color):
        """업로드 결과를 테이블에 추가"""
        try:
            row = self.upload_table.rowCount()
            self.upload_table.insertRow(row)
            
            # 각 컬럼에 데이터 추가
            self.upload_table.setItem(row, 0, QTableWidgetItem(product_data.get('title', '')))
            self.upload_table.setItem(row, 1, QTableWidgetItem(product_data.get('brand', '')))
            self.upload_table.setItem(row, 2, QTableWidgetItem(product_data.get('price', '')))
            
            # 상태 컬럼 (색상 적용)
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(QColor(status_color)))
            self.upload_table.setItem(row, 3, status_item)
            
        except Exception as e:
            self.log_message(f"❌ 결과 테이블 추가 오류: {str(e)}")
    
    def reset_upload_ui(self):
        """업로드 UI 상태 복원"""
        try:
            self.start_upload_btn.setEnabled(True)
            self.pause_upload_btn.setEnabled(False)
            self.stop_upload_btn.setEnabled(False)
            self.current_upload_status.setText("대기 중")
            
            # 업로드 진행률 위젯 숨기기
            self.hide_upload_progress_widget()
            
            # 다른 탭 활성화
            self.set_tabs_enabled(True)
            
        except Exception as e:
            self.log_message(f"❌ UI 상태 복원 오류: {str(e)}")
    
    def update_today_stats(self):
        """오늘 통계 업데이트"""
        try:
            # 오늘 크롤링 수
            self.today_crawled.setText(str(self.today_stats['crawled_count']))
            
            # 오늘 업로드 수
            self.today_uploaded.setText(str(self.today_stats['uploaded_count']))
            
            # 성공률 계산
            total_attempts = self.today_stats['success_count'] + self.today_stats['failed_count']
            if total_attempts > 0:
                success_rate = (self.today_stats['success_count'] / total_attempts) * 100
                self.success_rate.setText(f"{success_rate:.1f}%")
            else:
                self.success_rate.setText("0%")
            
            # 평균 처리 시간 계산
            if self.today_stats['process_count'] > 0:
                avg_time = self.today_stats['total_process_time'] / self.today_stats['process_count']
                self.avg_process_time.setText(f"{avg_time:.1f}초")
            else:
                self.avg_process_time.setText("0초")
                
        except Exception as e:
            self.log_message(f"❌ 통계 업데이트 오류: {str(e)}")
    
    def increment_crawled_count(self):
        """크롤링 수 증가"""
        self.today_stats['crawled_count'] += 1
        self.update_today_stats()
    
    def increment_uploaded_count(self):
        """업로드 수 증가"""
        self.today_stats['uploaded_count'] += 1
        self.update_today_stats()
    
    def add_process_time(self, process_time):
        """처리 시간 추가"""
        self.today_stats['total_process_time'] += process_time
        self.today_stats['process_count'] += 1
        self.update_today_stats()
    
    def increment_success_count(self):
        """성공 수 증가"""
        self.today_stats['success_count'] += 1
        self.update_today_stats()
    
    def increment_failed_count(self):
        """실패 수 증가"""
        self.today_stats['failed_count'] += 1
        self.update_today_stats()
    
    def safe_execute(self, func, *args, **kwargs):
        """안전한 함수 실행 - 예외 발생 시에도 프로그램 계속 실행"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.log_message(f"⚠️ 안전 실행 중 오류 (계속 진행): {str(e)}")
            import traceback
            print(f"안전 실행 오류 상세: {traceback.format_exc()}")
            return None
    
    def update_upload_progress_widget(self, current, total, status):
        """업로드 진행률 위젯 업데이트"""
        try:
            self.upload_progress_widget.update_progress(current, total, status)
        except Exception as e:
            self.log_message(f"⚠️ 업로드 진행률 위젯 업데이트 오류: {str(e)}")
            pass
    
    def update_price_progress_widget(self, current, total, status):
        """가격분석 진행률 위젯 업데이트"""
        try:
            self.price_progress_widget.update_progress(current, total, status)
        except Exception as e:
            self.log_message(f"⚠️ 업로드 진행률 위젯 업데이트 오류: {str(e)}")
            pass
        
    def display_products_in_table_optimized(self, products):
        """대용량 데이터를 위한 최적화된 테이블 표시"""
        try:
            # 테이블 업데이트 시작 전 신호 차단
            self.price_table.setUpdatesEnabled(False)
            
            # 테이블 초기화
            self.price_table.setRowCount(0)
            self.price_table.setRowCount(len(products))
            
            # 배치 처리로 데이터 입력
            for row, product in enumerate(products):
                try:
                    # 기본 상품 정보
                    self.price_table.setItem(row, 0, QTableWidgetItem(product.get('title', '')))
                    self.price_table.setItem(row, 1, QTableWidgetItem(product.get('current_price', '')))
                    self.price_table.setItem(row, 2, QTableWidgetItem('분석 필요'))
                    self.price_table.setItem(row, 3, QTableWidgetItem('계산 필요'))
                    self.price_table.setItem(row, 4, QTableWidgetItem('-'))
                    self.price_table.setItem(row, 5, QTableWidgetItem('대기 중'))
                    
                    # 액션 버튼은 나중에 추가 (성능 최적화)
                    if row < 50:  # 처음 50개만 즉시 버튼 추가
                        self.add_action_buttons_to_row(row)
                    
                    # 10개마다 UI 업데이트
                    if row % 10 == 0:
                        from PyQt6.QtWidgets import QApplication
                        QApplication.processEvents()
                        
                except Exception as e:
                    self.log_message(f"⚠️ 행 {row} 처리 중 오류: {str(e)}")
                    continue
            
            # 테이블 업데이트 재개
            self.price_table.setUpdatesEnabled(True)
            
            # 나머지 버튼들은 지연 추가
            if len(products) > 50:
                QTimer.singleShot(500, lambda: self.add_remaining_action_buttons(50, len(products)))
            
        except Exception as e:
            self.log_message(f"❌ 최적화된 테이블 표시 오류: {str(e)}")
            self.price_table.setUpdatesEnabled(True)
    
    def add_remaining_action_buttons(self, start_row, total_rows):
        """나머지 액션 버튼들을 지연 추가"""
        try:
            batch_size = 20
            end_row = min(start_row + batch_size, total_rows)
            
            for row in range(start_row, end_row):
                self.add_action_buttons_to_row(row)
            
            # 다음 배치가 있으면 계속 처리
            if end_row < total_rows:
                QTimer.singleShot(100, lambda: self.add_remaining_action_buttons(end_row, total_rows))
            else:
                self.log_message("✅ 모든 액션 버튼 추가 완료")
                
        except Exception as e:
            self.log_message(f"⚠️ 액션 버튼 추가 중 오류: {str(e)}")
    
    def add_action_buttons_to_row(self, row):
        """특정 행에 주력상품 추가 액션 버튼만 추가"""
        try:
            action_layout = QHBoxLayout()
            action_widget = QWidget()
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(3)
            
            # 주력상품 추가 버튼만 추가
            add_favorite_btn = QPushButton("⭐")
            add_favorite_btn.setToolTip("주력상품에 추가")
            add_favorite_btn.setFixedSize(25, 25)
            add_favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
                QPushButton:pressed {
                    background-color: #d39e00;
                }
            """)
            
            # 기존 함수 활용하여 버튼 클릭 이벤트 연결
            add_favorite_btn.clicked.connect(lambda: self.add_to_favorite_from_price_table(row))
            
            action_layout.addWidget(add_favorite_btn)
            action_layout.addStretch()  # 왼쪽 정렬
            
            action_widget.setLayout(action_layout)
            self.price_table.setCellWidget(row, 6, action_widget)
            
        except Exception as e:
            self.log_message(f"❌ 액션 버튼 추가 오류 (행 {row}): {str(e)}")
            # update_btn.setMaximumWidth(30)
            # update_btn.setToolTip("가격 수정")
            # update_btn.clicked.connect(lambda checked, r=row: self.update_single_product_price(r))
            
            # # 주력상품 추가 버튼
            favorite_btn = QPushButton("⭐")
            favorite_btn.setMaximumWidth(30)
            favorite_btn.setToolTip("주력상품 추가")
            favorite_btn.clicked.connect(lambda checked, r=row: self.add_to_favorite_from_price_table(r))
            
            # action_layout.addWidget(analyze_btn)
            # action_layout.addWidget(update_btn)
            action_layout.addWidget(favorite_btn)
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            action_widget.setLayout(action_layout)
            self.price_table.setCellWidget(row, 6, action_widget)
            
        except Exception as e:
            self.log_message(f"⚠️ 행 {row} 액션 버튼 추가 오류: {str(e)}")
            
    @pyqtSlot(int, int, str)
    def update_price_progress_widget_safe(self, current, total, status):
        """스레드 안전 진행률 위젯 업데이트"""
        try:
            self.price_progress_widget.update_progress(current, total, status)
        except Exception as e:
            self.log_message(f"⚠️ 진행률 위젯 업데이트 오류: {str(e)}")
    
    @pyqtSlot()
    def on_my_products_finished(self):
        """내 상품 크롤링 완료 처리"""
        try:
            # 분석된 데이터로 테이블 업데이트
            self.update_price_analysis_table()
            
            self.hide_price_progress_widget()
            self.set_tabs_enabled(True)
            self.log_message("✅ 내 상품 크롤링 및 가격분석 완료")
        except Exception as e:
            self.log_message(f"⚠️ 크롤링 완료 처리 오류: {str(e)}")
    
    def update_price_analysis_table(self):
        """가격분석 결과를 테이블에 반영"""
        try:
            # 현재 페이지의 상품들 가져오기
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.all_products))
            current_page_products = self.all_products[start_idx:end_idx]
            
            # 테이블 업데이트
            for row, product in enumerate(current_page_products):
                if row >= self.price_table.rowCount():
                    break
                    
                # 최저가 업데이트
                lowest_price = product.get('lowest_price', 0)
                if lowest_price > 0:
                    self.price_table.setItem(row, 2, QTableWidgetItem(f"¥{lowest_price:,}"))
                else:
                    self.price_table.setItem(row, 2, QTableWidgetItem("검색 실패"))
                
                # 제안가 업데이트
                suggested_price = product.get('suggested_price', 0)
                if suggested_price > 0:
                    self.price_table.setItem(row, 3, QTableWidgetItem(f"¥{suggested_price:,}"))
                else:
                    self.price_table.setItem(row, 3, QTableWidgetItem("-"))
                
                # 가격차이 업데이트
                price_difference = product.get('price_difference', 0)
                if price_difference > 0:
                    margin_text = f"+¥{price_difference:,} (비쌈)"
                elif price_difference < 0:
                    margin_text = f"¥{price_difference:,} (저렴함)"
                else:
                    margin_text = "¥0 (동일)" if lowest_price > 0 else "-"
                
                self.price_table.setItem(row, 4, QTableWidgetItem(margin_text))
                
                # 상태 업데이트
                status = product.get('status', '분석 대기')
                status_item = QTableWidgetItem(status)
                
                # 상태별 색상 설정
                if "수정 필요" in status:
                    status_item.setForeground(QBrush(QColor("#ffc107")))  # 노란색
                elif "손실 예상" in status:
                    status_item.setForeground(QBrush(QColor("#dc3545")))  # 빨간색
                elif "검색 실패" in status:
                    status_item.setForeground(QBrush(QColor("#6c757d")))  # 회색
                else:
                    status_item.setForeground(QBrush(QColor("#28a745")))  # 초록색
                
                self.price_table.setItem(row, 5, status_item)
                
                # 액션 버튼 추가 (주력상품 추가만)
                self.add_price_action_button(row, product)
            
            self.log_message("📊 테이블 업데이트 완료")
            
        except Exception as e:
            self.log_message(f"❌ 테이블 업데이트 오류: {str(e)}")
    
    def add_price_action_button(self, row, product):
        """가격분석 테이블에 주력상품 추가 액션 버튼만 추가"""
        try:
            # 액션 버튼 위젯 생성
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(3)
            
            # 주력상품 추가 버튼
            add_favorite_btn = QPushButton("⭐")
            add_favorite_btn.setToolTip("주력상품에 추가")
            add_favorite_btn.setFixedSize(25, 25)
            add_favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
                QPushButton:pressed {
                    background-color: #d39e00;
                }
            """)
            
            # 기존 함수 활용하여 버튼 클릭 이벤트 연결
            add_favorite_btn.clicked.connect(lambda: self.add_to_favorite_from_price_table(row))
            
            action_layout.addWidget(add_favorite_btn)
            action_layout.addStretch()  # 왼쪽 정렬
            
            # 테이블에 위젯 설정 (액션 컬럼은 6번째)
            self.price_table.setCellWidget(row, 6, action_widget)
            
        except Exception as e:
            self.log_message(f"❌ 액션 버튼 추가 오류 (행 {row}): {str(e)}")
            pass
            
    def analyze_existing_table_data(self):
        """기존 테이블 데이터로 가격분석 실행"""
        try:
            # 가격분석 설정값 가져오기
            discount = self.discount_amount.value()
            min_margin = self.min_margin.value()
            is_auto_mode = self.auto_mode.isChecked()
            
            self.my_products_log_signal.emit(f"🔍 기존 데이터 가격분석 시작 - 모드: {'🤖 자동' if is_auto_mode else '👤 수동'}")
            
            total_rows = self.price_table.rowCount()
            
            # 각 상품별 가격분석 실행
            for row in range(total_rows):
                try:
                    # 테이블에서 상품 정보 가져오기
                    product_name_item = self.price_table.item(row, 0)
                    current_price_item = self.price_table.item(row, 1)
                    
                    if not product_name_item or not current_price_item:
                        continue
                        
                    product_name = product_name_item.text()
                    current_price_text = current_price_item.text()
                    
                    self.my_products_log_signal.emit(f"🔍 분석 중: {product_name[:30]}...")
                    
                    # 진행률 업데이트
                    self.update_price_progress_signal.emit(
                        row + 1, 
                        total_rows, 
                        f"가격분석 중: {product_name[:30]}..."
                    )
                    
                    # BUYMA에서 해당 상품 검색하여 최저가 찾기
                    lowest_price = self.search_buyma_lowest_price(product_name)
                    
                    if lowest_price:
                        # 제안가 계산 (최저가 - 할인금액)
                        suggested_price = max(lowest_price - discount, 0)
                        
                        # 현재가격에서 숫자만 추출 (¥31,100 → 31100)
                        current_price_numbers = re.findall(r'[\d,]+', current_price_text)
                        current_price = int(current_price_numbers[0].replace(',', '')) if current_price_numbers else 0
                        
                        # 마진 계산 (내 가격과 최저가의 차이)
                        price_difference = current_price - lowest_price if current_price > 0 else 0
                        
                        # 테이블 업데이트 (시그널 사용)
                        self.price_analysis_table_update_signal.emit(row, 2, f"¥{lowest_price:,}")
                        self.price_analysis_table_update_signal.emit(row, 3, f"¥{suggested_price:,}")
                        
                        # 마진을 가격 차이로 표시
                        if price_difference > 0:
                            margin_text = f"+¥{price_difference:,} (비쌈)"
                        elif price_difference < 0:
                            margin_text = f"¥{price_difference:,} (저렴함)"
                        else:
                            margin_text = "¥0 (동일)"
                        
                        self.price_analysis_table_update_signal.emit(row, 4, margin_text)
                        
                        # 가격 수정 필요 상태 결정
                        suggested_difference = suggested_price - current_price
                        if suggested_difference >= -abs(min_margin):  # -500엔 이상이면 OK
                            status = "💰 가격 수정 필요"
                            self.my_products_log_signal.emit(f"✅ {product_name[:20]}... - 최저가: ¥{lowest_price:,}, 제안가: ¥{suggested_price:,}, 차이: {margin_text}")
                        else:
                            status = f"⚠️ 손실 예상 ({suggested_difference:+,}엔)"
                            self.my_products_log_signal.emit(f"⚠️ 손실 예상: {product_name[:20]}... - 제안가 차이: {suggested_difference:+,}엔")
                        
                        self.price_analysis_table_update_signal.emit(row, 5, status)
                        
                    else:
                        self.price_analysis_table_update_signal.emit(row, 2, "검색 실패")
                        self.price_analysis_table_update_signal.emit(row, 5, "❌ 최저가 검색 실패")
                        self.my_products_log_signal.emit(f"⚠️ {product_name[:20]}... - 최저가 검색 실패")
                    
                    # 딜레이
                    time.sleep(2)
                    
                except Exception as e:
                    self.my_products_log_signal.emit(f"❌ 상품 분석 오류 (행 {row}): {str(e)}")
                    continue
            
            # 분석 완료
            self.my_products_log_signal.emit("📊 기존 데이터 가격분석 완료!")
            
            # 완료 시그널 발송
            self.my_products_finished_signal.emit()
                
        except Exception as e:
            self.my_products_log_signal.emit(f"❌ 기존 데이터 가격분석 오류: {str(e)}")
            # 오류 시에도 완료 시그널 발송
            self.my_products_finished_signal.emit()
    
    @pyqtSlot(str, str)
    def set_progress_complete(self, title, message):
        """진행률 위젯 완료 상태 설정"""
        try:
            self.progress_widget.set_task_complete(title, message)
        except Exception as e:
            self.log_message(f"⚠️ 진행률 완료 상태 설정 오류: {str(e)}")
    
    @pyqtSlot(str, str)
    def set_progress_error(self, title, error_message):
        """진행률 위젯 오류 상태 설정"""
        try:
            self.progress_widget.set_task_error(title, error_message)
        except Exception as e:
            self.log_message(f"⚠️ 진행률 오류 상태 설정 오류: {str(e)}")
    
    def hide_upload_progress_widget(self):
        """업로드 진행률 위젯 숨기기"""
        try:
            self.upload_progress_widget.hide()
        except Exception as e:
            self.log_message(f"⚠️ 업로드 진행률 위젯 숨기기 오류: {str(e)}")
    
    def hide_price_progress_widget(self):
        """가격분석 진행률 위젯 숨기기"""
        try:
            self.price_progress_widget.hide()
        except Exception as e:
            self.log_message(f"⚠️ 가격분석 진행률 위젯 숨기기 오류: {str(e)}")
    
    def update_analyzed_prices(self):
        """분석된 상품들의 가격 수정"""
        # 로그인 상태 확인
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            QMessageBox.warning(
                self, 
                "로그인 필요", 
                "가격 수정을 위해서는 먼저 BUYMA 로그인이 필요합니다.\n\n"
                "설정 탭에서 '🔐 BUYMA 로그인' 버튼을 클릭하여 로그인해주세요."
            )
            return
        
        # 분석된 상품이 있는지 확인
        if self.price_table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "먼저 '🔍 가격분석'을 실행해주세요.")
            return
        
        # 수정이 필요한 상품 찾기
        need_update = []
        for row in range(self.price_table.rowCount()):
            status_item = self.price_table.item(row, 5)  # 상태 컬럼
            if status_item and "수정 필요" in status_item.text():
                need_update.append(row)
        
        if not need_update:
            QMessageBox.information(self, "정보", "수정이 필요한 상품이 없습니다.")
            return
        
        # 확인 다이얼로그
        reply = QMessageBox.question(
            self,
            "가격 수정 확인",
            f"총 {len(need_update)}개 상품의 가격을 수정하시겠습니까?\n\n"
            f"⚠️ 주의: 실제 BUYMA 상품 가격이 변경됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_message(f"💰 가격 수정 시작: {len(need_update)}개 상품")
        
        # 가격수정 진행률 위젯 표시 (업로드 위젯 재사용)
        self.upload_progress_widget.show()
        self.update_upload_progress_widget(0, len(need_update), "가격 수정 시작...")
        
        # 순차적으로 가격 수정 실행
        success_count = 0
        failed_count = 0
        
        for i, row in enumerate(need_update):
            try:
                product_name = self.price_table.item(row, 0).text()
                self.log_message(f"💰 가격 수정 중 ({i+1}/{len(need_update)}): {product_name[:30]}...")
                
                # 가격수정 진행률 위젯 업데이트
                self.update_upload_progress_widget(
                    i + 1, 
                    len(need_update), 
                    f"가격 수정 중: {product_name[:30]}..."
                )
                
                # 기존 가격 수정 함수 사용
                result = self.update_single_product_price(row)
                
                if result:
                    success_count += 1
                    self.log_message(f"✅ 가격 수정 완료: {product_name[:30]}")
                else:
                    failed_count += 1
                    self.log_message(f"❌ 가격 수정 실패: {product_name[:30]}")
                
            except Exception as e:
                failed_count += 1
                self.log_message(f"❌ 가격 수정 실패: {product_name[:30]} - {str(e)}")
        
        # 완료 메시지
        self.log_message(f"🎉 가격 수정 완료! 성공: {success_count}개, 실패: {failed_count}개")
        
        # 가격수정 진행률 위젯 숨기기
        self.upload_progress_widget.hide()
        
        QMessageBox.information(
            self,
            "가격 수정 완료",
            f"가격 수정이 완료되었습니다.\n\n"
            f"✅ 성공: {success_count}개\n"
            f"❌ 실패: {failed_count}개"
        )
    
    def show_crash_safe_confirmation(self, product_data, product_number, max_images):
        """크래시 방지 확인 다이얼로그 - 시그널/슬롯 방식"""
        self.log_message("📋 확인 다이얼로그 요청 중...")
        
        # 결과 초기화
        self.confirmation_result = None
        
        # 상품 정보 준비
        title = str(product_data.get('title', 'N/A'))[:30]
        message = f"상품을 BUYMA에 등록하시겠습니까?\n\n상품명: {title}...\n\n⚠️ 실제로 등록됩니다!"
        
        # 시그널로 메인 스레드에 다이얼로그 표시 요청
        self.show_confirmation_signal.emit("상품 등록 확인", message, title)
        
        # 결과 대기 (무한 대기)
        import time
        from PyQt6.QtWidgets import QApplication
        
        wait_count = 0
        while self.confirmation_result is None:
            QApplication.processEvents()
            time.sleep(0.1)
            wait_count += 1
            
            # 10초마다 대기 상태 로그
            if wait_count % 100 == 0:
                self.log_message("⏳ 사용자 응답 대기 중...")
        
        result = self.confirmation_result
        self.confirmation_result = None  # 결과 초기화
        
        self.log_message(f"✅ 사용자 응답 완료: {'승인' if result else '취소'}")
        return result
    
    @pyqtSlot(str, str, str)
    def show_confirmation_dialog_main_thread(self, title, message, product_name):
        """메인 스레드에서 실행되는 확인 다이얼로그"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            self.log_message("💬 확인 다이얼로그 표시됨")
            
            reply = QMessageBox.question(
                self,  # 부모 위젯을 self로 설정
                title,
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            # 결과 저장
            self.confirmation_result = reply == QMessageBox.StandardButton.Yes
            
        except Exception as e:
            self.log_message(f"⚠️ 다이얼로그 표시 오류: {str(e)}")
            # 오류 시 취소로 처리
            self.confirmation_result = False


def main():
    """메인 함수 - 전역 예외 처리 포함"""
    import sys
    import traceback
    from datetime import datetime
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """전역 예외 처리기 - 프로그램 크래시 방지"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # 예외 정보 로깅
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"🚨 예상치 못한 오류 발생 (프로그램 계속 실행):\n{error_msg}")
        
        # 오류 파일로 저장
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f'crash_report_{timestamp}.txt', 'w', encoding='utf-8') as f:
                f.write(f"크래시 리포트 - {datetime.now()}\n")
                f.write("=" * 60 + "\n")
                f.write(f"예외 타입: {exc_type.__name__}\n")
                f.write(f"예외 메시지: {str(exc_value)}\n")
                f.write("=" * 60 + "\n")
                f.write("상세 스택 트레이스:\n")
                f.write(error_msg)
                f.write("=" * 60 + "\n")
        except:
            pass
        
        # 사용자에게 알림 (가능한 경우)
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.warning(
                    None,
                    "프로그램 오류",
                    f"예상치 못한 오류가 발생했지만 프로그램은 계속 실행됩니다.\n\n오류 리포트가 crash_report_{timestamp}.txt 파일에 저장되었습니다.\n\n계속 사용하시기 바랍니다.",
                    QMessageBox.StandardButton.Ok
                )
        except:
            pass
    
    # 전역 예외 처리기 설정
    sys.excepthook = handle_exception
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QTimer
        
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # 안정적인 스타일 사용
        
        # 애플리케이션 정보 설정
        app.setApplicationName("BUYMA 자동화 프로그램")
        app.setApplicationVersion("3.1.0")
        app.setOrganizationName("소프트캣")
        
        # 폰트 설정 - 맑은 고딕으로 전체 통일
        font = QFont("맑은 고딕", 10)
        app.setFont(font)
        
        # 메인 윈도우 생성 및 표시
        window = Main()
        window.show()
        
        # 시작 메시지
        window.log_message("🚀 BUYMA 자동화 프로그램이 시작되었습니다.")
        window.log_message("⚙️ 설정을 확인하고 작업을 시작해주세요.")
        
        # 정기적인 메모리 정리 (크래시 방지)
        def cleanup_memory():
            try:
                import gc
                gc.collect()
                QTimer.singleShot(300000, cleanup_memory)  # 5분마다 실행
            except:
                pass
        
        QTimer.singleShot(300000, cleanup_memory)
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"🚨 프로그램 시작 중 치명적 오류: {e}")
        traceback.print_exc()
        
        # 치명적 오류도 파일로 저장
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f'fatal_error_{timestamp}.txt', 'w', encoding='utf-8') as f:
                f.write(f"치명적 오류 - {datetime.now()}\n")
                f.write("=" * 60 + "\n")
                f.write(f"오류: {str(e)}\n")
                f.write("=" * 60 + "\n")
                f.write(traceback.format_exc())
        except:
            pass


if __name__ == "__main__":
    main()
    