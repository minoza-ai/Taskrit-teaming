"""
임베딩 유사도 역치(Threshold) 결정 및 AI 능력치/작업 분해 테스트 스크립트.
"""

import sys
import os
import asyncio
import numpy as np

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈 임포트 가능하게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import gemini

# ==========================================
# 1. 임베딩 유사도 테스트용 데이터
# ==========================================
PAIRS = [
    # ==========================================
    # 1. 매우 유사 (Expected: 0.90 이상)
    # 사실상 같은 직무이거나, 완벽하게 대체/호환 가능한 기술 스택
    # ==========================================
    (
        "대용량 데이터 처리 및 API 개발을 위한 Python 기반의 백엔드 시스템 구축 역량",
        "파이썬을 활용하여 서버 비즈니스 로직을 설계하고 데이터를 처리하는 백엔드 개발 역량"
    ),
    (
        "React 프레임워크를 활용하여 컴포넌트 기반의 인터랙티브한 웹 프론트엔드 UI를 구현하는 역량",
        "Next.js를 활용하여 서버 사이드 렌더링(SSR) 및 검색 엔진 최적화(SEO)가 적용된 웹 애플리케이션을 개발하는 역량"
    ),
    (
        "PostgreSQL을 활용하여 복잡한 쿼리를 최적화하고 대용량 관계형 데이터베이스를 설계하는 역량",
        "MySQL 기반의 관계형 데이터베이스 모델링 및 트랜잭션의 안정적인 처리와 운영 역량"
    ),

    # ==========================================
    # 2. 중간 정도 연관 (Expected: 0.80 ~ 0.85 내외)
    # 같은 IT 도메인에 속하지만, 역할이 명확히 다르거나 협업 관계인 경우
    # (키워드 매칭 시 발생하던 '프론트/백엔드 동일시 오류'가 해결되는 구간)
    # ==========================================
    (
        "데이터의 무결성을 유지하고 쿼리 성능을 튜닝하는 전문적인 데이터베이스 관리(DBA) 역량",
        "클라우드 및 온프레미스 서버 인프라를 구축하고 운영 체제를 관리하는 시스템 엔지니어링 역량"
    ),
    (
        "타겟 고객층을 분석하고 브랜드를 홍보하여 시장 점유율을 높이는 디지털 마케팅 전략 기획 역량",
        "잠재 고객과 직접 소통하며 제품의 가치를 설득하고 실질적인 매출을 발생시키는 영업 및 세일즈 역량"
    ),
    (
        "비즈니스 데이터를 수집하고 통계 모델을 적용하여 유의미한 인사이트를 도출하는 데이터 분석 역량",
        "사용자 요구사항에 맞춰 최신 프레임워크 기반의 웹 애플리케이션을 기획하고 개발하는 역량"
    ),
    (
        "IT 프로젝트의 일정을 관리하고 팀원 간의 소통을 조율하여 목표를 달성하는 프로젝트 매니징 역량",
        "요구사항 명세서를 바탕으로 실제 동작하는 소프트웨어 코드를 작성하고 테스트하는 개발 역량"
    ),

    # ==========================================
    # 3. 무관 (Expected: 0.75 이하)
    # 도메인 자체가 달라서 의미적 교집합이 전혀 없는 데이터
    # ==========================================
    (
        "대용량 트래픽 처리를 위한 파이썬 기반의 백엔드 API 서버 설계 및 구축 역량",
        "다양한 식재료를 활용하여 고객의 입맛에 맞는 고급 서양식 요리를 조리하는 셰프 역량"
    ),
    (
        "React 프레임워크를 활용하여 상태 관리가 용이한 싱글 페이지 애플리케이션(SPA)을 개발하는 역량",
        "장거리 달리기 시 발의 피로도를 최소화하고 쿠션감을 제공하는 기능성 마라톤화 제작 기술"
    )
]

# ==========================================
# 2. 능력치 분해 테스트용 데이터
# ==========================================
ABILITY_TEXTS = [
    "저는 파이썬 백엔드 개발자입니다. FastAPI를 주로 사용하고, React로 간단한 프론트엔드도 만들 수 있습니다.",
    "10년차 UI/UX 디자이너로 Figma와 Adobe XD를 전문적으로 사용하며 사용자 리서치 경험이 풍부합니다.",
    "Node.js 메인 백엔드 서버와 통신하는 하이브리드 매칭 엔진 마이크로서비스를 구축했습니다. Vector DB에 대한 깊은 이해가 있습니다."
]

# ==========================================
# 3. 요구 능력치 도출 테스트용 데이터
# ==========================================
REQUIREMENT_TEXTS = [
    "AWS 클라우드 인프라 아키텍처 다이어그램 플랜",
    "Figma로 디자인한 SaaS 플랫폼 UI/UX 프로토타입 디자인 에셋",
    "OpenAI API를 활용한 고객 응대 챗봇 파이썬 템플릿 코드"
]

# ==========================================
# 4. 작업 분해 테스트용 데이터
# ==========================================
TASK_TEXTS = [
    "결제 수단 연동이 포함된 이커머스 웹사이트의 백엔드 시스템을 설계하고 구현해주세요.",
    "모바일 앱의 랜딩 페이지 배너 이미지 5장을 제작해줄 분을 찾습니다.",
    "리액트와 스프링부트를 사용해서 사내 직원용 인사관리 시스템을 처음부터 끝까지 혼자 만들어주세요."
]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ==========================================
# 테스트 러너
# ==========================================
async def test_embedding_similarity():
    print("\n" + "="*50)
    print(f"[TEST 1] 단어 쌍 임베딩 유사도 (총 {len(PAIRS)}개)")
    print("="*50)
    
    embeddings = {}
    for i, (w1, w2) in enumerate(PAIRS, 1):
        if w1 not in embeddings:
            embeddings[w1] = await gemini.embedText(w1)
        if w2 not in embeddings:
            embeddings[w2] = await gemini.embedText(w2)
        
        sim = cosine_similarity(embeddings[w1], embeddings[w2])
        print(f"[{i:02d}] '{w1}' <-> '{w2}' : {sim:.4f}")

async def test_ability_decomposition():
    print("\n" + "="*50)
    print("[TEST 2] 능력치 분해 (gemini.decomposeAbilities)")
    print("="*50)
    for i, text in enumerate(ABILITY_TEXTS, 1):
        print(f"\n원본 데이터 [{i}]: {text}")
        skills = await gemini.decomposeAbilities(text)
        import json
        print("-> 분해 결과:")
        for s in skills:
            print(f"   - {json.dumps(s, ensure_ascii=False)}")
        await asyncio.sleep(5)

async def test_requirement_decomposition():
    print("\n" + "="*50)
    print("[TEST 3] 요구 능력치 도출 (gemini.decomposeRequirements)")
    print("="*50)
    for i, text in enumerate(REQUIREMENT_TEXTS, 1):
        print(f"\n에셋 원본 데이터 [{i}]: {text}")
        skills = await gemini.decomposeRequirements(text)
        import json
        print("-> 도출 결과:")
        for s in skills:
            print(f"   - {json.dumps(s, ensure_ascii=False)}")
        await asyncio.sleep(5)

async def test_task_decomposition():
    print("\n" + "="*50)
    print("[TEST 4] 작업 분해 (gemini.decomposeTaskRequest)")
    print("="*50)
    for i, text in enumerate(TASK_TEXTS, 1):
        print(f"\n태스크 요청 [{i}]: {text}")
        skills = await gemini.decomposeTaskRequest(text)
        import json
        print("-> 필요 능력치 도출 결과:")
        for s in skills:
            print(f"   - {json.dumps(s, ensure_ascii=False)}")
        await asyncio.sleep(5)

async def main():
    await test_embedding_similarity()
    await test_ability_decomposition()
    await test_requirement_decomposition()
    await test_task_decomposition()
    print("\n모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
