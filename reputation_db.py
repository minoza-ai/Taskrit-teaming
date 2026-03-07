import json
import os

DB_FILE = "taskrit_db.json"
K_FACTOR = 32 # ELO 점수 변동 폭을 결정하는 상수

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def update_reputation(account_name, is_success, task_difficulty_rating=1500):
    """
    작업 완료 결과에 따라 계정의 ELO 평판 점수를 업데이트합니다.
    - is_success: True(검수 통과/대금 지급), False(실패/페널티)
    - task_difficulty_rating: 해당 작업의 난이도 (기본 1500 기준)
    """
    db = load_db()
    updated = False
    
    for account in db:
        if account["name"] == account_name:
            current_elo = account.get("elo", 1500)
            
            # ELO 승률 기대치 계산
            expected_score = 1 / (1 + 10 ** ((task_difficulty_rating - current_elo) / 400))
            actual_score = 1 if is_success else 0
            
            # 새로운 평판 점수 산출
            new_elo = current_elo + K_FACTOR * (actual_score - expected_score)
            account["elo"] = round(new_elo)
            
            print(f"📈 [{account_name}] 평판 업데이트: {current_elo} -> {account['elo']} (성공 여부: {is_success})")
            updated = True
            break
            
    if updated:
        save_db(db)
    else:
        print(f"계정 '{account_name}'을 찾을 수 없습니다.")

if __name__ == "__main__":
    # 평판 모듈 단독 테스트
    print("--- 평판 업데이트 테스트 ---")
    update_reputation("DevBot-X", is_success=True) # 성공 시 점수 상승
    update_reputation("차병성", is_success=False)  # 실패 시 점수 하락