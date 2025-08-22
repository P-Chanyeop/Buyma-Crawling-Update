feat: 크롤링 설정 적용 및 UI 개선 (v2.0.0 Enhanced Edition)

🚀 주요 기능 추가:
- 크롤링 설정 실제 적용 (이미지 포함, 색상/사이즈 옵션, 중복 제외)
- 스레드 기반 UI 안전성 강화
- 액션 버튼 레이아웃 개선 (가로 배치)

🔧 기술적 개선:
- run_crawling() 함수에 설정 매개변수 추가
- extract_item_data() 함수에 조건부 데이터 수집 로직 구현
- 중복 상품 체크 기능 (is_duplicate_product) 추가
- 시그널-슬롯 기반 UI 업데이트로 스레드 안전성 확보

🎨 UI/UX 개선:
- 크롤링 결과 테이블 액션 버튼 4개 가로 배치
- 행 높이와 버튼 크기 최적화 (35px 행, 35x28px 버튼)
- 맑은 고딕 폰트 전체 적용
- 실시간 로그 시스템 강화

🛠️ 버그 수정:
- 'action_main_layout' is not defined 오류 해결
- list index out of range 오류 안전장치 추가
- 이미지 수, 색상/사이즈 정보 표시 오류 수정
- 초기화 순서 문제로 인한 AttributeError 해결

📊 데이터 처리 개선:
- 크롤링 설정에 따른 선택적 데이터 수집
- 중복 상품 URL 기반 필터링
- 설정된 지연시간 정확한 적용
- 디버깅 로그 상세화

🔄 아키텍처 변경:
- threading.Thread에서 PyQt6 시그널-슬롯 패턴으로 전환
- 메인 스레드 UI 업데이트 안전성 확보
- 워커 스레드와 메인 스레드 간 안전한 통신

📝 문서 업데이트:
- README.md 전면 개편 (v2.0.0 기능 반영)
- 크롤링 설정 사용법 상세 설명 추가
- 업데이트 내역 및 문제 해결 가이드 보강

Breaking Changes:
- run_crawling() 함수 시그니처 변경 (settings 매개변수 추가)
- extract_item_data() 함수 시그니처 변경 (settings 매개변수 추가)

Co-authored-by: Amazon Q <q@amazon.com>
