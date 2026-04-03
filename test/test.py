import sys
import os
import json
import uuid

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.utils.hmac import generateHmac

def main():
    print("==================================================")
    print("TeamingOn API Integration Test (Real Scenario)")
    print("==================================================")
    
    # TestClient의 context manager 구문을 통해 lifespan (DB 연결 등)을 엽니다.
    with TestClient(app) as client:
        print("\n[STEP 1] 사람(지원자) 및 에셋 계정 생성")
        print("실제 LLM 파이프라인을 타므로 시간이 조금 소요됩니다...")
        
        # 1. 벡엔드 특화 시니어
        acc_backend = f"backend-{uuid.uuid4().hex[:8]}"
        res_backend = client.post("/Account", json={
            "accountId": acc_backend,
            "userId": "user-backend",
            "nickname": "Backend Senior",
            "type": "human",
            "abilityText": "이커머스와 핀테크 도메인에서 7년간 백엔드 개발 경험이 있습니다. Spring Boot와 Java를 기반으로 개발하며 Redis 캐시 서버 모델 최적화와 레거시 결제망 통합 등 복잡한 서버 인프라 설계에 강점이 있습니다. 대규모 트래픽 분산 처리에 자신 있습니다.",
            "cost": 80000,
            "skipAi": False,
            "hmac": generateHmac(acc_backend)
        })
        print(f"- Backend Account Creation: {res_backend.status_code}")
        
        # 2. 프론트엔드 특화 주니어
        acc_frontend = f"frontend-{uuid.uuid4().hex[:8]}"
        res_frontend = client.post("/Account", json={
            "accountId": acc_frontend,
            "userId": "user-frontend",
            "nickname": "Frontend Jr",
            "type": "human",
            "abilityText": "주로 React.js와 TailwindCSS를 활용해서 시각적인 프론트엔드 UI를 개발합니다. 인터랙션 및 프론트 사용자 경험 성능 향상에 관심이 많습니다.",
            "cost": 30000,
            "skipAi": False,
            "hmac": generateHmac(acc_frontend)
        })
        print(f"- Frontend Account Creation: {res_frontend.status_code}")
        
        # 3. 데이터베이스 에셋
        acc_asset = f"asset-{uuid.uuid4().hex[:8]}"
        res_asset = client.post("/Account", json={
            "accountId": acc_asset,
            "userId": "user-asset",
            "nickname": "Oracle DB Archive",
            "type": "asset",
            "abilityText": "과거 사용하던 레거시 오라클 결제 데이터베이스 마이그레이션 백업 시스템. 복잡한 튜닝 쿼리가 많아 높은 수준의 데이터베이스 관리 자격 및 서버/백엔드 분석 이해가 극히 요구됨.",
            "cost": 10000,
            "skipAi": False,
            "hmac": generateHmac(acc_asset)
        })
        print(f"- Asset Account Creation: {res_asset.status_code}")


        # -- 2단계: 메타데이터 추출 확인 --
        print("\n[STEP 2] 백엔드(Backend) 지원자 메타데이터 추출 확인")
        # 실제 생성된 Account를 조회해 본다 (DB에서 어빌리티 객체가 잘 떨어지는지)
        res_comp = client.get(f"/Account/{acc_backend}/Components")
        if res_comp.status_code == 200:
            print(json.dumps(res_comp.json(), ensure_ascii=False, indent=2))
        else:
            print("Failed to fetch components.", res_comp.text)


        # -- 3단계: 태스크 발행 및 하이브리드 엔진 매칭 --
        print("\n[STEP 3] 클라이언트 태스크 발행 (매칭 작동 점검)")
        user_client = f"client-{uuid.uuid4().hex[:8]}"
        task_req = "트래픽이 폭주하는 이벤트 기획 시즌입니다. 메인 결제 백엔드를 담당하여 Java와 Spring 시스템을 구축해줄 시니어 개발자를 찾습니다."
        print(f"- Request: {task_req}")

        res_task = client.post("/Task", json={
            "accountId": user_client,
            "request": task_req,
            "requiredDate": 0,
            "requiredElo": 0,
            "requiredCost": 0,
            "requireHuman": False,
            "maxCost": 150000,
            "hmac": generateHmac(user_client)
        })
        
        print(f"- Task Creation Status: {res_task.status_code}")
        if res_task.status_code == 201:
            print("\n>> 하이브리드 매칭 리랭킹 결과 (Score 내림차순 정렬) <<")
            match_results = res_task.json()
            for skill_match in match_results:
                req_ability = skill_match.get("requiredAbility")
                cands = skill_match.get("candidates", [])
                print(f"\n[Required] {req_ability}")
                if not cands:
                     print("  -> No suitable candidates found.")
                for i, c in enumerate(cands, 1):
                    # Show matching attributes
                    print(f"  {i}. {c.get('accountType')} | ID: {c.get('accountId')}")
                    print(f"     Score: {c.get('score', 0):.4f} (Vector: {c.get('similarity', 0):.4f}, Keyword: {c.get('keywordScore', 0):.4f})")
                    print(f"     Matched Text: {c.get('abilityText')}")
        else:
            print("Failed to start task execution:", res_task.text)
            
    print("\nAPI Integration Tests successfully completed.")

if __name__ == "__main__":
    main()
