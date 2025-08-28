#!/usr/bin/env python3
import re

# buyma.py 파일 읽기
with open('buyma.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 작업 상태 체크 패턴들 제거
patterns_to_remove = [
    # work_stopped 체크 패턴
    r'\s*# 작업 상태 체크.*?\n\s*if self\.work_stopped:.*?\n\s*.*?중지됨.*?\n\s*break\n',
    r'\s*if self\.work_stopped:.*?\n\s*.*?중지됨.*?\n\s*break\n',
    r'\s*if self\.work_stopped:.*?\n\s*.*?중지됨.*?\n\s*return.*?\n',
    r'\s*if self\.work_stopped:.*?\n\s*return.*?\n',
    
    # work_paused 체크 패턴
    r'\s*while self\.work_paused:.*?\n\s*.*?일시정지.*?\n\s*time\.sleep\(1\)\n\s*if self\.work_stopped:.*?\n\s*.*?중지됨.*?\n\s*return.*?\n',
    r'\s*while self\.work_paused:.*?\n\s*.*?일시정지.*?\n\s*time\.sleep\(1\)\n',
    
    # 단독 work_stopped 체크
    r'\s*if self\.work_stopped:\s*\n\s*return \{\'success\': False, \'error\': \'사용자에 의해 중지됨\'\}\s*\n',
    
    # 작업 상태 변수 초기화 (유지)
    # 작업 제어 함수들 (유지)
]

# 패턴 적용
for pattern in patterns_to_remove:
    content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)

# 결과 저장
with open('buyma.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("작업 상태 체크 코드 제거 완료")
