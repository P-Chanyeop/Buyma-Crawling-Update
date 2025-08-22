#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램 테스트 실행 스크립트
스레드 기반으로 개선된 버전 테스트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_imports():
    """필요한 모듈들이 제대로 import되는지 테스트"""
    print("🔍 모듈 import 테스트 중...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✅ PyQt6.QtWidgets 정상")
    except ImportError as e:
        print(f"❌ PyQt6.QtWidgets 오류: {e}")
        return False
    
    try:
        from PyQt6.QtCore import QThread, pyqtSignal
        print("✅ PyQt6.QtCore 정상")
    except ImportError as e:
        print(f"❌ PyQt6.QtCore 오류: {e}")
        return False
    
    try:
        import selenium
        print("✅ Selenium 정상")
    except ImportError as e:
        print(f"❌ Selenium 오류: {e}")
        return False
    
    try:
        import psutil
        print("✅ psutil 정상")
    except ImportError as e:
        print(f"❌ psutil 오류: {e}")
        return False
    
    try:
        import requests
        print("✅ requests 정상")
    except ImportError as e:
        print(f"❌ requests 오류: {e}")
        return False
    
    return True

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 BUYMA 자동화 프로그램 Enhanced Edition 테스트")
    print("=" * 60)
    
    # 모듈 테스트
    if not test_imports():
        print("\n❌ 필요한 라이브러리가 설치되지 않았습니다.")
        print("다음 명령어로 설치해주세요:")
        print("pip install PyQt6 selenium psutil requests")
        input("\nEnter 키를 눌러 종료하세요...")
        return
    
    print("\n✅ 모든 모듈이 정상적으로 로드되었습니다.")
    print("\n🎯 개선사항:")
    print("   1. 💰 가격관리 - 스레드 기반으로 UI 멈춤 현상 해결")
    print("   2. ⭐ 주력상품 - 백그라운드에서 안전하게 실행")
    print("   3. 🎨 맑은 고딕 폰트 - 전체 UI에 적용")
    print("   4. ⏹️ 중지 기능 - 언제든지 작업 중지 가능")
    print("   5. 🔄 스레드 관리 - 프로그램 종료 시 안전한 정리")
    
    print("\n🚀 프로그램을 시작합니다...")
    
    try:
        from buyma import main as buyma_main
        buyma_main()
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 프로그램이 중단되었습니다.")
        
    except Exception as e:
        print(f"\n❌ 프로그램 실행 오류: {e}")
        print("\n디버그 정보:")
        import traceback
        traceback.print_exc()
        input("\nEnter 키를 눌러 종료하세요...")

if __name__ == "__main__":
    main()
