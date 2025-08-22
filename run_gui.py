#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUYMA 자동화 프로그램 실행 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from buyma_automation_gui import main
    
    if __name__ == "__main__":
        print("BUYMA 자동화 프로그램을 시작합니다...")
        print("GUI 창이 열리지 않으면 작업 표시줄을 확인해주세요.")
        main()
        
except ImportError as e:
    print(f"필요한 모듈을 찾을 수 없습니다: {e}")
    print("다음 명령어로 필요한 패키지를 설치해주세요:")
    print("pip install -r requirements.txt")
    input("엔터 키를 눌러 종료...")
    
except Exception as e:
    print(f"프로그램 실행 중 오류가 발생했습니다: {e}")
    input("엔터 키를 눌러 종료...")
