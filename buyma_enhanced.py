#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램 - 개선된 버전
개발자: 소프트캣
버전: 1.1.0

개선사항:
1. 가격관리 - 내 상품들을 다 뒤지면서 최저가확인 후 수정
2. 주력상품 - 내 상품들중에 주력 상품을 선택 후 지정-> 시작 버튼 클릭시 주력상품 다 뒤지면서 최저가확인 후 수정
3. 전체 프로그램 폰트 - 맑은 고딕 전부다 수정
"""

import sys
import os
import json
import psutil
import requests
import threading
import random
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                            QTableWidgetItem, QProgressBar, QComboBox, 
                            QSpinBox, QCheckBox, QGroupBox, QFrame, 
                            QFileDialog, QMessageBox, QScrollArea, 
                            QRadioButton, QButtonGroup, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont, QColor, QBrush

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class PriceManagementWorker(QThread):
    """가격 관리 작업을 위한 워커 스레드"""
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
        """가격 관리 실행"""
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
                    cost_price = product.get('cost_price', 0)
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
                    time.sleep(random.uniform(2, 4))
                    
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
        # 실제 구현에서는 웹 크롤링으로 경쟁사 가격 조회
        base_price = product.get('current_price', 15000)
        # 시뮬레이션: 현재가의 80-95% 범위에서 랜덤
        return int(base_price * random.uniform(0.8, 0.95))
    
    def update_product_price(self, product, new_price):
        """상품 가격 업데이트 (시뮬레이션)"""
        try:
            # 실제 구현에서는 BUYMA API 또는 웹 자동화로 가격 수정
            time.sleep(random.uniform(1, 3))  # 업데이트 시뮬레이션
            return random.choice([True, True, True, False])  # 75% 성공률
        except:
            return False
    
    def stop(self):
        """작업 중지"""
        self.is_running = False

class FavoriteProductsWorker(QThread):
    """주력 상품 관리 작업을 위한 워커 스레드"""
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
                    cost_price = product.get('cost_price', 0)
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
                    time.sleep(random.uniform(3, 5))
                    
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
            time.sleep(random.uniform(2, 4))
            return random.choice([True, True, True, False])  # 75% 성공률
        except:
            return False
    
    def stop(self):
        """작업 중지"""
        self.is_running = False

class EnhancedBuymaAutomation(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 데이터 초기화
        self.favorite_products = []
        self.favorites_file = "favorite_products.json"
        self.price_analysis_results = []
        self.favorite_check_results = []
        
        # 워커 스레드
        self.price_worker = None
        self.favorite_worker = None
        
        self.init_ui()
        self.load_settings()
        self.load_favorite_products()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BUYMA 자동화 프로그램 v1.1.0 - Enhanced Edition")
        self.setGeometry(100, 100, 1500, 1000)
        self.setMinimumSize(1300, 900)
        
        # 전체 폰트를 맑은 고딕으로 설정
        font = QFont("맑은 고딕", 10)
        self.setFont(font)
        
        # 스타일 설정
        self.setup_styles()
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 헤더
        self.create_header(main_layout)
        
        # 탭 위젯
        self.create_tabs(main_layout)
        
        # 상태바
        self.create_status_bar()
        
    def setup_styles(self):
        """스타일 설정"""
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
                font-family: '맑은 고딕';
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #dee2e6;
                padding: 12px 24px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 12px;
                color: #495057;
                min-width: 120px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: '맑은 고딕';
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border-bottom: 2px solid #007bff;
            }
            
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
            }
            
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #343a40;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background: white;
                font-family: '맑은 고딕';
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                background: white;
                color: #007bff;
                font-size: 14px;
                font-family: '맑은 고딕';
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 12px;
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
                color: #ffffff;
            }
            
            QLineEdit, QSpinBox {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                background: white;
                selection-background-color: #007bff;
                font-family: '맑은 고딕';
            }
            
            QLineEdit:focus, QSpinBox:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QTableWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background: white;
                gridline-color: #e9ecef;
                font-size: 11px;
                font-family: '맑은 고딕';
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
                font-family: '맑은 고딕';
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
                font-size: 11px;
                color: #495057;
                font-family: '맑은 고딕';
            }
            
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                background: #f8f9fa;
                font-family: '맑은 고딕';
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #20c997);
                border-radius: 4px;
            }
            
            QCheckBox, QRadioButton {
                font-size: 12px;
                color: #495057;
                spacing: 8px;
                font-family: '맑은 고딕';
            }
            
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
                border: 2px solid #dee2e6;
                background: white;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                border: 2px solid #007bff;
                background: #007bff;
                border-radius: 3px;
            }
            
            QLabel {
                color: #495057;
                font-size: 12px;
                background: transparent;
                border: none;
                font-family: '맑은 고딕';
            }
            
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background: white;
                font-size: 11px;
                color: #495057;
                font-family: '맑은 고딕', 'Consolas', monospace;
            }
        """)
    
    def create_header(self, layout):
        """헤더 생성"""
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 10px;
                margin-bottom: 10px;
            }
            QLabel {
                color: white; 
                font-size: 24px; 
                font-weight: bold;
                background: transparent;
                border: none;
                font-family: '맑은 고딕';
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QLabel("🚀 BUYMA 자동화 프로그램 - Enhanced Edition")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        version_label = QLabel("v1.1.0")
        version_label.setStyleSheet("font-size: 16px; color: rgba(255, 255, 255, 0.8); font-family: '맑은 고딕';")
        header_layout.addWidget(version_label)
        
        layout.addWidget(header_frame)
    
    def create_tabs(self, layout):
        """탭 생성"""
        self.tab_widget = QTabWidget()
        
        # 1. 가격 관리 탭 (개선됨)
        self.create_enhanced_price_tab()
        
        # 2. 주력 상품 관리 탭 (개선됨)
        self.create_enhanced_favorite_tab()
        
        # 3. 대시보드 탭
        self.create_dashboard_tab()
        
        # 4. 설정 탭
        self.create_settings_tab()
        
        layout.addWidget(self.tab_widget)
    
    def create_enhanced_price_tab(self):
        """개선된 가격 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 제목
        title_label = QLabel("💰 전체 상품 가격 관리")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; font-family: '맑은 고딕';")
        layout.addWidget(title_label)
        
        # 설정 영역
        settings_group = QGroupBox("⚙️ 가격 관리 설정")
        settings_layout = QGridLayout(settings_group)
        
        # 모드 선택
        settings_layout.addWidget(QLabel("관리 모드:"), 0, 0)
        self.price_mode_combo = QComboBox()
        self.price_mode_combo.addItems(["🤖 자동 모드 (조건 맞으면 즉시 수정)", "👤 수동 모드 (검토 후 수정)"])
        self.price_mode_combo.setStyleSheet("font-family: '맑은 고딕'; font-size: 12px;")
        settings_layout.addWidget(self.price_mode_combo, 0, 1, 1, 2)
        
        # 할인 금액
        settings_layout.addWidget(QLabel("할인 금액(엔):"), 1, 0)
        self.price_discount_amount = QSpinBox()
        self.price_discount_amount.setRange(1, 10000)
        self.price_discount_amount.setValue(100)
        self.price_discount_amount.setSuffix("엔")
        settings_layout.addWidget(self.price_discount_amount, 1, 1)
        
        # 최소 마진
        settings_layout.addWidget(QLabel("최소 마진(엔):"), 1, 2)
        self.price_min_margin = QSpinBox()
        self.price_min_margin.setRange(0, 50000)
        self.price_min_margin.setValue(500)
        self.price_min_margin.setSuffix("엔")
        settings_layout.addWidget(self.price_min_margin, 1, 3)
        
        # 필터 옵션
        settings_layout.addWidget(QLabel("브랜드 필터:"), 2, 0)
        self.price_brand_filter = QLineEdit()
        self.price_brand_filter.setPlaceholderText("특정 브랜드만 분석 (비워두면 전체)")
        settings_layout.addWidget(self.price_brand_filter, 2, 1, 1, 3)
        
        # 옵션 체크박스
        options_layout = QHBoxLayout()
        self.exclude_loss_check = QCheckBox("손실 예상 상품 자동 제외")
        self.exclude_loss_check.setChecked(True)
        options_layout.addWidget(self.exclude_loss_check)
        
        self.backup_before_update = QCheckBox("수정 전 백업 생성")
        self.backup_before_update.setChecked(True)
        options_layout.addWidget(self.backup_before_update)
        
        options_layout.addStretch()
        settings_layout.addLayout(options_layout, 3, 0, 1, 4)
        
        layout.addWidget(settings_group)
        
        # 컨트롤 버튼
        control_layout = QHBoxLayout()
        
        self.load_products_btn = QPushButton("📥 내 상품 불러오기")
        self.load_products_btn.setMinimumHeight(45)
        self.load_products_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #138496, stop:1 #0f6674);
            }
        """)
        self.load_products_btn.clicked.connect(self.load_my_products)
        
        self.start_price_analysis_btn = QPushButton("🔍 가격 분석 시작")
        self.start_price_analysis_btn.setMinimumHeight(45)
        self.start_price_analysis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.start_price_analysis_btn.clicked.connect(self.start_price_analysis)
        self.start_price_analysis_btn.setEnabled(False)
        
        self.stop_price_analysis_btn = QPushButton("⏹️ 중지")
        self.stop_price_analysis_btn.setMinimumHeight(45)
        self.stop_price_analysis_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 14px;
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
        
        control_layout.addWidget(self.load_products_btn)
        control_layout.addWidget(self.start_price_analysis_btn)
        control_layout.addWidget(self.stop_price_analysis_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 진행 상황
        progress_group = QGroupBox("📊 진행 상황")
        progress_layout = QVBoxLayout(progress_group)
        
        self.price_progress_bar = QProgressBar()
        self.price_progress_bar.setStyleSheet("font-family: '맑은 고딕';")
        progress_layout.addWidget(self.price_progress_bar)
        
        # 통계
        stats_layout = QHBoxLayout()
        
        self.price_total_label = QLabel("총 상품: 0개")
        self.price_total_label.setStyleSheet("font-weight: bold; color: #007bff; padding: 5px; font-family: '맑은 고딕';")
        
        self.price_analyzed_label = QLabel("분석 완료: 0개")
        self.price_analyzed_label.setStyleSheet("font-weight: bold; color: #28a745; padding: 5px; font-family: '맑은 고딕';")
        
        self.price_updated_label = QLabel("수정 완료: 0개")
        self.price_updated_label.setStyleSheet("font-weight: bold; color: #17a2b8; padding: 5px; font-family: '맑은 고딕';")
        
        self.price_excluded_label = QLabel("제외: 0개")
        self.price_excluded_label.setStyleSheet("font-weight: bold; color: #ffc107; padding: 5px; font-family: '맑은 고딕';")
        
        self.price_failed_label = QLabel("실패: 0개")
        self.price_failed_label.setStyleSheet("font-weight: bold; color: #dc3545; padding: 5px; font-family: '맑은 고딕';")
        
        stats_layout.addWidget(self.price_total_label)
        stats_layout.addWidget(self.price_analyzed_label)
        stats_layout.addWidget(self.price_updated_label)
        stats_layout.addWidget(self.price_excluded_label)
        stats_layout.addWidget(self.price_failed_label)
        stats_layout.addStretch()
        
        progress_layout.addLayout(stats_layout)
        layout.addWidget(progress_group)
        
        # 결과 테이블
        result_group = QGroupBox("📈 분석 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.price_result_table = QTableWidget()
        self.price_result_table.setColumnCount(8)
        self.price_result_table.setHorizontalHeaderLabels([
            "상품명", "브랜드", "현재가격", "경쟁사 최저가", "제안가격", "예상마진", "상태", "액션"
        ])
        self.price_result_table.horizontalHeader().setStretchLastSection(True)
        self.price_result_table.setStyleSheet("font-family: '맑은 고딕';")
        
        result_layout.addWidget(self.price_result_table)
        layout.addWidget(result_group)
        
        # 로그
        log_group = QGroupBox("📝 작업 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.price_log_text = QTextEdit()
        self.price_log_text.setMaximumHeight(150)
        self.price_log_text.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #00ff00;
                font-family: '맑은 고딕', 'Consolas', monospace;
                font-size: 11px;
                border: 2px solid #333;
                border-radius: 6px;
            }
        """)
        log_layout.addWidget(self.price_log_text)
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(tab, "💰 가격 관리")
    
    def create_enhanced_favorite_tab(self):
        """개선된 주력 상품 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 제목
        title_label = QLabel("⭐ 주력 상품 관리")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; font-family: '맑은 고딕';")
        layout.addWidget(title_label)
        
        # 상단 컨트롤 영역
        control_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 왼쪽: 주력 상품 추가
        add_group = QGroupBox("🔖 주력 상품 추가")
        add_layout = QVBoxLayout(add_group)
        
        # 상품 정보 입력
        input_layout = QGridLayout()
        
        input_layout.addWidget(QLabel("브랜드:"), 0, 0)
        self.fav_brand_input = QLineEdit()
        self.fav_brand_input.setPlaceholderText("예: SAN SAN GEAR")
        input_layout.addWidget(self.fav_brand_input, 0, 1)
        
        input_layout.addWidget(QLabel("상품명:"), 1, 0)
        self.fav_product_input = QLineEdit()
        self.fav_product_input.setPlaceholderText("예: EYEWITHNESS T-SHIRT")
        input_layout.addWidget(self.fav_product_input, 1, 1)
        
        input_layout.addWidget(QLabel("현재가격:"), 2, 0)
        self.fav_price_input = QSpinBox()
        self.fav_price_input.setRange(100, 1000000)
        self.fav_price_input.setValue(15000)
        self.fav_price_input.setSuffix("엔")
        input_layout.addWidget(self.fav_price_input, 2, 1)
        
        input_layout.addWidget(QLabel("원가:"), 3, 0)
        self.fav_cost_input = QSpinBox()
        self.fav_cost_input.setRange(0, 500000)
        self.fav_cost_input.setValue(8000)
        self.fav_cost_input.setSuffix("엔")
        input_layout.addWidget(self.fav_cost_input, 3, 1)
        
        add_layout.addLayout(input_layout)
        
        # 추가 버튼
        add_btn_layout = QHBoxLayout()
        
        self.add_favorite_btn = QPushButton("⭐ 주력 상품 추가")
        self.add_favorite_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f39c12, stop:1 #e67e22);
                font-size: 13px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e67e22, stop:1 #d35400);
            }
        """)
        self.add_favorite_btn.clicked.connect(self.add_favorite_product)
        
        self.clear_inputs_btn = QPushButton("🗑️ 입력 초기화")
        self.clear_inputs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #5a6268);
                font-size: 13px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6268, stop:1 #495057);
            }
        """)
        self.clear_inputs_btn.clicked.connect(self.clear_favorite_inputs)
        
        add_btn_layout.addWidget(self.add_favorite_btn)
        add_btn_layout.addWidget(self.clear_inputs_btn)
        add_layout.addLayout(add_btn_layout)
        
        control_splitter.addWidget(add_group)
        
        # 오른쪽: 관리 기능
        manage_group = QGroupBox("🛠️ 관리 기능")
        manage_layout = QVBoxLayout(manage_group)
        
        # 설정
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("할인 금액(엔):"), 0, 0)
        self.fav_discount_amount = QSpinBox()
        self.fav_discount_amount.setRange(1, 10000)
        self.fav_discount_amount.setValue(100)
        self.fav_discount_amount.setSuffix("엔")
        settings_layout.addWidget(self.fav_discount_amount, 0, 1)
        
        settings_layout.addWidget(QLabel("최소 마진(엔):"), 1, 0)
        self.fav_min_margin = QSpinBox()
        self.fav_min_margin.setRange(0, 50000)
        self.fav_min_margin.setValue(500)
        self.fav_min_margin.setSuffix("엔")
        settings_layout.addWidget(self.fav_min_margin, 1, 1)
        
        manage_layout.addLayout(settings_layout)
        
        # 관리 버튼들
        manage_btn_layout = QVBoxLayout()
        
        self.check_favorites_btn = QPushButton("🚀 주력상품 가격 확인 시작")
        self.check_favorites_btn.setMinimumHeight(40)
        self.check_favorites_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.check_favorites_btn.clicked.connect(self.start_favorite_check)
        
        self.stop_favorites_btn = QPushButton("⏹️ 중지")
        self.stop_favorites_btn.setMinimumHeight(40)
        self.stop_favorites_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """)
        self.stop_favorites_btn.clicked.connect(self.stop_favorite_check)
        self.stop_favorites_btn.setEnabled(False)
        
        self.export_favorites_btn = QPushButton("📤 주력상품 내보내기")
        self.export_favorites_btn.setStyleSheet("""
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
        self.export_favorites_btn.clicked.connect(self.export_favorite_products)
        
        manage_btn_layout.addWidget(self.check_favorites_btn)
        manage_btn_layout.addWidget(self.stop_favorites_btn)
        manage_btn_layout.addWidget(self.export_favorites_btn)
        manage_layout.addLayout(manage_btn_layout)
        
        control_splitter.addWidget(manage_group)
        control_splitter.setSizes([300, 300])
        
        layout.addWidget(control_splitter)
        
        # 진행 상황
        progress_group = QGroupBox("📊 진행 상황")
        progress_layout = QVBoxLayout(progress_group)
        
        self.favorite_progress_bar = QProgressBar()
        self.favorite_progress_bar.setStyleSheet("font-family: '맑은 고딕';")
        progress_layout.addWidget(self.favorite_progress_bar)
        
        # 통계
        stats_layout = QHBoxLayout()
        
        self.fav_total_label = QLabel("총 주력상품: 0개")
        self.fav_total_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px; font-family: '맑은 고딕';")
        
        self.fav_checked_label = QLabel("확인 완료: 0개")
        self.fav_checked_label.setStyleSheet("font-weight: bold; color: #28a745; padding: 5px; font-family: '맑은 고딕';")
        
        self.fav_updated_label = QLabel("가격 수정: 0개")
        self.fav_updated_label.setStyleSheet("font-weight: bold; color: #007bff; padding: 5px; font-family: '맑은 고딕';")
        
        self.fav_failed_label = QLabel("실패: 0개")
        self.fav_failed_label.setStyleSheet("font-weight: bold; color: #dc3545; padding: 5px; font-family: '맑은 고딕';")
        
        stats_layout.addWidget(self.fav_total_label)
        stats_layout.addWidget(self.fav_checked_label)
        stats_layout.addWidget(self.fav_updated_label)
        stats_layout.addWidget(self.fav_failed_label)
        stats_layout.addStretch()
        
        progress_layout.addLayout(stats_layout)
        layout.addWidget(progress_group)
        
        # 주력 상품 목록
        favorites_group = QGroupBox("⭐ 주력 상품 목록")
        favorites_layout = QVBoxLayout(favorites_group)
        
        # 목록 관리 버튼
        list_control_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ 전체 선택")
        self.select_all_btn.clicked.connect(self.select_all_favorites)
        
        self.deselect_all_btn = QPushButton("❌ 전체 해제")
        self.deselect_all_btn.clicked.connect(self.deselect_all_favorites)
        
        self.delete_selected_btn = QPushButton("🗑️ 선택 삭제")
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
        """)
        self.delete_selected_btn.clicked.connect(self.delete_selected_favorites)
        
        list_control_layout.addWidget(self.select_all_btn)
        list_control_layout.addWidget(self.deselect_all_btn)
        list_control_layout.addWidget(self.delete_selected_btn)
        list_control_layout.addStretch()
        
        favorites_layout.addLayout(list_control_layout)
        
        # 주력 상품 테이블
        self.favorites_table = QTableWidget()
        self.favorites_table.setColumnCount(6)
        self.favorites_table.setHorizontalHeaderLabels([
            "선택", "브랜드", "상품명", "현재가격", "원가", "등록일"
        ])
        self.favorites_table.horizontalHeader().setStretchLastSection(True)
        self.favorites_table.setStyleSheet("font-family: '맑은 고딕';")
        
        favorites_layout.addWidget(self.favorites_table)
        layout.addWidget(favorites_group)
        
        # 확인 결과
        result_group = QGroupBox("📈 확인 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.favorite_result_table = QTableWidget()
        self.favorite_result_table.setColumnCount(7)
        self.favorite_result_table.setHorizontalHeaderLabels([
            "상품명", "현재가격", "경쟁사 최저가", "제안가격", "예상마진", "상태", "수정여부"
        ])
        self.favorite_result_table.horizontalHeader().setStretchLastSection(True)
        self.favorite_result_table.setStyleSheet("font-family: '맑은 고딕';")
        
        result_layout.addWidget(self.favorite_result_table)
        layout.addWidget(result_group)
        
        # 로그
        log_group = QGroupBox("📝 작업 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.favorite_log_text = QTextEdit()
        self.favorite_log_text.setMaximumHeight(120)
        self.favorite_log_text.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #00ff00;
                font-family: '맑은 고딕', 'Consolas', monospace;
                font-size: 11px;
                border: 2px solid #333;
                border-radius: 6px;
            }
        """)
        log_layout.addWidget(self.favorite_log_text)
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(tab, "⭐ 주력 상품")
    
    def create_dashboard_tab(self):
        """대시보드 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 제목
        title_label = QLabel("📊 대시보드")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; font-family: '맑은 고딕';")
        layout.addWidget(title_label)
        
        # 통계 카드들
        stats_layout = QGridLayout()
        
        # 오늘 통계
        today_group = QGroupBox("📅 오늘 통계")
        today_layout = QGridLayout(today_group)
        
        today_layout.addWidget(QLabel("가격 분석:"), 0, 0)
        self.today_analyzed = QLabel("0개")
        self.today_analyzed.setStyleSheet("font-size: 18px; font-weight: bold; color: #007bff; font-family: '맑은 고딕';")
        today_layout.addWidget(self.today_analyzed, 0, 1)
        
        today_layout.addWidget(QLabel("가격 수정:"), 1, 0)
        self.today_updated = QLabel("0개")
        self.today_updated.setStyleSheet("font-size: 18px; font-weight: bold; color: #28a745; font-family: '맑은 고딕';")
        today_layout.addWidget(self.today_updated, 1, 1)
        
        stats_layout.addWidget(today_group, 0, 0)
        
        # 주력 상품 통계
        favorite_stats_group = QGroupBox("⭐ 주력 상품")
        favorite_stats_layout = QGridLayout(favorite_stats_group)
        
        favorite_stats_layout.addWidget(QLabel("등록된 상품:"), 0, 0)
        self.total_favorites_dash = QLabel("0개")
        self.total_favorites_dash.setStyleSheet("font-size: 18px; font-weight: bold; color: #f39c12; font-family: '맑은 고딕';")
        favorite_stats_layout.addWidget(self.total_favorites_dash, 0, 1)
        
        favorite_stats_layout.addWidget(QLabel("마지막 확인:"), 1, 0)
        self.last_check_dash = QLabel("없음")
        self.last_check_dash.setStyleSheet("font-size: 14px; color: #6c757d; font-family: '맑은 고딕';")
        favorite_stats_layout.addWidget(self.last_check_dash, 1, 1)
        
        stats_layout.addWidget(favorite_stats_group, 0, 1)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout = QGridLayout(system_group)
        
        system_layout.addWidget(QLabel("CPU 사용률:"), 0, 0)
        self.cpu_usage = QLabel("0%")
        self.cpu_usage.setStyleSheet("font-size: 16px; font-weight: bold; color: #17a2b8; font-family: '맑은 고딕';")
        system_layout.addWidget(self.cpu_usage, 0, 1)
        
        system_layout.addWidget(QLabel("메모리 사용률:"), 1, 0)
        self.memory_usage = QLabel("0%")
        self.memory_usage.setStyleSheet("font-size: 16px; font-weight: bold; color: #6f42c1; font-family: '맑은 고딕';")
        system_layout.addWidget(self.memory_usage, 1, 1)
        
        stats_layout.addWidget(system_group, 0, 2)
        
        layout.addLayout(stats_layout)
        
        # 최근 활동
        activity_group = QGroupBox("📋 최근 활동")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_log = QTextEdit()
        self.activity_log.setMaximumHeight(200)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-family: '맑은 고딕';
                font-size: 11px;
                color: #495057;
            }
        """)
        activity_layout.addWidget(self.activity_log)
        
        layout.addWidget(activity_group)
        
        # 빠른 액션
        quick_actions_group = QGroupBox("⚡ 빠른 액션")
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        
        self.quick_price_check_btn = QPushButton("🔍 빠른 가격 확인")
        self.quick_price_check_btn.setMinimumHeight(50)
        self.quick_price_check_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
            }
        """)
        
        self.quick_favorite_check_btn = QPushButton("⭐ 주력상품 확인")
        self.quick_favorite_check_btn.setMinimumHeight(50)
        self.quick_favorite_check_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        
        self.open_settings_btn = QPushButton("⚙️ 설정")
        self.open_settings_btn.setMinimumHeight(50)
        self.open_settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #5a6268);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6268, stop:1 #495057);
            }
        """)
        self.open_settings_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(3))
        
        quick_actions_layout.addWidget(self.quick_price_check_btn)
        quick_actions_layout.addWidget(self.quick_favorite_check_btn)
        quick_actions_layout.addWidget(self.open_settings_btn)
        
        layout.addWidget(quick_actions_group)
        
        self.tab_widget.addTab(tab, "📊 대시보드")
    
    def create_settings_tab(self):
        """설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 제목
        title_label = QLabel("⚙️ 설정")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; font-family: '맑은 고딕';")
        layout.addWidget(title_label)
        
        # BUYMA 계정 설정
        account_group = QGroupBox("👤 BUYMA 계정 설정")
        account_layout = QGridLayout(account_group)
        
        account_layout.addWidget(QLabel("이메일:"), 0, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("BUYMA 로그인 이메일")
        account_layout.addWidget(self.email_input, 0, 1)
        
        account_layout.addWidget(QLabel("비밀번호:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("BUYMA 로그인 비밀번호")
        account_layout.addWidget(self.password_input, 1, 1)
        
        layout.addWidget(account_group)
        
        # 기본 설정
        default_group = QGroupBox("🔧 기본 설정")
        default_layout = QGridLayout(default_group)
        
        default_layout.addWidget(QLabel("기본 할인 금액(엔):"), 0, 0)
        self.default_discount = QSpinBox()
        self.default_discount.setRange(1, 10000)
        self.default_discount.setValue(100)
        self.default_discount.setSuffix("엔")
        default_layout.addWidget(self.default_discount, 0, 1)
        
        default_layout.addWidget(QLabel("기본 최소 마진(엔):"), 0, 2)
        self.default_min_margin = QSpinBox()
        self.default_min_margin.setRange(0, 50000)
        self.default_min_margin.setValue(500)
        self.default_min_margin.setSuffix("엔")
        default_layout.addWidget(self.default_min_margin, 0, 3)
        
        default_layout.addWidget(QLabel("작업 딜레이(초):"), 1, 0)
        self.work_delay = QSpinBox()
        self.work_delay.setRange(1, 30)
        self.work_delay.setValue(3)
        self.work_delay.setSuffix("초")
        default_layout.addWidget(self.work_delay, 1, 1)
        
        default_layout.addWidget(QLabel("재시도 횟수:"), 1, 2)
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        self.retry_count.setSuffix("회")
        default_layout.addWidget(self.retry_count, 1, 3)
        
        layout.addWidget(default_group)
        
        # 알림 설정
        notification_group = QGroupBox("🔔 알림 설정")
        notification_layout = QVBoxLayout(notification_group)
        
        self.enable_sound = QCheckBox("작업 완료 시 소리 알림")
        self.enable_sound.setChecked(True)
        
        self.enable_popup = QCheckBox("중요 이벤트 팝업 알림")
        self.enable_popup.setChecked(True)
        
        self.auto_backup = QCheckBox("자동 백업 생성")
        self.auto_backup.setChecked(True)
        
        notification_layout.addWidget(self.enable_sound)
        notification_layout.addWidget(self.enable_popup)
        notification_layout.addWidget(self.auto_backup)
        
        layout.addWidget(notification_group)
        
        # 고급 설정
        advanced_group = QGroupBox("🔬 고급 설정")
        advanced_layout = QGridLayout(advanced_group)
        
        advanced_layout.addWidget(QLabel("브라우저 헤드리스 모드:"), 0, 0)
        self.headless_mode = QCheckBox("백그라운드에서 실행")
        advanced_layout.addWidget(self.headless_mode, 0, 1)
        
        advanced_layout.addWidget(QLabel("로그 레벨:"), 1, 0)
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText("INFO")
        advanced_layout.addWidget(self.log_level, 1, 1)
        
        layout.addWidget(advanced_group)
        
        # 설정 버튼
        settings_btn_layout = QHBoxLayout()
        
        self.save_settings_btn = QPushButton("💾 설정 저장")
        self.save_settings_btn.setMinimumHeight(40)
        self.save_settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
        """)
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        self.reset_settings_btn = QPushButton("🔄 기본값 복원")
        self.reset_settings_btn.setMinimumHeight(40)
        self.reset_settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffc107, stop:1 #e0a800);
                font-size: 14px;
                font-weight: bold;
                font-family: '맑은 고딕';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e0a800, stop:1 #d39e00);
            }
        """)
        self.reset_settings_btn.clicked.connect(self.reset_settings)
        
        settings_btn_layout.addWidget(self.save_settings_btn)
        settings_btn_layout.addWidget(self.reset_settings_btn)
        settings_btn_layout.addStretch()
        
        layout.addLayout(settings_btn_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "⚙️ 설정")
    
    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #495057;
                font-size: 11px;
                font-family: '맑은 고딕';
            }
        """)
        
        # 상태 정보
        self.status_label = QLabel("준비됨")
        self.status_bar.addWidget(self.status_label)
        
        # 시간 표시
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)
        
        # 타이머로 시간 업데이트
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        
        # 시스템 모니터링 타이머
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.update_system_stats)
        self.system_timer.start(5000)  # 5초마다 업데이트
    
    # ==================== 메인 기능 구현 ====================
    
    def load_my_products(self):
        """내 상품 불러오기 (시뮬레이션)"""
        try:
            self.log_to_price("📥 내 상품 목록을 불러오는 중...")
            
            # 시뮬레이션 데이터 생성
            sample_products = []
            brands = ["SAN SAN GEAR", "NIKE", "ADIDAS", "PUMA", "CONVERSE"]
            product_types = ["T-SHIRT", "HOODIE", "SNEAKERS", "JACKET", "PANTS"]
            
            for i in range(20):  # 20개 샘플 상품
                product = {
                    'name': f"{random.choice(product_types)} {i+1:03d}",
                    'brand': random.choice(brands),
                    'current_price': random.randint(10000, 50000),
                    'cost_price': random.randint(5000, 25000),
                    'id': f"PROD_{i+1:03d}"
                }
                sample_products.append(product)
            
            self.my_products = sample_products
            self.price_total_label.setText(f"총 상품: {len(self.my_products)}개")
            self.start_price_analysis_btn.setEnabled(True)
            
            self.log_to_price(f"✅ {len(self.my_products)}개 상품을 불러왔습니다.")
            self.update_activity_log(f"내 상품 {len(self.my_products)}개 불러오기 완료")
            
        except Exception as e:
            self.log_to_price(f"❌ 상품 불러오기 실패: {str(e)}")
    
    def start_price_analysis(self):
        """가격 분석 시작"""
        if not hasattr(self, 'my_products') or not self.my_products:
            QMessageBox.warning(self, "경고", "먼저 상품을 불러와주세요.")
            return
        
        try:
            # 설정 수집
            settings = {
                'auto_mode': self.price_mode_combo.currentIndex() == 0,
                'discount_amount': self.price_discount_amount.value(),
                'min_margin': self.price_min_margin.value(),
                'brand_filter': self.price_brand_filter.text().strip(),
                'exclude_loss': self.exclude_loss_check.isChecked()
            }
            
            # 브랜드 필터 적용
            products_to_analyze = self.my_products
            if settings['brand_filter']:
                products_to_analyze = [p for p in self.my_products 
                                     if settings['brand_filter'].lower() in p['brand'].lower()]
            
            if not products_to_analyze:
                QMessageBox.warning(self, "경고", "분석할 상품이 없습니다.")
                return
            
            # UI 상태 변경
            self.start_price_analysis_btn.setEnabled(False)
            self.stop_price_analysis_btn.setEnabled(True)
            self.price_progress_bar.setValue(0)
            self.price_result_table.setRowCount(0)
            
            # 워커 스레드 시작
            self.price_worker = PriceManagementWorker(products_to_analyze, settings)
            self.price_worker.progress_updated.connect(self.update_price_progress)
            self.price_worker.product_analyzed.connect(self.add_price_result)
            self.price_worker.finished.connect(self.price_analysis_finished)
            self.price_worker.log_message.connect(self.log_to_price)
            self.price_worker.start()
            
            self.log_to_price(f"🚀 {len(products_to_analyze)}개 상품 가격 분석을 시작합니다.")
            self.update_activity_log(f"가격 분석 시작 - {len(products_to_analyze)}개 상품")
            
        except Exception as e:
            self.log_to_price(f"❌ 가격 분석 시작 실패: {str(e)}")
    
    def stop_price_analysis(self):
        """가격 분석 중지"""
        if self.price_worker and self.price_worker.isRunning():
            self.price_worker.stop()
            self.price_worker.wait()
            
        self.start_price_analysis_btn.setEnabled(True)
        self.stop_price_analysis_btn.setEnabled(False)
        self.log_to_price("⏹️ 가격 분석이 중지되었습니다.")
    
    def update_price_progress(self, current, total):
        """가격 분석 진행률 업데이트"""
        progress = int((current / total) * 100)
        self.price_progress_bar.setValue(progress)
        self.price_analyzed_label.setText(f"분석 완료: {current}개")
    
    def add_price_result(self, result):
        """가격 분석 결과 추가"""
        row = self.price_result_table.rowCount()
        self.price_result_table.insertRow(row)
        
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
                if "수정 불가" in item_text:
                    item.setForeground(QBrush(QColor("#dc3545")))
                elif "수정 가능" in item_text:
                    item.setForeground(QBrush(QColor("#28a745")))
                else:
                    item.setForeground(QBrush(QColor("#6c757d")))
                    
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            elif col == 5:  # 마진 컬럼
                if result['margin'] < 0:
                    item.setForeground(QBrush(QColor("#dc3545")))
                else:
                    item.setForeground(QBrush(QColor("#28a745")))
                    
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            self.price_result_table.setItem(row, col, item)
    
    def price_analysis_finished(self, stats):
        """가격 분석 완료"""
        self.start_price_analysis_btn.setEnabled(True)
        self.stop_price_analysis_btn.setEnabled(False)
        
        # 통계 업데이트
        self.price_analyzed_label.setText(f"분석 완료: {stats['analyzed']}개")
        self.price_updated_label.setText(f"수정 완료: {stats['updated']}개")
        self.price_excluded_label.setText(f"제외: {stats['excluded']}개")
        self.price_failed_label.setText(f"실패: {stats['failed']}개")
        
        # 대시보드 통계 업데이트
        current_analyzed = int(self.today_analyzed.text().replace("개", ""))
        current_updated = int(self.today_updated.text().replace("개", ""))
        
        self.today_analyzed.setText(f"{current_analyzed + stats['analyzed']}개")
        self.today_updated.setText(f"{current_updated + stats['updated']}개")
        
        self.update_activity_log(f"가격 분석 완료 - 분석:{stats['analyzed']}, 수정:{stats['updated']}")
        
        # 완료 알림
        if hasattr(self, 'enable_popup') and self.enable_popup.isChecked():
            QMessageBox.information(self, "완료", 
                f"가격 분석이 완료되었습니다.\n\n"
                f"• 분석 완료: {stats['analyzed']}개\n"
                f"• 수정 완료: {stats['updated']}개\n"
                f"• 제외: {stats['excluded']}개\n"
                f"• 실패: {stats['failed']}개")
    
    def add_favorite_product(self):
        """주력 상품 추가"""
        brand = self.fav_brand_input.text().strip()
        product_name = self.fav_product_input.text().strip()
        price = self.fav_price_input.value()
        cost = self.fav_cost_input.value()
        
        if not brand or not product_name:
            QMessageBox.warning(self, "경고", "브랜드와 상품명을 입력해주세요.")
            return
        
        # 중복 확인
        for product in self.favorite_products:
            if product['brand'] == brand and product['name'] == product_name:
                QMessageBox.warning(self, "경고", "이미 등록된 상품입니다.")
                return
        
        # 새 상품 추가
        new_product = {
            'brand': brand,
            'name': product_name,
            'current_price': price,
            'cost_price': cost,
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        self.favorite_products.append(new_product)
        self.save_favorite_products()
        self.update_favorites_table()
        self.clear_favorite_inputs()
        
        self.log_to_favorite(f"⭐ 주력 상품 추가: {brand} - {product_name}")
        self.update_activity_log(f"주력 상품 추가: {brand} - {product_name}")
    
    def clear_favorite_inputs(self):
        """주력 상품 입력 필드 초기화"""
        self.fav_brand_input.clear()
        self.fav_product_input.clear()
        self.fav_price_input.setValue(15000)
        self.fav_cost_input.setValue(8000)
    
    def update_favorites_table(self):
        """주력 상품 테이블 업데이트"""
        self.favorites_table.setRowCount(len(self.favorite_products))
        
        for row, product in enumerate(self.favorite_products):
            # 체크박스
            checkbox = QCheckBox()
            self.favorites_table.setCellWidget(row, 0, checkbox)
            
            # 데이터
            items = [
                "",  # 체크박스 컬럼
                product['brand'],
                product['name'],
                f"{product['current_price']:,}엔",
                f"{product['cost_price']:,}엔",
                product['added_date']
            ]
            
            for col in range(1, len(items)):
                item = QTableWidgetItem(items[col])
                self.favorites_table.setItem(row, col, item)
        
        # 통계 업데이트
        self.fav_total_label.setText(f"총 주력상품: {len(self.favorite_products)}개")
        self.total_favorites_dash.setText(f"{len(self.favorite_products)}개")
    
    def start_favorite_check(self):
        """주력 상품 가격 확인 시작"""
        if not self.favorite_products:
            QMessageBox.warning(self, "경고", "등록된 주력 상품이 없습니다.")
            return
        
        try:
            # 설정 수집
            settings = {
                'discount_amount': self.fav_discount_amount.value(),
                'min_margin': self.fav_min_margin.value()
            }
            
            # UI 상태 변경
            self.check_favorites_btn.setEnabled(False)
            self.stop_favorites_btn.setEnabled(True)
            self.favorite_progress_bar.setValue(0)
            self.favorite_result_table.setRowCount(0)
            
            # 워커 스레드 시작
            self.favorite_worker = FavoriteProductsWorker(self.favorite_products, settings)
            self.favorite_worker.progress_updated.connect(self.update_favorite_progress)
            self.favorite_worker.product_checked.connect(self.add_favorite_result)
            self.favorite_worker.finished.connect(self.favorite_check_finished)
            self.favorite_worker.log_message.connect(self.log_to_favorite)
            self.favorite_worker.start()
            
            self.log_to_favorite(f"⭐ {len(self.favorite_products)}개 주력 상품 가격 확인을 시작합니다.")
            self.update_activity_log(f"주력 상품 가격 확인 시작 - {len(self.favorite_products)}개")
            
        except Exception as e:
            self.log_to_favorite(f"❌ 주력 상품 확인 시작 실패: {str(e)}")
    
    def stop_favorite_check(self):
        """주력 상품 확인 중지"""
        if self.favorite_worker and self.favorite_worker.isRunning():
            self.favorite_worker.stop()
            self.favorite_worker.wait()
            
        self.check_favorites_btn.setEnabled(True)
        self.stop_favorites_btn.setEnabled(False)
        self.log_to_favorite("⏹️ 주력 상품 확인이 중지되었습니다.")
    
    def update_favorite_progress(self, current, total):
        """주력 상품 확인 진행률 업데이트"""
        progress = int((current / total) * 100)
        self.favorite_progress_bar.setValue(progress)
        self.fav_checked_label.setText(f"확인 완료: {current}개")
    
    def add_favorite_result(self, result):
        """주력 상품 확인 결과 추가"""
        row = self.favorite_result_table.rowCount()
        self.favorite_result_table.insertRow(row)
        
        # 데이터 설정
        items = [
            result['name'],
            f"{result['current_price']:,}엔",
            f"{result['competitor_price']:,}엔",
            f"{result['suggested_price']:,}엔",
            f"{result['margin']:,}엔",
            result['status'],
            "✅" if result['updated'] else "❌"
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            
            # 상태에 따른 색상 설정
            if col == 5:  # 상태 컬럼
                if "완료" in item_text:
                    item.setForeground(QBrush(QColor("#28a745")))
                elif "실패" in item_text or "불가" in item_text:
                    item.setForeground(QBrush(QColor("#dc3545")))
                else:
                    item.setForeground(QBrush(QColor("#6c757d")))
                    
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            elif col == 4:  # 마진 컬럼
                if result['margin'] < 0:
                    item.setForeground(QBrush(QColor("#dc3545")))
                else:
                    item.setForeground(QBrush(QColor("#28a745")))
                    
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            self.favorite_result_table.setItem(row, col, item)
    
    def favorite_check_finished(self, stats):
        """주력 상품 확인 완료"""
        self.check_favorites_btn.setEnabled(True)
        self.stop_favorites_btn.setEnabled(False)
        
        # 통계 업데이트
        self.fav_checked_label.setText(f"확인 완료: {stats['checked']}개")
        self.fav_updated_label.setText(f"가격 수정: {stats['updated']}개")
        self.fav_failed_label.setText(f"실패: {stats['failed']}개")
        
        # 마지막 확인 시간 업데이트
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.last_check_dash.setText(current_time)
        
        self.update_activity_log(f"주력 상품 확인 완료 - 확인:{stats['checked']}, 수정:{stats['updated']}")
        
        # 완료 알림
        if hasattr(self, 'enable_popup') and self.enable_popup.isChecked():
            QMessageBox.information(self, "완료", 
                f"주력 상품 확인이 완료되었습니다.\n\n"
                f"• 확인 완료: {stats['checked']}개\n"
                f"• 가격 수정: {stats['updated']}개\n"
                f"• 실패: {stats['failed']}개")
    
    def select_all_favorites(self):
        """모든 주력 상품 선택"""
        for row in range(self.favorites_table.rowCount()):
            checkbox = self.favorites_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all_favorites(self):
        """모든 주력 상품 선택 해제"""
        for row in range(self.favorites_table.rowCount()):
            checkbox = self.favorites_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def delete_selected_favorites(self):
        """선택된 주력 상품 삭제"""
        selected_rows = []
        for row in range(self.favorites_table.rowCount()):
            checkbox = self.favorites_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            QMessageBox.warning(self, "경고", "삭제할 상품을 선택해주세요.")
            return
        
        reply = QMessageBox.question(self, "확인", 
            f"{len(selected_rows)}개 상품을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 역순으로 삭제 (인덱스 변경 방지)
            for row in reversed(selected_rows):
                del self.favorite_products[row]
            
            self.save_favorite_products()
            self.update_favorites_table()
            self.log_to_favorite(f"🗑️ {len(selected_rows)}개 주력 상품을 삭제했습니다.")
    
    def export_favorite_products(self):
        """주력 상품 내보내기"""
        if not self.favorite_products:
            QMessageBox.warning(self, "경고", "내보낼 주력 상품이 없습니다.")
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "주력 상품 내보내기", 
                f"favorite_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json)")
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.favorite_products, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "완료", f"주력 상품을 {filename}에 저장했습니다.")
                self.log_to_favorite(f"📤 주력 상품을 {filename}에 내보냈습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 실패: {str(e)}")
    
    # ==================== 유틸리티 함수 ====================
    
    def log_to_price(self, message):
        """가격 관리 로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.price_log_text.append(f"[{timestamp}] {message}")
    
    def log_to_favorite(self, message):
        """주력 상품 로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.favorite_log_text.append(f"[{timestamp}] {message}")
    
    def update_activity_log(self, message):
        """활동 로그 업데이트"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")
        
        # 로그가 너무 길어지면 자동으로 정리
        if self.activity_log.document().blockCount() > 100:
            cursor = self.activity_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 20)
            cursor.removeSelectedText()
    
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)
    
    def update_system_stats(self):
        """시스템 통계 업데이트"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent()
            self.cpu_usage.setText(f"{cpu_percent:.1f}%")
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            self.memory_usage.setText(f"{memory.percent:.1f}%")
            
            # 색상 변경 (사용률에 따라)
            if cpu_percent > 80:
                self.cpu_usage.setStyleSheet("color: #dc3545; font-weight: bold; font-family: '맑은 고딕';")
            elif cpu_percent > 60:
                self.cpu_usage.setStyleSheet("color: #ffc107; font-weight: bold; font-family: '맑은 고딕';")
            else:
                self.cpu_usage.setStyleSheet("color: #28a745; font-weight: bold; font-family: '맑은 고딕';")
            
            if memory.percent > 80:
                self.memory_usage.setStyleSheet("color: #dc3545; font-weight: bold; font-family: '맑은 고딕';")
            elif memory.percent > 60:
                self.memory_usage.setStyleSheet("color: #ffc107; font-weight: bold; font-family: '맑은 고딕';")
            else:
                self.memory_usage.setStyleSheet("color: #28a745; font-weight: bold; font-family: '맑은 고딕';")
                
        except Exception as e:
            print(f"시스템 통계 업데이트 오류: {e}")
    
    def load_settings(self):
        """설정 로드"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 설정 적용
                if hasattr(self, 'email_input'):
                    self.email_input.setText(settings.get('email', ''))
                if hasattr(self, 'default_discount'):
                    self.default_discount.setValue(settings.get('default_discount', 100))
                if hasattr(self, 'default_min_margin'):
                    self.default_min_margin.setValue(settings.get('default_min_margin', 500))
                
        except Exception as e:
            print(f"설정 로드 오류: {e}")
    
    def save_settings(self):
        """설정 저장"""
        try:
            settings = {
                'email': self.email_input.text(),
                'default_discount': self.default_discount.value(),
                'default_min_margin': self.default_min_margin.value(),
                'work_delay': self.work_delay.value(),
                'retry_count': self.retry_count.value(),
                'enable_sound': self.enable_sound.isChecked(),
                'enable_popup': self.enable_popup.isChecked(),
                'auto_backup': self.auto_backup.isChecked(),
                'headless_mode': self.headless_mode.isChecked(),
                'log_level': self.log_level.currentText()
            }
            
            with open("settings.json", 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "완료", "설정이 저장되었습니다.")
            self.update_activity_log("설정 저장 완료")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {str(e)}")
    
    def reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(self, "확인", 
            "모든 설정을 기본값으로 복원하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.email_input.clear()
            self.password_input.clear()
            self.default_discount.setValue(100)
            self.default_min_margin.setValue(500)
            self.work_delay.setValue(3)
            self.retry_count.setValue(3)
            self.enable_sound.setChecked(True)
            self.enable_popup.setChecked(True)
            self.auto_backup.setChecked(True)
            self.headless_mode.setChecked(False)
            self.log_level.setCurrentText("INFO")
            
            QMessageBox.information(self, "완료", "설정이 기본값으로 복원되었습니다.")
    
    def load_favorite_products(self):
        """주력 상품 로드"""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self.favorite_products = json.load(f)
                self.update_favorites_table()
        except Exception as e:
            print(f"주력 상품 로드 오류: {e}")
            self.favorite_products = []
    
    def save_favorite_products(self):
        """주력 상품 저장"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorite_products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"주력 상품 저장 오류: {e}")
    
    def closeEvent(self, event):
        """프로그램 종료 시 처리"""
        # 실행 중인 워커 스레드 정리
        if self.price_worker and self.price_worker.isRunning():
            self.price_worker.stop()
            self.price_worker.wait()
        
        if self.favorite_worker and self.favorite_worker.isRunning():
            self.favorite_worker.stop()
            self.favorite_worker.wait()
        
        # 설정 자동 저장
        if hasattr(self, 'auto_backup') and self.auto_backup.isChecked():
            self.save_settings()
        
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 전체 애플리케이션 폰트를 맑은 고딕으로 설정
    font = QFont("맑은 고딕", 10)
    app.setFont(font)
    
    # 메인 윈도우 생성 및 표시
    window = EnhancedBuymaAutomation()
    window.show()
    
    # 시작 메시지
    window.update_activity_log("BUYMA 자동화 프로그램 Enhanced Edition 시작")
    window.log_to_price("💡 가격 관리 기능이 준비되었습니다.")
    window.log_to_favorite("💡 주력 상품 관리 기능이 준비되었습니다.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
