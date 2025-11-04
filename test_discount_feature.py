#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주력상품 할인 기능 테스트
"""

def test_discount_logic():
    """할인 로직 테스트"""
    
    # 테스트 데이터
    favorite_products = [
        {
            'name': '테스트 상품 1',
            'current_price': 10000,
            'product_id': 'TEST001'
        },
        {
            'name': '테스트 상품 2', 
            'current_price': 15000,
            'product_id': 'TEST002'
        }
    ]
    
    # 설정값
    pre_discount_enabled = True
    pre_discount_amount = 500  # 크롤링 전 할인
    post_discount_amount = 100  # 크롤링 후 할인
    
    print("=== 주력상품 할인 기능 테스트 ===")
    print(f"사전 할인 활성화: {pre_discount_enabled}")
    print(f"크롤링 전 할인: {pre_discount_amount}엔")
    print(f"크롤링 후 할인: {post_discount_amount}엔")
    print()
    
    # 1단계: 사전 할인 (체크박스가 활성화된 경우에만)
    if pre_discount_enabled:
        print("🔽 1단계: 사전 할인 실행")
        for product in favorite_products:
            original_price = product['current_price']
            new_price = original_price - pre_discount_amount
            if new_price < 100:
                new_price = 100
            
            product['current_price'] = new_price
            print(f"  - {product['name']}: {original_price:,}엔 → {new_price:,}엔 (-{pre_discount_amount}엔)")
        print()
    
    # 2단계: 가격분석 (경쟁사 최저가 조회)
    print("🔍 2단계: 가격분석 (경쟁사 최저가 조회)")
    for product in favorite_products:
        # 시뮬레이션: 경쟁사 최저가
        competitor_price = product['current_price'] - 200  # 현재가보다 200엔 낮다고 가정
        
        # 제안가 계산 (경쟁사 최저가 - 크롤링 후 할인)
        suggested_price = competitor_price - post_discount_amount
        
        print(f"  - {product['name']}:")
        print(f"    현재가: {product['current_price']:,}엔")
        print(f"    경쟁사 최저가: {competitor_price:,}엔")
        print(f"    제안가: {suggested_price:,}엔 (최저가 - {post_discount_amount}엔)")
        
        # 가격차이 계산
        price_diff = suggested_price - product['current_price']
        if price_diff > 0:
            print(f"    → 💰 가격 수정 필요 (+{price_diff:,}엔)")
        elif price_diff < 0:
            print(f"    → ⚠️ 손실 예상 ({price_diff:,}엔)")
        else:
            print(f"    → ✅ 현재가 적정")
        print()
    
    print("=== 테스트 완료 ===")

if __name__ == "__main__":
    test_discount_logic()
