import sys
import os
import uuid
import json

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.utils.hmac import generateHmac

DUMMY_SIZE = 50
DUMMY_PATH = "./dummy.json"

def generate_nickname(item):
    """항목 속성을 이용하여 닉네임 자동 생성"""
    return f"{item.get('job_category', 'User')} {item.get('experience', '')} ({item.get('tech_trend', '')})"

def insert_dummy_data(client):
    json_path = os.path.join(os.path.dirname(__file__), DUMMY_PATH)
    if not os.path.exists(json_path):
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DUMMY_PATH)
        
    if not os.path.exists(json_path):
        print(f"Error: Could not find dummy.json at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    target_data = data[:DUMMY_SIZE]
    print(f"\nAPI를 경유하여 더미 데이터 {len(target_data)}개를 DB에 주입합니다...")
    print("백그라운드에서 AI 분해가 수행되므로 계정당 수 초씩 소요될 수 있습니다.")
    
    for i, item in enumerate(target_data, 1):
        account_id = f"dummy-{uuid.uuid4().hex[:8]}"
        
        payload = {
            "accountId": account_id,
            "userId": f"usr-dummy-{i}",
            "nickname": generate_nickname(item),
            "type": item.get("type", "human"),
            "abilityText": item.get("abilityText", ""),
            "cost": item.get("cost", 30000),
            "skipAi": False,
            "hmac": generateHmac(account_id)
        }
        
        print(f"[{i}/{len(target_data)}] 계정 생성 중: {payload['nickname']}...")
        res = client.post("/Account", json=payload)
        
        if res.status_code == 201:
            print(f"  -> 성공적으로 생성되었습니다. (ID: {account_id})")
        else:
            print(f"  -> 계정 생성 실패! (Status: {res.status_code})")
            print(f"     {res.text}")

def match_test(client, request_text: str):
    """테스트 작업을 넣고 매칭 결과를 출력하는 커스텀 테스트 함수"""
    print("\n==================================================")
    print("Match Engine Test Request")
    print("==================================================")
    print(f"- Task Request: {request_text}")
    
    user_client = f"client-{uuid.uuid4().hex[:8]}"
    res_task = client.post("/Task", json={
        "accountId": user_client,
        "request": request_text,
        "requiredDate": 0,
        "requiredElo": 0,
        "requiredCost": 0,
        "requireHuman": False,
        "maxCost": 0,  # 0이면 limit 무시
        "hmac": generateHmac(user_client)
    })
    
    if res_task.status_code == 201:
        print("\n>> 하이브리드 엔진 매칭 결과 <<")
        match_results = res_task.json()
        for skill_match in match_results:
            req_ability = skill_match.get("requiredAbility")
            cands = skill_match.get("candidates", [])
            print(f"\n[Required] {req_ability} (Total Cands: {len(cands)})")
            if not cands:
                 print("  -> 적합한 후보자를 찾을 수 없습니다.")
                 
            # 최대 5명의 후보만 출력하여 결과 파악
            for i, c in enumerate(cands[:5], 1):
                print(f"  {i}. {c.get('accountType')} | ID: {c.get('accountId')}")
                print(f"     Final Score: {c.get('score', 0):.4f} (Vector: {c.get('similarity', 0):.4f}, Keyword: {c.get('keywordScore', 0):.4f})")
                print(f"     Matched Text: {c.get('abilityText')}")
    else:
        print("Failed to execute match test:", res_task.text)

def main():
    print("==================================================")
    print("Dummy Data Injection & Match Test Script")
    print("==================================================")
    
    with TestClient(app) as client:
        # 1. 처음 150개의 더미 계정 주입 수행
        insert_dummy_data(client)
        
        # 2. 매칭 엔진 동작 테스트 (원하는 태스크를 문자열로 주입 가능)
        while True:
          task = input("매칭할 작업을 입력하세요:")
          if len(task) < 2:
            break
          match_test(client, task)

if __name__ == "__main__":
    main()
