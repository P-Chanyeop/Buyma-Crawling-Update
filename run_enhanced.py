#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램 Enhanced Edition 실행 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from buyma_enhanced import main
    
    if __name__ == "__main__":
        print("🚀 BUYMA 자동화 프로그램 Enhanced Edition을 시작합니다...")
        print("📋 개선사항:")
        print("   1. 💰 가격관리 - 내 상품들을 다 뒤지면서 최저가확인 후 수정")
        print("   2. ⭐ 주력상품 - 선택된 주력 상품들의 가격을 자동으로 확인하고 수정")
        print("   3. 🎨 전체 프로그램 폰트 - 맑은 고딕으로 통일")
        print("=" * 60)
        
        main()
        
except ImportError as e:
    print(f"❌ 모듈 import 오류: {e}")
    print("필요한 라이브러리를 설치해주세요:")
    print("pip install PyQt6 selenium psutil requests")
    
except Exception as e:
    print(f"❌ 프로그램 실행 오류: {e}")
    input("Enter 키를 눌러 종료하세요...")
