#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램 GUI
개발자: 소프트캣
버전: 1.0.0
"""

import sys
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QTableWidget, 
                            QTableWidgetItem, QProgressBar, QComboBox, 
                            QSpinBox, QCheckBox, QGroupBox, QFrame, 
                            QScrollArea, QSplitter, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QLinearGradient

class BuymaAutomationGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BUYMA 자동화 프로그램 v1.0.0 - Professional Edition")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # 스타일 설정
        self.setup_styles()
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 헤더 섹션
        self.create_header(main_layout)
        
        # 탭 위젯 생성
        self.create_tab_widget(main_layout)
        
        # 상태바 생성
        self.create_status_bar()
        
        # 설정 로드
        self.load_settings()
        
    def setup_styles(self):
        """전문적인 스타일 설정"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background: white;
                margin-top: 5px;
            }
            
            QTabWidget::tab-bar {
                alignment: center;
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
                margin-top: 10px;
                padding-top: 10px;
                background: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                background: white;
                color: #007bff;
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
                min-height: 20px;
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
            
            QPushButton.success {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
            }
            
            QPushButton.success:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
            
            QPushButton.warning {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffc107, stop:1 #e0a800);
                color: #212529;
            }
            
            QPushButton.warning:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e0a800, stop:1 #d39e00);
            }
            
            QPushButton.danger {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
            }
            
            QPushButton.danger:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c82333, stop:1 #a71e2a);
            }
            
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                background: white;
                selection-background-color: #007bff;
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
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
            
            QLabel {
                color: #495057;
                font-size: 11px;
            }
            
            QLabel.title {
                font-size: 16px;
                font-weight: bold;
                color: #212529;
            }
            
            QLabel.subtitle {
                font-size: 12px;
                color: #6c757d;
            }
            
            QScrollArea {
                border: none;
                background: transparent;
            }
            
            QFrame.separator {
                background: #dee2e6;
                max-height: 1px;
                min-height: 1px;
            }
        """)
    
    def create_header(self, layout):
        """헤더 섹션 생성"""
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 12px;
                margin-bottom: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 15, 30, 15)
        
        # 로고/제목 영역
        title_layout = QVBoxLayout()
        
        title_label = QLabel("BUYMA 자동화 프로그램")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }
        """)
        
        subtitle_label = QLabel("Professional Edition v1.0.0 - 경쟁사 상품 자동 크롤링 & 업로드")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                margin: 0;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        # 상태 정보 영역
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.connection_status = QLabel("● 연결 대기중")
        self.connection_status.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        self.last_update = QLabel(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.last_update.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 10px;
            }
        """)
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.last_update)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(status_layout)
        
        layout.addWidget(header_frame)
    
    def create_tab_widget(self, layout):
        """탭 위젯 생성"""
        self.tab_widget = QTabWidget()
        
        # 탭 생성
        self.create_crawling_tab()
        self.create_price_management_tab()
        self.create_upload_tab()
        self.create_monitoring_tab()
        self.create_settings_tab()
        
        layout.addWidget(self.tab_widget)
    
    def create_crawling_tab(self):
        """크롤링 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 크롤링 설정 그룹
        crawling_group = QGroupBox("🔍 크롤링 설정")
        crawling_layout = QGridLayout(crawling_group)
        crawling_layout.setSpacing(10)
        
        # URL 입력
        crawling_layout.addWidget(QLabel("경쟁사 페이지 URL:"), 0, 0)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.buyma.com/r/-B5718956O1/ (예시)")
        crawling_layout.addWidget(self.url_input, 0, 1, 1, 2)
        
        url_browse_btn = QPushButton("📁 URL 목록")
        url_browse_btn.clicked.connect(self.browse_url_list)
        crawling_layout.addWidget(url_browse_btn, 0, 3)
        
        # 크롤링 옵션
        crawling_layout.addWidget(QLabel("크롤링 개수:"), 1, 0)
        self.crawl_count = QSpinBox()
        self.crawl_count.setRange(1, 1000)
        self.crawl_count.setValue(50)
        crawling_layout.addWidget(self.crawl_count, 1, 1)
        
        crawling_layout.addWidget(QLabel("지연 시간(초):"), 1, 2)
        self.delay_time = QSpinBox()
        self.delay_time.setRange(1, 60)
        self.delay_time.setValue(3)
        crawling_layout.addWidget(self.delay_time, 1, 3)
        
        # 필터 옵션
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
        self.crawling_table.setColumnCount(6)
        self.crawling_table.setHorizontalHeaderLabels([
            "상품명", "브랜드", "가격", "이미지 수", "옵션 수", "URL"
        ])
        self.crawling_table.horizontalHeader().setStretchLastSection(True)
        
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
    
    def create_price_management_tab(self):
        """가격 관리 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 가격 분석 설정
        analysis_group = QGroupBox("💰 가격 분석 설정")
        analysis_layout = QGridLayout(analysis_group)
        
        analysis_layout.addWidget(QLabel("브랜드명:"), 0, 0)
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("예: SAN SAN GEAR")
        analysis_layout.addWidget(self.brand_input, 0, 1)
        
        analysis_layout.addWidget(QLabel("상품명:"), 0, 2)
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("예: EYEWITHNESS T-SHIRT")
        analysis_layout.addWidget(self.product_input, 0, 3)
        
        analysis_layout.addWidget(QLabel("가격 할인(엔):"), 1, 0)
        self.discount_amount = QSpinBox()
        self.discount_amount.setRange(1, 10000)
        self.discount_amount.setValue(100)
        analysis_layout.addWidget(self.discount_amount, 1, 1)
        
        analysis_layout.addWidget(QLabel("최소 마진(엔):"), 1, 2)
        self.min_margin = QSpinBox()
        self.min_margin.setRange(0, 50000)
        self.min_margin.setValue(500)
        analysis_layout.addWidget(self.min_margin, 1, 3)
        
        layout.addWidget(analysis_group)
        
        # 가격 관리 컨트롤
        price_control_layout = QHBoxLayout()
        
        self.analyze_price_btn = QPushButton("🔍 가격 분석")
        self.analyze_price_btn.clicked.connect(self.analyze_prices)
        
        self.update_price_btn = QPushButton("💱 가격 업데이트")
        self.update_price_btn.setProperty("class", "success")
        self.update_price_btn.clicked.connect(self.update_prices)
        
        self.batch_update_btn = QPushButton("📦 일괄 업데이트")
        self.batch_update_btn.setProperty("class", "warning")
        
        price_control_layout.addWidget(self.analyze_price_btn)
        price_control_layout.addWidget(self.update_price_btn)
        price_control_layout.addWidget(self.batch_update_btn)
        price_control_layout.addStretch()
        
        layout.addLayout(price_control_layout)
        
        # 가격 분석 결과
        price_result_group = QGroupBox("📈 가격 분석 결과")
        price_result_layout = QVBoxLayout(price_result_group)
        
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(7)
        self.price_table.setHorizontalHeaderLabels([
            "상품명", "현재가격", "경쟁사 최저가", "제안가격", "예상마진", "상태", "액션"
        ])
        self.price_table.horizontalHeader().setStretchLastSection(True)
        
        price_result_layout.addWidget(self.price_table)
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
        
        upload_layout.addWidget(QLabel("카테고리:"), 0, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "레디스 패션", "맨즈 패션", "키즈&베이비", "코스메&향수", 
            "가방&지갑", "슈즈", "액세서리", "시계", "라이프스타일"
        ])
        upload_layout.addWidget(self.category_combo, 0, 1)
        
        upload_layout.addWidget(QLabel("배송 방법:"), 0, 2)
        self.shipping_combo = QComboBox()
        self.shipping_combo.addItems(["국제배송", "국내배송", "직배송"])
        upload_layout.addWidget(self.shipping_combo, 0, 3)
        
        upload_layout.addWidget(QLabel("업로드 모드:"), 1, 0)
        self.upload_mode = QComboBox()
        self.upload_mode.addItems(["즉시 등록", "초안 저장", "예약 등록"])
        upload_layout.addWidget(self.upload_mode, 1, 1)
        
        upload_layout.addWidget(QLabel("이미지 최대 개수:"), 1, 2)
        self.max_images = QSpinBox()
        self.max_images.setRange(1, 20)
        self.max_images.setValue(10)
        upload_layout.addWidget(self.max_images, 1, 3)
        
        # 자동화 옵션
        self.auto_translate = QCheckBox("자동 번역")
        upload_layout.addWidget(self.auto_translate, 2, 0)
        
        self.auto_categorize = QCheckBox("자동 카테고리 분류")
        upload_layout.addWidget(self.auto_categorize, 2, 1)
        
        self.watermark_images = QCheckBox("워터마크 추가")
        upload_layout.addWidget(self.watermark_images, 2, 2)
        
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
        
        # 전체 진행률
        upload_progress_layout.addWidget(QLabel("전체 진행률:"))
        self.upload_progress = QProgressBar()
        self.upload_progress.setTextVisible(True)
        upload_progress_layout.addWidget(self.upload_progress)
        
        # 현재 작업
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
        
        # 로그 출력
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(200)
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                border: 2px solid #333;
            }
        """)
        monitoring_layout.addWidget(QLabel("시스템 로그:"))
        monitoring_layout.addWidget(self.log_output)
        
        layout.addWidget(monitoring_group)
        
        # 성능 통계
        stats_group = QGroupBox("📊 성능 통계")
        stats_layout = QGridLayout(stats_group)
        
        # 오늘의 통계
        stats_layout.addWidget(QLabel("오늘 크롤링:"), 0, 0)
        self.today_crawled = QLabel("0")
        self.today_crawled.setStyleSheet("font-size: 14px; font-weight: bold; color: #007bff;")
        stats_layout.addWidget(self.today_crawled, 0, 1)
        
        stats_layout.addWidget(QLabel("오늘 업로드:"), 0, 2)
        self.today_uploaded = QLabel("0")
        self.today_uploaded.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
        stats_layout.addWidget(self.today_uploaded, 0, 3)
        
        stats_layout.addWidget(QLabel("성공률:"), 1, 0)
        self.success_rate = QLabel("0%")
        self.success_rate.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffc107;")
        stats_layout.addWidget(self.success_rate, 1, 1)
        
        stats_layout.addWidget(QLabel("평균 처리 시간:"), 1, 2)
        self.avg_process_time = QLabel("0초")
        self.avg_process_time.setStyleSheet("font-size: 14px; font-weight: bold; color: #6f42c1;")
        stats_layout.addWidget(self.avg_process_time, 1, 3)
        
        layout.addWidget(stats_group)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout = QGridLayout(system_group)
        
        system_layout.addWidget(QLabel("CPU 사용률:"), 0, 0)
        self.cpu_usage = QProgressBar()
        self.cpu_usage.setMaximum(100)
        system_layout.addWidget(self.cpu_usage, 0, 1)
        
        system_layout.addWidget(QLabel("메모리 사용률:"), 1, 0)
        self.memory_usage = QProgressBar()
        self.memory_usage.setMaximum(100)
        system_layout.addWidget(self.memory_usage, 1, 1)
        
        system_layout.addWidget(QLabel("네트워크 상태:"), 2, 0)
        self.network_status = QLabel("● 정상")
        self.network_status.setStyleSheet("color: #28a745; font-weight: bold;")
        system_layout.addWidget(self.network_status, 2, 1)
        
        layout.addWidget(system_group)
        
        # 알림 설정
        notification_group = QGroupBox("🔔 알림 설정")
        notification_layout = QVBoxLayout(notification_group)
        
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
        
        self.tab_widget.addTab(tab, "📺 모니터링")
    
    def create_settings_tab(self):
        """설정 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # BUYMA 계정 설정
        account_group = QGroupBox("👤 BUYMA 계정 설정")
        account_layout = QGridLayout(account_group)
        
        account_layout.addWidget(QLabel("이메일:"), 0, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your-email@example.com")
        account_layout.addWidget(self.email_input, 0, 1)
        
        account_layout.addWidget(QLabel("비밀번호:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        account_layout.addWidget(self.password_input, 1, 1)
        
        test_login_btn = QPushButton("🔐 로그인 테스트")
        test_login_btn.clicked.connect(self.test_login)
        account_layout.addWidget(test_login_btn, 1, 2)
        
        layout.addWidget(account_group)
        
        # 브라우저 설정
        browser_group = QGroupBox("🌐 브라우저 설정")
        browser_layout = QGridLayout(browser_group)
        
        browser_layout.addWidget(QLabel("브라우저:"), 0, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome", "Firefox", "Edge"])
        browser_layout.addWidget(self.browser_combo, 0, 1)
        
        browser_layout.addWidget(QLabel("헤드리스 모드:"), 0, 2)
        self.headless_mode = QCheckBox()
        browser_layout.addWidget(self.headless_mode, 0, 3)
        
        browser_layout.addWidget(QLabel("사용자 에이전트:"), 1, 0)
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("기본값 사용")
        browser_layout.addWidget(self.user_agent, 1, 1, 1, 3)
        
        layout.addWidget(browser_group)
        
        # 고급 설정
        advanced_group = QGroupBox("⚙️ 고급 설정")
        advanced_layout = QGridLayout(advanced_group)
        
        advanced_layout.addWidget(QLabel("최대 동시 작업:"), 0, 0)
        self.max_workers = QSpinBox()
        self.max_workers.setRange(1, 10)
        self.max_workers.setValue(3)
        advanced_layout.addWidget(self.max_workers, 0, 1)
        
        advanced_layout.addWidget(QLabel("요청 간격(초):"), 0, 2)
        self.request_delay = QSpinBox()
        self.request_delay.setRange(1, 30)
        self.request_delay.setValue(3)
        advanced_layout.addWidget(self.request_delay, 0, 3)
        
        advanced_layout.addWidget(QLabel("타임아웃(초):"), 1, 0)
        self.timeout_setting = QSpinBox()
        self.timeout_setting.setRange(10, 300)
        self.timeout_setting.setValue(60)
        advanced_layout.addWidget(self.timeout_setting, 1, 1)
        
        advanced_layout.addWidget(QLabel("재시도 횟수:"), 1, 2)
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        advanced_layout.addWidget(self.retry_count, 1, 3)
        
        layout.addWidget(advanced_group)
        
        # 데이터 관리
        data_group = QGroupBox("💾 데이터 관리")
        data_layout = QHBoxLayout(data_group)
        
        backup_btn = QPushButton("💾 설정 백업")
        backup_btn.clicked.connect(self.backup_settings)
        
        restore_btn = QPushButton("📥 설정 복원")
        restore_btn.clicked.connect(self.restore_settings)
        
        clear_data_btn = QPushButton("🗑️ 데이터 초기화")
        clear_data_btn.setProperty("class", "danger")
        clear_data_btn.clicked.connect(self.clear_all_data)
        
        data_layout.addWidget(backup_btn)
        data_layout.addWidget(restore_btn)
        data_layout.addWidget(clear_data_btn)
        data_layout.addStretch()
        
        layout.addWidget(data_group)
        
        # 설정 저장/불러오기
        settings_control_layout = QHBoxLayout()
        
        save_settings_btn = QPushButton("💾 설정 저장")
        save_settings_btn.setProperty("class", "success")
        save_settings_btn.clicked.connect(self.save_settings)
        
        load_settings_btn = QPushButton("📂 설정 불러오기")
        load_settings_btn.clicked.connect(self.load_settings)
        
        reset_settings_btn = QPushButton("🔄 기본값 복원")
        reset_settings_btn.setProperty("class", "warning")
        reset_settings_btn.clicked.connect(self.reset_settings)
        
        settings_control_layout.addWidget(save_settings_btn)
        settings_control_layout.addWidget(load_settings_btn)
        settings_control_layout.addWidget(reset_settings_btn)
        settings_control_layout.addStretch()
        
        layout.addLayout(settings_control_layout)
        layout.addStretch()
        
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
        
        # 상태 메시지
        self.status_label = QLabel("준비 완료")
        status_bar.addWidget(self.status_label)
        
        # 진행률 표시
        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setVisible(False)
        status_bar.addPermanentWidget(self.status_progress)
        
        # 시간 표시
        self.time_label = QLabel()
        self.update_time()
        status_bar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 1초마다 업데이트
    
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(current_time)
    
    # 크롤링 관련 메서드
    def browse_url_list(self):
        """URL 목록 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "URL 목록 파일 선택", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.url_input.setText(file_path)
    
    def start_crawling(self):
        """크롤링 시작"""
        self.log_message("크롤링을 시작합니다...")
        self.start_crawling_btn.setEnabled(False)
        self.stop_crawling_btn.setEnabled(True)
        self.crawling_progress.setValue(0)
        self.crawling_status.setText("크롤링 진행중...")
        
        # TODO: 실제 크롤링 로직 구현
        
    def preview_crawling(self):
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
    
    def clear_crawling_results(self):
        """크롤링 결과 지우기"""
        reply = QMessageBox.question(
            self, "확인", "크롤링 결과를 모두 지우시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.crawling_table.setRowCount(0)
            self.log_message("크롤링 결과를 지웠습니다.")
    
    # 가격 관리 관련 메서드
    def analyze_prices(self):
        """가격 분석"""
        brand = self.brand_input.text().strip()
        product = self.product_input.text().strip()
        
        if not brand or not product:
            QMessageBox.warning(self, "경고", "브랜드명과 상품명을 입력해주세요.")
            return
            
        self.log_message(f"가격 분석 시작: {brand} - {product}")
        # TODO: 가격 분석 로직 구현
        
    def update_prices(self):
        """가격 업데이트"""
        self.log_message("가격 업데이트를 시작합니다...")
        # TODO: 가격 업데이트 로직 구현
    
    # 업로드 관련 메서드
    def start_upload(self):
        """업로드 시작"""
        self.log_message("자동 업로드를 시작합니다...")
        self.start_upload_btn.setEnabled(False)
        self.pause_upload_btn.setEnabled(True)
        self.stop_upload_btn.setEnabled(True)
        self.upload_progress.setValue(0)
        self.current_upload_status.setText("업로드 진행중...")
        
        # TODO: 업로드 로직 구현
        
    def retry_failed_uploads(self):
        """실패한 업로드 재시도"""
        self.log_message("실패한 업로드를 재시도합니다...")
        # TODO: 재시도 로직 구현
        
    def export_upload_results(self):
        """업로드 결과 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "업로드 결과 저장", f"upload_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if file_path:
            self.log_message(f"업로드 결과를 {file_path}에 저장했습니다.")
    
    # 설정 관련 메서드
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
            'headless': self.headless_mode.isChecked(),
            'max_workers': self.max_workers.value(),
            'request_delay': self.request_delay.value(),
            'timeout': self.timeout_setting.value(),
            'retry_count': self.retry_count.value(),
            'crawl_count': self.crawl_count.value(),
            'delay_time': self.delay_time.value(),
            'discount_amount': self.discount_amount.value(),
            'min_margin': self.min_margin.value(),
            'category': self.category_combo.currentText(),
            'shipping': self.shipping_combo.currentText(),
            'upload_mode': self.upload_mode.currentText(),
            'max_images': self.max_images.value(),
            'include_images': self.include_images.isChecked(),
            'include_options': self.include_options.isChecked(),
            'skip_duplicates': self.skip_duplicates.isChecked(),
            'auto_translate': self.auto_translate.isChecked(),
            'auto_categorize': self.auto_categorize.isChecked(),
            'watermark_images': self.watermark_images.isChecked(),
            'enable_notifications': self.enable_notifications.isChecked(),
            'notify_on_complete': self.notify_on_complete.isChecked(),
            'notify_on_error': self.notify_on_error.isChecked()
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
                self.headless_mode.setChecked(settings.get('headless', False))
                self.max_workers.setValue(settings.get('max_workers', 3))
                self.request_delay.setValue(settings.get('request_delay', 3))
                self.timeout_setting.setValue(settings.get('timeout', 60))
                self.retry_count.setValue(settings.get('retry_count', 3))
                self.crawl_count.setValue(settings.get('crawl_count', 50))
                self.delay_time.setValue(settings.get('delay_time', 3))
                self.discount_amount.setValue(settings.get('discount_amount', 100))
                self.min_margin.setValue(settings.get('min_margin', 500))
                self.category_combo.setCurrentText(settings.get('category', '레디스 패션'))
                self.shipping_combo.setCurrentText(settings.get('shipping', '국제배송'))
                self.upload_mode.setCurrentText(settings.get('upload_mode', '즉시 등록'))
                self.max_images.setValue(settings.get('max_images', 10))
                self.include_images.setChecked(settings.get('include_images', True))
                self.include_options.setChecked(settings.get('include_options', True))
                self.skip_duplicates.setChecked(settings.get('skip_duplicates', True))
                self.auto_translate.setChecked(settings.get('auto_translate', False))
                self.auto_categorize.setChecked(settings.get('auto_categorize', False))
                self.watermark_images.setChecked(settings.get('watermark_images', False))
                self.enable_notifications.setChecked(settings.get('enable_notifications', True))
                self.notify_on_complete.setChecked(settings.get('notify_on_complete', True))
                self.notify_on_error.setChecked(settings.get('notify_on_error', True))
                
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
            self.headless_mode.setChecked(False)
            self.max_workers.setValue(3)
            self.request_delay.setValue(3)
            self.timeout_setting.setValue(60)
            self.retry_count.setValue(3)
            self.crawl_count.setValue(50)
            self.delay_time.setValue(3)
            self.discount_amount.setValue(100)
            self.min_margin.setValue(500)
            self.category_combo.setCurrentText('레디스 패션')
            self.shipping_combo.setCurrentText('국제배송')
            self.upload_mode.setCurrentText('즉시 등록')
            self.max_images.setValue(10)
            self.include_images.setChecked(True)
            self.include_options.setChecked(True)
            self.skip_duplicates.setChecked(True)
            self.auto_translate.setChecked(False)
            self.auto_categorize.setChecked(False)
            self.watermark_images.setChecked(False)
            self.enable_notifications.setChecked(True)
            self.notify_on_complete.setChecked(True)
            self.notify_on_error.setChecked(True)
            
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
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        self.log_output.append(formatted_message)
        self.status_label.setText(message)
        
        # 로그 자동 스크롤
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """프로그램 종료 시 설정 저장"""
        self.save_settings()
        event.accept()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("BUYMA 자동화 프로그램")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("소프트캣")
    
    # 폰트 설정
    font = QFont("맑은 고딕", 9)
    app.setFont(font)
    
    # 메인 윈도우 생성 및 표시
    window = BuymaAutomationGUI()
    window.show()
    
    # 시작 메시지
    window.log_message("BUYMA 자동화 프로그램이 시작되었습니다.")
    window.log_message("설정을 확인하고 작업을 시작해주세요.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
