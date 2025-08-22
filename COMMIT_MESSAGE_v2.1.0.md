fix: 크롤링 안정성 대폭 강화 및 QUOTA_EXCEEDED 오류 해결 (v2.1.0)

🛡️ 주요 안정성 개선:
- QUOTA_EXCEEDED 오류 완전 해결 (Google API 할당량 초과 방지)
- 브라우저 갑작스런 종료 문제 해결
- 크롤링 중 프로그램 팅김 현상 방지
- 메모리 누수 및 리소스 관리 개선

🔧 Chrome 브라우저 최적화:
- Google API 관련 기능 비활성화 (--disable-background-networking)
- 확장 프로그램 및 기본 앱 비활성화 (--disable-extensions, --disable-default-apps)
- 백그라운드 프로세스 차단 (--disable-background-timer-throttling)
- 메모리 압박 방지 옵션 추가 (--memory-pressure-off)
- 로그 및 디버깅 기능 비활성화 (--silent, --log-level=3)

🔄 재시도 및 복구 로직:
- 브라우저 초기화 실패 시 자동 재시도 (최대 3회)
- 크롤링 중 브라우저 상태 실시간 체크
- 심각한 오류 자동 감지 및 안전한 중단
- 네트워크 연결 끊김 감지 및 대응

💾 메모리 및 리소스 관리:
- 가비지 컬렉션 강제 실행 (gc.collect())
- 모든 브라우저 탭 안전한 종료
- 드라이버 리소스 완전 정리
- 메모리 사용량 최적화 옵션 추가

⚠️ 오류 감지 및 대응 시스템:
- QUOTA_EXCEEDED 오류 패턴 감지
- "chrome not reachable" 오류 감지
- 심각한 오류 발생 시 크롤링 자동 중단
- 상세한 오류 로깅 및 디버깅 정보 제공

🎯 사용자 경험 개선:
- 브라우저 초기화 진행 상황 실시간 표시
- 재시도 횟수 및 상태 로그 출력
- 안정성 가이드 및 권장 설정 제공
- 오류 발생 시 명확한 해결 방안 제시

📊 성능 최적화:
- Chrome 프로세스 경량화
- 불필요한 백그라운드 작업 제거
- 네트워크 요청 최적화
- CPU 및 메모리 사용량 감소

🔍 디버깅 및 모니터링:
- 브라우저 상태 체크 로직 추가
- 크롤링 진행 상황 상세 추적
- 오류 발생 지점 정확한 식별
- 시스템 리소스 사용량 모니터링

📝 문서 업데이트:
- README.md에 v2.1.0 업데이트 내역 추가
- 크롤링 안정성 가이드 섹션 추가
- 문제 해결 가이드 확장 (QUOTA_EXCEEDED, 브라우저 종료 등)
- 권장 설정 및 사용법 업데이트

Breaking Changes: 없음

Fixes:
- 크롤링 중 프로그램 갑작스런 종료 (#issue-001)
- QUOTA_EXCEEDED 오류로 인한 크롤링 실패 (#issue-002)
- 메모리 누수로 인한 성능 저하 (#issue-003)
- 브라우저 초기화 실패 시 복구 불가 (#issue-004)

Co-authored-by: Amazon Q <q@amazon.com>
