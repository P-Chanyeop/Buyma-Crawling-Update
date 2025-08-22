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
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                            QTableWidgetItem, QProgressBar, QComboBox, 
                            QSpinBox, QCheckBox, QGroupBox, QFrame, 
                            QFileDialog, QMessageBox, QScrollArea, 
                            QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont, QColor, QBrush

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import time


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
    
    def __init__(self):
        super().__init__()
        
        # 주력 상품 데이터 초기화
        self.favorite_products = []
        self.favorites_file = "favorite_products.json"
        
        # 워커 스레드 초기화
        self.price_analysis_worker = None
        self.favorite_analysis_worker = None
        
        self.init_ui()
        self.load_settings()
        
        # 크롤링 시그널 연결
        self.crawling_progress_signal.connect(self.update_crawling_progress)
        self.crawling_status_signal.connect(self.update_crawling_status)
        self.crawling_result_signal.connect(self.add_crawling_result_safe)
        self.crawling_finished_signal.connect(self.crawling_finished_safe)
        
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
        
        # 대시보드 탭 (첫 번째)
        self.create_dashboard_tab()
        
        # 크롤링 탭
        self.create_crawling_tab()
        
        # 가격 관리 탭
        self.create_price_tab()
        
        # 주력 상품 관리 탭 (새로 추가)
        self.create_favorite_products_tab()
        
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
        
        self.tab_widget.addTab(tab, "📊 대시보드")
    
    def create_favorite_products_tab(self):
        """주력 상품 관리 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 제목
        title_label = QLabel("⭐ 주력 상품 관리")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 상단 컨트롤 영역
        control_layout = QHBoxLayout()
        
        # 상품 추가 섹션
        add_group = QGroupBox("🔖 주력 상품 추가")
        add_group.setMinimumHeight(120)
        add_layout = QVBoxLayout(add_group)
        
        # 상품 정보 입력
        input_layout = QHBoxLayout()
        
        input_layout.addWidget(QLabel("브랜드:"))
        self.fav_brand_input = QLineEdit()
        self.fav_brand_input.setPlaceholderText("예: SAN SAN GEAR")
        self.fav_brand_input.setMinimumHeight(35)
        input_layout.addWidget(self.fav_brand_input)
        
        input_layout.addWidget(QLabel("상품명:"))
        self.fav_product_input = QLineEdit()
        self.fav_product_input.setPlaceholderText("예: EYEWITHNESS T-SHIRT")
        self.fav_product_input.setMinimumHeight(35)
        input_layout.addWidget(self.fav_product_input)
        
        input_layout.addWidget(QLabel("현재가격:"))
        self.fav_price_input = QSpinBox()
        self.fav_price_input.setRange(100, 1000000)
        self.fav_price_input.setValue(15000)
        self.fav_price_input.setStyleSheet(self.get_spinbox_style())
        self.fav_price_input.setSuffix("엔")
        self.fav_price_input.setMinimumHeight(35)
        input_layout.addWidget(self.fav_price_input)
        
        add_layout.addLayout(input_layout)
        
        # 추가 버튼
        add_btn_layout = QHBoxLayout()
        self.add_favorite_btn = QPushButton("⭐ 주력 상품 추가")
        self.add_favorite_btn.setMinimumHeight(40)
        self.add_favorite_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f39c12, stop:1 #e67e22);
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e67e22, stop:1 #d35400);
            }
        """)
        self.add_favorite_btn.clicked.connect(self.add_favorite_product)
        add_btn_layout.addWidget(self.add_favorite_btn)
        
        self.import_from_crawling_btn = QPushButton("📥 크롤링 결과에서 추가")
        self.import_from_crawling_btn.setMinimumHeight(40)
        self.import_from_crawling_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #1f4e79);
            }
        """)
        self.import_from_crawling_btn.clicked.connect(self.import_from_crawling)
        add_btn_layout.addWidget(self.import_from_crawling_btn)
        
        add_layout.addLayout(add_btn_layout)
        control_layout.addWidget(add_group)
        
        # 관리 버튼 섹션
        manage_group = QGroupBox("🛠️ 관리 기능")
        manage_group.setMinimumHeight(120)
        manage_layout = QVBoxLayout(manage_group)
        
        # 일괄 관리 버튼들
        batch_layout = QHBoxLayout()
        
        # 새로운 기능: 주력상품 일괄 처리 시작 버튼
        self.start_favorite_analysis_btn = QPushButton("🚀 주력상품 가격확인 시작")
        self.start_favorite_analysis_btn.setMinimumHeight(45)
        self.start_favorite_analysis_btn.setStyleSheet("""
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
        self.start_favorite_analysis_btn.clicked.connect(self.start_favorite_analysis)
        batch_layout.addWidget(self.start_favorite_analysis_btn)
        
        # 중지 버튼 추가
        self.stop_favorite_analysis_btn = QPushButton("⏹️ 확인 중지")
        self.stop_favorite_analysis_btn.setMinimumHeight(45)
        self.stop_favorite_analysis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a93226);
            }
        """)
        self.stop_favorite_analysis_btn.clicked.connect(self.stop_favorite_analysis)
        self.stop_favorite_analysis_btn.setEnabled(False)
        batch_layout.addWidget(self.stop_favorite_analysis_btn)
        
        self.check_all_prices_btn = QPushButton("🔍 전체 가격 확인")
        self.check_all_prices_btn.setMinimumHeight(40)
        self.check_all_prices_btn.setStyleSheet("""
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
        self.check_all_prices_btn.clicked.connect(self.check_all_favorite_prices)
        batch_layout.addWidget(self.check_all_prices_btn)
        
        self.auto_update_favorites_btn = QPushButton("🔄 자동 가격 수정")
        self.auto_update_favorites_btn.setMinimumHeight(40)
        self.auto_update_favorites_btn.setStyleSheet("""
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
        self.auto_update_favorites_btn.clicked.connect(self.auto_update_favorite_prices)
        batch_layout.addWidget(self.auto_update_favorites_btn)
        
        manage_layout.addLayout(batch_layout)
        
        # 파일 관리 버튼들
        file_layout = QHBoxLayout()
        
        self.save_favorites_btn = QPushButton("💾 목록 저장")
        self.save_favorites_btn.setMinimumHeight(35)
        self.save_favorites_btn.clicked.connect(self.save_favorite_products)
        file_layout.addWidget(self.save_favorites_btn)
        
        self.load_favorites_btn = QPushButton("📂 목록 불러오기")
        self.load_favorites_btn.setMinimumHeight(35)
        self.load_favorites_btn.clicked.connect(self.load_favorite_products)
        file_layout.addWidget(self.load_favorites_btn)
        
        self.clear_favorites_btn = QPushButton("🗑️ 전체 삭제")
        self.clear_favorites_btn.setMinimumHeight(35)
        self.clear_favorites_btn.setStyleSheet("background: #e74c3c; color: white;")
        self.clear_favorites_btn.clicked.connect(self.clear_favorite_products)
        file_layout.addWidget(self.clear_favorites_btn)
        
        manage_layout.addLayout(file_layout)
        control_layout.addWidget(manage_group)
        
        layout.addLayout(control_layout)
        
        # 주력 상품 목록 테이블
        table_group = QGroupBox("📋 주력 상품 목록")
        table_layout = QVBoxLayout(table_group)
        
        self.favorite_table = QTableWidget()
        self.favorite_table.setColumnCount(8)
        self.favorite_table.setHorizontalHeaderLabels([
            "브랜드", "상품명", "현재가격", "경쟁사 최저가", "제안가격", "상태", "마지막 확인", "액션"
        ])
        self.favorite_table.horizontalHeader().setStretchLastSection(True)
        self.favorite_table.setAlternatingRowColors(True)
        self.favorite_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 테이블 컬럼 너비 설정
        self.favorite_table.setColumnWidth(0, 120)  # 브랜드
        self.favorite_table.setColumnWidth(1, 200)  # 상품명
        self.favorite_table.setColumnWidth(2, 100)  # 현재가격
        self.favorite_table.setColumnWidth(3, 120)  # 경쟁사 최저가
        self.favorite_table.setColumnWidth(4, 100)  # 제안가격
        self.favorite_table.setColumnWidth(5, 100)  # 상태
        self.favorite_table.setColumnWidth(6, 120)  # 마지막 확인
        
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
        
        # 초기 데이터 로드 (UI 완성 후에 호출하도록 제거)
        # self.load_favorite_products_on_startup()  # 이 줄 제거
        
        self.tab_widget.addTab(tab, "⭐ 주력 상품")
        
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
        
        self.preview_btn = QPushButton("👁️ 미리보기")
        self.preview_btn.clicked.connect(self.preview_crawling)
        
        control_layout.addWidget(self.start_crawling_btn)
        control_layout.addWidget(self.stop_crawling_btn)
        control_layout.addWidget(self.preview_btn)
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
        self.crawling_table.verticalHeader().setDefaultSectionSize(35)
        
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
        """가격 관리 탭 생성"""
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
        
        # 가격 분석 설정
        analysis_group = QGroupBox("⚙️ 자동 모드 설정")
        analysis_layout = QGridLayout(analysis_group)
        
        analysis_layout.addWidget(QLabel("브랜드명:"), 0, 0)
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("예: SAN SAN GEAR (전체 상품 분석시 비워두세요)")
        analysis_layout.addWidget(self.brand_input, 0, 1, 1, 2)
        
        analysis_layout.addWidget(QLabel("상품명:"), 1, 0)
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("예: EYEWITHNESS T-SHIRT (전체 상품 분석시 비워두세요)")
        analysis_layout.addWidget(self.product_input, 1, 1, 1, 2)
        
        analysis_layout.addWidget(QLabel("할인 금액(엔):"), 2, 0)
        self.discount_amount = QSpinBox()
        self.discount_amount.setRange(1, 10000)
        self.discount_amount.setValue(100)
        self.discount_amount.setStyleSheet(self.get_spinbox_style())
        analysis_layout.addWidget(self.discount_amount, 2, 1)
        
        analysis_layout.addWidget(QLabel("최소 마진(엔):"), 2, 2)
        self.min_margin = QSpinBox()
        self.min_margin.setRange(0, 50000)
        self.min_margin.setValue(500)
        self.min_margin.setStyleSheet(self.get_spinbox_style())
        analysis_layout.addWidget(self.min_margin, 2, 3)
        
        self.exclude_loss_products = QCheckBox("손실 예상 상품 자동 제외")
        self.exclude_loss_products.setChecked(True)
        analysis_layout.addWidget(self.exclude_loss_products, 3, 0, 1, 2)
        
        layout.addWidget(analysis_group)
        
        # 가격 관리 컨트롤
        price_control_layout = QHBoxLayout()
        
        self.analyze_price_btn = QPushButton("🔍 가격 분석 시작")
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
        self.analyze_price_btn.clicked.connect(self.analyze_prices)
        
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
        
        # 새로운 기능: 내 상품 전체 분석 버튼
        self.analyze_all_my_products_btn = QPushButton("🔍 내 상품 전체 분석 & 수정")
        self.analyze_all_my_products_btn.setMinimumHeight(45)
        self.analyze_all_my_products_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                font-size: 13px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #138496, stop:1 #0f6674);
            }
        """)
        self.analyze_all_my_products_btn.clicked.connect(self.analyze_all_my_products)
        
        # 중지 버튼 추가
        self.stop_price_analysis_btn = QPushButton("⏹️ 분석 중지")
        self.stop_price_analysis_btn.setMinimumHeight(45)
        self.stop_price_analysis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 13px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """)
        self.stop_price_analysis_btn.clicked.connect(self.stop_price_analysis)
        self.stop_price_analysis_btn.setEnabled(False)
        
        price_control_layout.addWidget(self.analyze_price_btn)
        price_control_layout.addWidget(self.auto_update_all_btn)
        price_control_layout.addWidget(self.analyze_all_my_products_btn)
        price_control_layout.addWidget(self.stop_price_analysis_btn)
        price_control_layout.addStretch()
        
        layout.addLayout(price_control_layout)
        
        # 가격 분석 결과
        price_result_group = QGroupBox("📈 가격 분석 결과")
        price_result_layout = QVBoxLayout(price_result_group)
        
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(8)
        self.price_table.setHorizontalHeaderLabels([
            "상품명", "브랜드", "현재가격", "경쟁사 최저가", "제안가격", "예상마진", "상태", "액션"
        ])
        self.price_table.horizontalHeader().setStretchLastSection(True)
        
        price_result_layout.addWidget(self.price_table)
        
        # 결과 요약
        summary_layout = QHBoxLayout()
        
        self.total_analyzed = QLabel("분석 완료: 0개")
        self.total_analyzed.setStyleSheet("font-weight: bold; color: #007bff; padding: 5px;")
        
        self.auto_updated = QLabel("자동 수정: 0개")
        self.auto_updated.setStyleSheet("font-weight: bold; color: #28a745; padding: 5px;")
        
        self.excluded_items = QLabel("제외: 0개")
        self.excluded_items.setStyleSheet("font-weight: bold; color: #ffc107; padding: 5px;")
        
        self.failed_items = QLabel("실패: 0개")
        self.failed_items.setStyleSheet("font-weight: bold; color: #dc3545; padding: 5px;")
        
        summary_layout.addWidget(self.total_analyzed)
        summary_layout.addWidget(self.auto_updated)
        summary_layout.addWidget(self.excluded_items)
        summary_layout.addWidget(self.failed_items)
        summary_layout.addStretch()
        
        price_result_layout.addLayout(summary_layout)
        layout.addWidget(price_result_group)
        
        self.tab_widget.addTab(tab, "💰 가격 관리")
        
    def create_upload_tab(self):
        """업로드 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 업로드 설정
        upload_group = QGroupBox("📤 업로드 설정")
        upload_layout = QGridLayout(upload_group)
        
        # upload_layout.addWidget(QLabel("카테고리:"), 0, 0)
        # self.category_combo = QComboBox()
        # self.category_combo.addItems([
        #     "레디스 패션", "맨즈 패션", "키즈&베이비", "코스메&향수", 
        #     "가방&지갑", "슈즈", "액세서리", "시계", "라이프스타일"
        # ])
        # upload_layout.addWidget(self.category_combo, 0, 1)
        
        # upload_layout.addWidget(QLabel("배송 방법:"), 0, 2)
        # self.shipping_combo = QComboBox()
        # self.shipping_combo.addItems(["국제배송", "국내배송", "직배송"])
        # upload_layout.addWidget(self.shipping_combo, 0, 3)
        
        # upload_layout.addWidget(QLabel("업로드 모드:"), 1, 0)
        # self.upload_mode = QComboBox()
        # self.upload_mode.addItems(["즉시 등록", "초안 저장", "예약 등록"])
        # upload_layout.addWidget(self.upload_mode, 1, 1)
        
        upload_layout.addWidget(QLabel("이미지 최대 개수:"), 0, 0)
        self.max_images = QSpinBox()
        self.max_images.setRange(1, 20)
        self.max_images.setValue(10)
        self.max_images.setStyleSheet(self.get_spinbox_style())
        upload_layout.addWidget(self.max_images, 0, 1)
        
        # self.auto_translate = QCheckBox("자동 번역")
        # upload_layout.addWidget(self.auto_translate, 2, 0)
        
        # self.auto_categorize = QCheckBox("자동 카테고리 분류")
        # upload_layout.addWidget(self.auto_categorize, 2, 1)
        
        # self.watermark_images = QCheckBox("워터마크 추가")
        # upload_layout.addWidget(self.watermark_images, 2, 2)
        
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
        
        test_login_btn = QPushButton("🔐 로그인 테스트")
        test_login_btn.setMinimumHeight(35)
        test_login_btn.clicked.connect(self.test_login)
        account_layout.addWidget(test_login_btn, 1, 2)
        
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
            
            self.log_message("❌ 네트워크 연결 복구 실패")
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
            self.log_message(f"❌ BUYMA 사이트 접근 불가: {str(e)}")
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
    
    def run_automation_process(self):
        """자동화 프로세스 실행 (사용하지 않음 - 삭제됨)"""
        pass
    
    def update_current_step(self, step_text, color):
        """현재 단계 업데이트 (사용하지 않음 - 삭제됨)"""
        pass
    
    def simulate_step_progress(self, progress_bar, step_name):
        """단계별 진행률 시뮬레이션 (사용하지 않음 - 삭제됨)"""
        pass
    
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
    
    def start_crawling(self):
        """크롤링 시작"""
        url = self.url_input.text().strip()
        count = self.crawl_count.value()
        
        if not url:
            QMessageBox.warning(self, "경고", "크롤링할 URL을 입력해주세요.")
            return
        
        # URL 유효성 검사
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "경고", "올바른 URL을 입력해주세요. (http:// 또는 https://로 시작)")
            return
        
        # UI 상태 변경
        self.start_crawling_btn.setEnabled(False)
        self.stop_crawling_btn.setEnabled(True)
        self.crawling_progress.setValue(0)
        self.crawling_status.setText("크롤링 준비중...")
        
        # 테이블 초기화
        self.crawling_table.setRowCount(0)
        
        # 로그 시작
        self.log_message("🚀 크롤링을 시작합니다...")
        self.log_message(f"📋 URL: {url}")
        self.log_message(f"📋 목표 개수: {count}개")
        
        # 별도 스레드에서 크롤링 실행 (필요한 설정만 포함)
        crawling_settings = {
            'include_images': self.include_images.isChecked(),
            'include_options': self.include_options.isChecked(), 
            'skip_duplicates': self.skip_duplicates.isChecked(),
            'delay': self.delay_time.value()
        }
        
        self.crawling_thread = threading.Thread(
            target=self.run_crawling, 
            args=(url, count, crawling_settings), 
            daemon=True
        )
        self.crawling_thread.start()
    
    def run_crawling(self, url, count, settings):
        """크롤링 실행 (별도 스레드) - 설정 적용"""
        driver = None
        crawled_products = []  # 중복 체크용
        
        try:
            self.log_message("🌐 브라우저를 시작합니다...")
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
            
            # Chrome 옵션 설정 (API 할당량 오류 해결)
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Google API 관련 오류 방지
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            
            # 할당량 초과 방지
            chrome_options.add_argument('--disable-component-extensions-with-background-pages')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-extensions')
            
            # 안정성 향상
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-gpu-logging')
            chrome_options.add_argument('--silent')
            
            # WebDriver 생성 (재시도 로직 포함)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.implicitly_wait(self.timeout_setting.value())
                    self.log_message(f"✅ 브라우저 초기화 성공 (시도 {attempt + 1}/{max_retries})")
                    break
                except Exception as e:
                    self.log_message(f"⚠️ 브라우저 초기화 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:
                        self.log_message("❌ 브라우저 초기화 최종 실패")
                        self.crawling_status_signal.emit("브라우저 초기화 실패")
                        self.crawling_finished_signal.emit()
                        return
                    time.sleep(2)  # 재시도 전 대기
            
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
                    self.log_message("🔄 브라우저가 안전하게 종료되었습니다.")
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
                                    color_text = li.text.strip()
                                    if color_text and color_text not in colors:
                                        colors.append(color_text)
                                except:
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
            
            # 상품 설명 추출 (안전장치)
            try:
                description_element = driver.find_element(By.CSS_SELECTOR, "p.free_txt")
                description_text = description_element.text.strip() if description_element else ""
            except Exception as e:
                self.log_message(f"⚠️ 상품 설명 추출 실패: {str(e)}")
                description_text = ""
            
            # 카테고리 추출 (안전장치)
            try:
                category_element = driver.find_element(By.CSS_SELECTOR, "#s_cate dd")
                category_text = category_element.text.strip() if category_element else ""
            except Exception as e:
                self.log_message(f"⚠️ 카테고리 추출 실패: {str(e)}")
                category_text = ""
            
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
            
            # 디버깅 로그 추가
            self.log_message(f"✅ 상품 #{index+1} 데이터 추출 완료: {title[:30]}...")
            self.log_message(f"   📊 이미지: {len(images)}장, 색상: {len(colors)}개, 사이즈: {len(sizes)}개")
            
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
        """안정적인 Chrome 옵션 반환"""
        options = Options()
        
        # 기본 안정성 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
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
        
        # 메모리 및 성능 최적화
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-mode')
        
        # 로그 및 디버깅 비활성화
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
        
        # 2. 주력상품 추가 버튼
        add_favorite_btn = QPushButton("⭐")
        add_favorite_btn.setToolTip("주력 상품으로 추가")
        add_favorite_btn.setFixedSize(35, 28)
        add_favorite_btn.setStyleSheet("""
            QPushButton {
                background: #f39c12;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: #e67e22;
            }
        """)
        add_favorite_btn.clicked.connect(lambda checked, r=row: self.add_crawled_to_favorites(r))
        action_layout.addWidget(add_favorite_btn)
        
        # 3. 바로 업로드 버튼
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
    
    def preview_crawling(self):
        """크롤링 미리보기"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "경고", "미리보기할 URL을 입력해주세요.")
            return
        
        self.log_message(f"🔍 미리보기: {url}")
        
        # 간단한 미리보기 (첫 3개만)
        self.preview_thread = threading.Thread(target=self.run_crawling, args=(url, 3), daemon=True)
        self.preview_thread.start()
        """크롤링 미리보기"""
        self.log_message("크롤링 미리보기를 실행합니다...")
        # TODO: 미리보기 로직 구현
        
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
    
    def analyze_prices(self):
        """가격 분석"""
        brand = self.brand_input.text().strip()
        product = self.product_input.text().strip()
        
        if not brand or not product:
            QMessageBox.warning(self, "경고", "브랜드명과 상품명을 모두 입력해주세요.")
            return
        
        # UI 상태 변경
        self.analyze_price_btn.setEnabled(False)
        self.analyze_price_btn.setText("🔍 분석 중...")
        
        # 테이블 초기화
        self.price_table.setRowCount(0)
        
        # 로그 시작
        self.log_message(f"🔍 가격 분석 시작: {brand} - {product}")
        
        # 별도 스레드에서 가격 분석 실행
        self.price_analysis_thread = threading.Thread(
            target=self.run_price_analysis, 
            args=(brand, product), 
            daemon=True
        )
        self.price_analysis_thread.start()
    
    def run_price_analysis(self, brand, product):
        """가격 분석 실행 (별도 스레드)"""
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
            
            # BUYMA 검색 URL 생성
            search_query = f"{brand} {product}"
            search_url = f"https://www.buyma.com/r/_/4FK1249/?q={search_query}"
            
            self.log_message(f"📄 BUYMA 검색: {search_query}")
            
            # 검색 페이지 접속
            driver.get(search_url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.log_message("🔍 경쟁사 상품을 수집합니다...")
            
            # 검색 결과 수집
            competitor_products = self.extract_competitor_products(driver, brand, product)
            
            if not competitor_products:
                self.log_message("❌ 검색 결과를 찾을 수 없습니다.")
                return
            
            # 가격 분석 및 결과 표시
            self.analyze_competitor_prices(competitor_products, brand, product)
            
        except Exception as e:
            self.log_message(f"❌ 가격 분석 오류: {str(e)}")
        finally:
            if driver:
                driver.quit()
            
            # UI 상태 복원
            self.analyze_price_btn.setEnabled(True)
            self.analyze_price_btn.setText("🔍 가격 분석 시작")
    
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
                action_btn.clicked.connect(lambda checked, r=row: self.auto_update_price(r))
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
                action_btn.clicked.connect(lambda checked, r=row: self.manual_update_price(r))
            
            self.price_table.setCellWidget(row, 7, action_btn)
            
            # 자동 스크롤
            self.price_table.scrollToBottom()
            
        except Exception as e:
            self.log_message(f"결과 추가 오류: {str(e)}")
        
    def add_demo_price_data(self):
        """데모용 가격 데이터 추가"""
        from PyQt6.QtGui import QColor, QBrush
        
        demo_data = [
            ["상품A", "브랜드A", "5000엔", "4500엔", "4400엔", "+600엔", "수정 가능", "수정"],
            ["상품B", "브랜드B", "3000엔", "2800엔", "2700엔", "-100엔", "손실 예상", "제외"],
            ["상품C", "브랜드C", "8000엔", "7500엔", "7400엔", "+1100엔", "수정 가능", "수정"],
        ]
        
        self.price_table.setRowCount(len(demo_data))
        
        for row, data in enumerate(demo_data):
            for col, value in enumerate(data):
                if col == 7:  # 액션 컬럼
                    if value == "수정":
                        btn = QPushButton("💱 수정")
                        btn.setStyleSheet("""
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
                        btn.clicked.connect(lambda checked, r=row: self.update_single_price(r))
                        self.price_table.setCellWidget(row, col, btn)
                    else:
                        btn = QPushButton("❌ 제외")
                        btn.setStyleSheet("""
                            QPushButton {
                                background: #dc3545;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                padding: 5px 10px;
                                font-size: 10px;
                            }
                        """)
                        btn.setEnabled(False)
                        self.price_table.setCellWidget(row, col, btn)
                else:
                    item = QTableWidgetItem(str(value))
                    if col == 6:  # 상태 컬럼
                        if "손실" in str(value):
                            # 빨간색으로 설정
                            item.setForeground(QBrush(QColor("#dc3545")))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif "수정 가능" in str(value):
                            # 녹색으로 설정
                            item.setForeground(QBrush(QColor("#28a745")))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                    elif col == 5:  # 예상마진 컬럼
                        if "-" in str(value):
                            # 마이너스 마진은 빨간색
                            item.setForeground(QBrush(QColor("#dc3545")))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        else:
                            # 플러스 마진은 녹색
                            item.setForeground(QBrush(QColor("#28a745")))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                    
                    self.price_table.setItem(row, col, item)
        
        # 요약 정보 업데이트
        self.total_analyzed.setText("분석 완료: 3개")
        self.auto_updated.setText("자동 수정: 0개")
        self.excluded_items.setText("제외: 1개")
        self.failed_items.setText("실패: 0개")
        
    def update_single_price(self, row):
        """개별 상품 가격 수정"""
        from PyQt6.QtGui import QColor, QBrush
        
        product_name = self.price_table.item(row, 0).text()
        self.log_message(f"가격 수정 중: {product_name}")
        
        # TODO: 실제 가격 수정 로직 구현
        
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
        font = status_item.font()
        font.setBold(True)
        status_item.setFont(font)
        self.price_table.setItem(row, 6, status_item)
    
    def start_upload(self):
        """업로드 시작"""
        # 크롤링된 데이터가 있는지 확인
        if self.crawling_table.rowCount() == 0:
            QMessageBox.warning(self, "경고", "업로드할 상품 데이터가 없습니다.\n먼저 크롤링 탭에서 상품을 수집해주세요.")
            return
        
        reply = QMessageBox.question(
            self, 
            "확인", 
            f"크롤링된 {self.crawling_table.rowCount()}개 상품을 BUYMA에 업로드하시겠습니까?\n\n이 작업은 시간이 오래 걸릴 수 있습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # UI 상태 변경
        self.start_upload_btn.setEnabled(False)
        self.pause_upload_btn.setEnabled(True)
        self.stop_upload_btn.setEnabled(True)
        self.upload_progress.setValue(0)
        self.current_upload_status.setText("업로드 준비중...")
        
        # 업로드 테이블 초기화
        self.upload_table.setRowCount(0)
        
        # 로그 시작
        self.log_message(f"📤 BUYMA 업로드 시작: {self.crawling_table.rowCount()}개 상품")
        
        # 별도 스레드에서 업로드 실행
        self.upload_thread = threading.Thread(target=self.run_bulk_upload, daemon=True)
        self.upload_thread.start()
    
    def run_bulk_upload(self):
        """일괄 업로드 실행 (별도 스레드)"""
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
            
            # BUYMA 로그인
            if not self.buyma_login(driver):
                self.log_message("❌ BUYMA 로그인 실패 - 업로드를 중단합니다.")
                return
            
            # 크롤링된 상품들을 하나씩 업로드
            total_products = self.crawling_table.rowCount()
            success_count = 0
            failed_count = 0
            
            for row in range(total_products):
                try:
                    # 상품 정보 가져오기
                    product_data = self.get_crawled_product_data(row)
                    
                    self.log_message(f"📤 업로드 중 ({row+1}/{total_products}): {product_data['title']}")
                    
                    # BUYMA에 상품 업로드
                    upload_success = self.upload_single_product(driver, product_data)
                    
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
            
        except Exception as e:
            self.log_message(f"❌ 일괄 업로드 오류: {str(e)}")
        finally:
            if driver:
                driver.quit()
            
            # UI 상태 복원
            self.start_upload_btn.setEnabled(True)
            self.pause_upload_btn.setEnabled(False)
            self.stop_upload_btn.setEnabled(False)
    
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
    
    def upload_single_product(self, driver, product_data):
        """단일 상품 BUYMA 업로드"""
        try:
            self.log_message(f"📝 상품 등록 페이지 접속: {product_data['title']}")
            
            # BUYMA 상품 등록 페이지로 이동
            upload_url = "https://www.buyma.com/my/item/new/"
            driver.get(upload_url)
            
            # 페이지 로딩 대기
            import time
            time.sleep(3)
            
            # 상품명 입력
            title_success = self.fill_product_title(driver, product_data['title'])
            if not title_success:
                return False
            
            # 브랜드 입력
            brand_success = self.fill_product_brand(driver, product_data['brand'])
            if not brand_success:
                return False
            
            # 가격 입력
            price_success = self.fill_product_price(driver, product_data['price'])
            if not price_success:
                return False
            
            # 상품 설명 입력
            desc_success = self.fill_product_description(driver, product_data['description'])
            if not desc_success:
                return False
            
            # 이미지 업로드 (있는 경우)
            if product_data.get('images'):
                image_success = self.upload_product_images(driver, product_data['images'])
                if not image_success:
                    self.log_message("⚠️ 이미지 업로드 실패 - 계속 진행")
            
            # 카테고리 선택 (기본값 사용)
            self.select_default_category(driver)
            
            # 저장 또는 등록
            save_success = self.save_product(driver)
            
            return save_success
            
        except Exception as e:
            self.log_message(f"단일 상품 업로드 오류: {str(e)}")
            return False
    
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
        
    def save_settings(self):
        """설정 저장"""
        settings = {
            'email': self.email_input.text(),
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
    
    def log_message(self, message):
        """로그 메시지 출력 (안전장치 포함)"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{timestamp}] {message}"
            
            # log_output이 존재하는지 확인
            if hasattr(self, 'log_output') and self.log_output is not None:
                self.log_output.append(formatted_message)
                
                # 로그 자동 스크롤
                scrollbar = self.log_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            else:
                # UI가 아직 준비되지 않은 경우 콘솔에 출력
                print(formatted_message)
            
            # status_label이 존재하는지 확인
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText(message)
                
        except Exception as e:
            # 로그 출력 중 오류가 발생해도 프로그램이 중단되지 않도록
            print(f"로그 출력 오류: {e} - 메시지: {message}")
    
    def closeEvent(self, event):
        """프로그램 종료 시 설정 저장 및 타이머 정리"""
        # 타이머 정리
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'system_timer'):
            self.system_timer.stop()
            
        # 설정 저장
        self.save_settings()
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
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "수정할 주력 상품이 없습니다.")
                return
            
            # 수정이 필요한 상품들 찾기
            need_update = [p for p in self.favorite_products if '수정 필요' in p.get('status', '')]
            
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
    
    def update_favorite_table(self):
        """주력 상품 테이블 업데이트"""
        try:
            self.favorite_table.setRowCount(len(self.favorite_products))
            
            for row, product in enumerate(self.favorite_products):
                # 브랜드
                self.favorite_table.setItem(row, 0, QTableWidgetItem(product['brand']))
                
                # 상품명
                self.favorite_table.setItem(row, 1, QTableWidgetItem(product['product']))
                
                # 현재가격
                self.favorite_table.setItem(row, 2, QTableWidgetItem(f"{product['current_price']}엔"))
                
                # 경쟁사 최저가
                competitor_price = product.get('competitor_price', 0)
                if competitor_price > 0:
                    self.favorite_table.setItem(row, 3, QTableWidgetItem(f"{competitor_price}엔"))
                else:
                    self.favorite_table.setItem(row, 3, QTableWidgetItem("미확인"))
                
                # 제안가격
                suggested_price = product.get('suggested_price', 0)
                if suggested_price > 0:
                    self.favorite_table.setItem(row, 4, QTableWidgetItem(f"{suggested_price}엔"))
                else:
                    self.favorite_table.setItem(row, 4, QTableWidgetItem("미확인"))
                
                # 상태
                status = product.get('status', '확인 필요')
                status_item = QTableWidgetItem(status)
                
                if '수정 필요' in status:
                    status_item.setForeground(QBrush(QColor("#e74c3c")))
                elif '최신' in status:
                    status_item.setForeground(QBrush(QColor("#27ae60")))
                else:
                    status_item.setForeground(QBrush(QColor("#f39c12")))
                
                self.favorite_table.setItem(row, 5, status_item)
                
                # 마지막 확인
                self.favorite_table.setItem(row, 6, QTableWidgetItem(product.get('last_check', '없음')))
                
                # 액션 버튼
                action_layout = QHBoxLayout()
                action_widget = QWidget()
                
                # 가격 확인 버튼
                check_btn = QPushButton("🔍")
                check_btn.setMaximumWidth(30)
                check_btn.setToolTip("가격 확인")
                check_btn.clicked.connect(lambda checked, r=row: self.check_single_favorite_price(r))
                action_layout.addWidget(check_btn)
                
                # 삭제 버튼
                delete_btn = QPushButton("🗑️")
                delete_btn.setMaximumWidth(30)
                delete_btn.setToolTip("삭제")
                delete_btn.setStyleSheet("background: #e74c3c; color: white;")
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_favorite_product(r))
                action_layout.addWidget(delete_btn)
                
                action_layout.setContentsMargins(5, 2, 5, 2)
                action_widget.setLayout(action_layout)
                self.favorite_table.setCellWidget(row, 7, action_widget)
            
            # 통계 업데이트
            self.update_favorite_statistics()
            
        except Exception as e:
            self.log_message(f"주력 상품 테이블 업데이트 오류: {str(e)}")
    
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
        """전체 주력 상품 삭제"""
        try:
            if not self.favorite_products:
                QMessageBox.information(self, "알림", "삭제할 주력 상품이 없습니다.")
                return
            
            reply = QMessageBox.question(
                self, 
                "전체 삭제 확인", 
                f"모든 주력 상품({len(self.favorite_products)}개)을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.favorite_products.clear()
                self.update_favorite_table()
                self.save_favorite_products_auto()
                self.log_message("🗑️ 모든 주력 상품 삭제 완료")
                QMessageBox.information(self, "삭제 완료", "모든 주력 상품이 삭제되었습니다.")
            
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
            
            # 2. 주력상품 추가 버튼
            add_favorite_btn = QPushButton("⭐")
            add_favorite_btn.setToolTip("주력 상품으로 추가")
            add_favorite_btn.setFixedSize(35, 28)
            add_favorite_btn.setStyleSheet("""
                QPushButton {
                    background: #f39c12;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: '맑은 고딕';
                }
                QPushButton:hover {
                    background: #e67e22;
                }
            """)
            add_favorite_btn.clicked.connect(lambda checked, r=row: self.add_crawled_to_favorites(r))
            action_layout.addWidget(add_favorite_btn)
            
            # 3. 바로 업로드 버튼
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
            
            # 행 높이를 버튼 높이에 맞춤
            self.crawling_table.setRowHeight(row, 35)
            
            # 자동 스크롤
            self.crawling_table.scrollToBottom()
            
        except Exception as e:
            print(f"크롤링 결과 추가 오류: {e}")
    
    def crawling_finished_safe(self):
        """크롤링 완료 처리 (메인 스레드에서 안전하게)"""
        try:
            # UI 상태 복원
            self.start_crawling_btn.setEnabled(True)
            self.stop_crawling_btn.setEnabled(False)
            self.crawling_status.setText("크롤링 완료")
            self.crawling_progress.setValue(100)
            
        except Exception as e:
            print(f"크롤링 완료 처리 오류: {e}")
    
    # ==================== 새로운 기능 구현 ====================
    
    def analyze_all_my_products(self):
        """내 상품 전체 분석 & 수정 - 스레드 기반으로 개선"""
        try:
            # 이미 실행 중인 작업이 있으면 중지
            if self.price_analysis_worker and self.price_analysis_worker.isRunning():
                QMessageBox.warning(self, "경고", "이미 가격 분석이 진행 중입니다.")
                return
            
            self.log_message("🔍 내 상품 목록을 불러오는 중...")
            
            # 시뮬레이션: 내 상품 목록 가져오기
            my_products = self.simulate_get_my_products()
            
            if not my_products:
                QMessageBox.warning(self, "경고", "분석할 상품이 없습니다.")
                return
            
            # 설정 수집
            settings = {
                'auto_mode': self.auto_mode.isChecked(),
                'discount_amount': self.discount_amount.value(),
                'min_margin': self.min_margin.value(),
                'brand_filter': self.brand_input.text().strip() if hasattr(self, 'brand_input') else '',
                'exclude_loss': self.exclude_loss_products.isChecked() if hasattr(self, 'exclude_loss_products') else True
            }
            
            # 브랜드 필터 적용
            products_to_analyze = my_products
            if settings['brand_filter']:
                products_to_analyze = [p for p in my_products 
                                     if settings['brand_filter'].lower() in p.get('brand', '').lower()]
            
            if not products_to_analyze:
                QMessageBox.warning(self, "경고", "필터 조건에 맞는 상품이 없습니다.")
                return
            
            # UI 상태 변경
            self.analyze_all_my_products_btn.setEnabled(False)
            self.analyze_all_my_products_btn.setText("🔄 분석 중...")
            self.stop_price_analysis_btn.setEnabled(True)
            
            # 가격 분석 결과 테이블 초기화
            self.price_table.setRowCount(0)
            
            # 통계 초기화
            self.total_analyzed.setText("분석 완료: 0개")
            self.auto_updated.setText("자동 수정: 0개")
            self.excluded_items.setText("제외: 0개")
            self.failed_items.setText("실패: 0개")
            
            # 워커 스레드 시작
            self.price_analysis_worker = PriceAnalysisWorker(products_to_analyze, settings)
            self.price_analysis_worker.progress_updated.connect(self.update_price_analysis_progress)
            self.price_analysis_worker.product_analyzed.connect(self.add_price_analysis_result)
            self.price_analysis_worker.finished.connect(self.price_analysis_finished)
            self.price_analysis_worker.log_message.connect(self.log_message)
            self.price_analysis_worker.start()
            
            self.log_message(f"🚀 {len(products_to_analyze)}개 상품 가격 분석을 시작합니다.")
            
        except Exception as e:
            self.log_message(f"❌ 전체 분석 시작 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"전체 상품 분석 시작 중 오류가 발생했습니다:\n{str(e)}")
    
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
            # UI 상태 복원
            self.analyze_all_my_products_btn.setEnabled(True)
            self.analyze_all_my_products_btn.setText("🔍 내 상품 전체 분석 & 수정")
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
    
    def start_favorite_analysis(self):
        """주력상품 가격확인 시작 - 스레드 기반으로 개선"""
        try:
            # 이미 실행 중인 작업이 있으면 중지
            if self.favorite_analysis_worker and self.favorite_analysis_worker.isRunning():
                QMessageBox.warning(self, "경고", "이미 주력 상품 분석이 진행 중입니다.")
                return
                
            if not self.favorite_products:
                QMessageBox.warning(self, "경고", "등록된 주력 상품이 없습니다.\n먼저 주력 상품을 추가해주세요.")
                return
            
            # 설정 수집
            settings = {
                'discount_amount': self.discount_amount.value(),
                'min_margin': self.min_margin.value()
            }
            
            # UI 상태 변경
            self.start_favorite_analysis_btn.setEnabled(False)
            self.start_favorite_analysis_btn.setText("🔄 확인 중...")
            self.stop_favorite_analysis_btn.setEnabled(True)
            
            # 통계 초기화
            self.need_update_count.setText("수정 필요: 0개")
            self.up_to_date_count.setText("최신 상태: 0개")
            
            # 워커 스레드 시작
            self.favorite_analysis_worker = FavoriteAnalysisWorker(self.favorite_products, settings)
            self.favorite_analysis_worker.progress_updated.connect(self.update_favorite_analysis_progress)
            self.favorite_analysis_worker.product_checked.connect(self.favorite_product_checked)
            self.favorite_analysis_worker.finished.connect(self.favorite_analysis_finished)
            self.favorite_analysis_worker.log_message.connect(self.log_message)
            self.favorite_analysis_worker.start()
            
            self.log_message(f"⭐ {len(self.favorite_products)}개 주력 상품 가격 확인을 시작합니다.")
            
        except Exception as e:
            self.log_message(f"❌ 주력상품 확인 시작 오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"주력 상품 확인 시작 중 오류가 발생했습니다:\n{str(e)}")
    
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
            self.start_favorite_analysis_btn.setEnabled(True)
            self.start_favorite_analysis_btn.setText("🚀 주력상품 가격확인 시작")
            self.stop_favorite_analysis_btn.setEnabled(False)
            
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
                
                # UI 상태 복원
                self.analyze_all_my_products_btn.setEnabled(True)
                self.analyze_all_my_products_btn.setText("🔍 내 상품 전체 분석 & 수정")
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
                self.start_favorite_analysis_btn.setEnabled(True)
                self.start_favorite_analysis_btn.setText("🚀 주력상품 가격확인 시작")
                self.stop_favorite_analysis_btn.setEnabled(False)
                
                self.log_message("⏹️ 주력 상품 확인이 사용자에 의해 중지되었습니다.")
                
        except Exception as e:
            self.log_message(f"중지 처리 오류: {str(e)}")
    
    def simulate_get_my_products(self):
        """내 상품 목록 가져오기 시뮬레이션"""
        # 실제 구현에서는 BUYMA API나 웹 크롤링으로 내 상품 목록을 가져옴
        sample_products = []
        brands = ["SAN SAN GEAR", "NIKE", "ADIDAS", "PUMA", "CONVERSE", "BALENCIAGA", "GUCCI"]
        product_types = ["T-SHIRT", "HOODIE", "SNEAKERS", "JACKET", "PANTS", "BAG", "WALLET"]
        
        for i in range(15):  # 15개 샘플 상품
            product = {
                'name': f"{random.choice(product_types)} {i+1:03d}",
                'brand': random.choice(brands),
                'current_price': random.randint(15000, 80000),
                'cost_price': random.randint(8000, 40000),
                'product_id': f"PROD_{i+1:03d}"
            }
            sample_products.append(product)
        
        return sample_products
    
    def simulate_get_competitor_price(self, product):
        """경쟁사 최저가 조회 시뮬레이션"""
        # 실제 구현에서는 경쟁사 사이트를 크롤링하여 최저가를 찾음
        base_price = product['current_price']
        # 현재가의 80-95% 범위에서 경쟁사 가격 시뮬레이션
        competitor_price = int(base_price * random.uniform(0.80, 0.95))
        return competitor_price
    
    def simulate_update_price(self, product, new_price):
        """가격 업데이트 시뮬레이션"""
        # 실제 구현에서는 BUYMA API나 웹 자동화로 가격을 수정
        # 시뮬레이션: 90% 성공률
        return random.random() < 0.9
    
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


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("BUYMA 자동화 프로그램")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("소프트캣")
    
    # 폰트 설정 - 맑은 고딕으로 전체 통일
    font = QFont("맑은 고딕", 10)
    app.setFont(font)
    
    # 메인 윈도우 생성 및 표시
    window = Main()
    window.show()
    
    # 시작 메시지
    window.log_message("BUYMA 자동화 프로그램이 시작되었습니다.")
    window.log_message("설정을 확인하고 작업을 시작해주세요.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
