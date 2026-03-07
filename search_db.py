import json
import numpy as np
from sentence_transformers import SentenceTransformer
import re

DB_FILE = "taskrit_db.json"

print("임베딩 모델을 로드하는 중입니다...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def load_db():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("DB 파일이 없습니다. ability_db.py를 먼저 실행해 데이터를 넣어주세요.")
        return []

def cosine_similarity(v1, v2):
    """두 벡터 간의 코사인 유사도를 계산합니다 (-1.0 ~ 1.0). 1.0에 가까울수록 일치함."""
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def decompose_task(complex_task_text):
    """
    [API 불필요 버전] 정규 표현식을 활용하여 문장을 하위 태스크로 쪼갭니다.
    성능 무관, 빠른 파이프라인 테스트를 위한 임시(Mock) 함수입니다.
    """
    print("🧠 [로컬 처리] 외부 API 없이 텍스트를 분석하여 세분화하는 중...")
    
    # 한국어에서 무언가를 나열할 때 자주 쓰는 기호나 접속사를 기준으로 자릅니다.
    # 예: 쉼표, '그리고', '하고', '랑', '및'
    pattern = r',|\s+그리고\s+|\s+하고\s+|\s+하며\s+|\s+랑\s+|\s+및\s+'
    
    raw_tasks = re.split(pattern, complex_task_text)
    
    # 공백 제거 및 의미 없는 짧은 문자열(1글자 이하) 필터링
    tasks = [t.strip() for t in raw_tasks if len(t.strip()) > 1]
    
    # 만약 쪼개지지 않았다면 원본을 그대로 반환
    if not tasks:
        tasks = [complex_task_text]
        
    return tasks

def find_best_matches_for_task(task_text, db, constraints=None, top_n=3):
    if constraints is None:
        constraints = {}
        
    task_vector = model.encode(task_text).tolist()
    results = []
    
    for account in db:
        # ==========================================
        # [Pre-Filtering] 평판 및 하드 제약 조건 검사
        # ==========================================
        if constraints.get("is_available") and not account.get("is_available", True):
            continue # 현재 작업 불가능한 계정 제외
            
        if constraints.get("require_human") and account.get("account_type") != "HUMAN":
            continue # 인간 전문가만 원할 경우 AI/로봇 제외
            
        if "max_cost" in constraints and account.get("cost", 10000) > constraints["max_cost"]:
            continue # 예산(단가) 초과 계정 제외
            
        if "min_elo" in constraints and account.get("elo", 1500) < constraints["min_elo"]:
            continue # 최소 요구 평판 미달 계정 제외
            
        # ==========================================
        # 조건 통과 계정 대상 벡터 유사도(적합도) 계산
        # ==========================================
        for ability in account.get("abilities_list", []):
            score = cosine_similarity(task_vector, ability["vector"])
            results.append({
                "account_name": account["name"],
                "account_type": account["account_type"],
                "elo": account.get("elo", 1500),
                "cost": account.get("cost", 10000),
                "matched_ability": ability["description"],
                "score": float(score)
            })
            
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

def build_team(complex_task_text, constraints=None):
    db = load_db()
    if not db:
        return

    print(f"\n[프로젝트 의뢰] {complex_task_text}")
    if constraints:
        print(f"⚠️ [제약 조건] 예산: {constraints.get('max_cost', '무제한')}, 최소 평판: {constraints.get('min_elo', 0)}, 인간 필수: {constraints.get('require_human', False)}")
    print("-" * 50)
    
    sub_tasks = decompose_task(complex_task_text)
    final_team = []
    
    for task in sub_tasks:
        matches = find_best_matches_for_task(task, db, constraints, top_n=1)
        if matches:
            best = matches[0]
            final_team.append({
                "task": task,
                "assignee": best["account_name"],
                "type": best["account_type"],
                "elo": best["elo"],
                "cost": best["cost"],
                "score": best["score"]
            })
        else:
            print(f"  ❌ '{task}' 업무는 제약 조건을 만족하는 적임자를 찾지 못했습니다.")

    print("\n🚀 [Step 3] 최종 추천 HCMR 팀 구성안:")
    for item in final_team:
        print(f"  - [{item['type']}] {item['assignee']} (평판: {item['elo']}, 단가: {item['cost']})")
        print(f"    담당 업무: '{item['task']}' (매칭률: {item['score']*100:.1f}%)")
    print("-" * 50)

def taskrit_test():
    """다양한 제약 조건을 가정한 팀 빌딩 검색 파이프라인 테스트"""
    print("\n--- [search_db] Taskrit 팀 매칭 테스트 시작 ---")
    
    # 시나리오 1: 제약 조건 없음 (가장 유사도가 높은 최적임자 무조건 배정)
    print("\n[테스트 케이스 1: 제약 조건 없음 (순수 벡터 매칭)]")
    scenario_1 = "React 기반 유저 대시보드 화면 만들기, Web3 지갑 연동 에스크로 시스템 설계"
    build_team(scenario_1, constraints=None)
    
    # 시나리오 2: 예산 부족 및 즉시 투입 필요 (AI 중심 매칭)
    print("\n[테스트 케이스 2: 예산 타이트 (단가 5,000 이하), 즉시 투입 가능자]")
    constraints_2 = {
        "max_cost": 5000,
        "is_available": True
    }
    scenario_2 = "추천 알고리즘 설계 및 대용량 데이터 전처리, React 컴포넌트 자동 생성"
    build_team(scenario_2, constraints=constraints_2)
    # -> 인간(차병성 등)은 비싸서 배제되고, DataBrain-99와 DevBot-X 같은 저비용 AI가 매칭될 것입니다.

    # 시나리오 3: 중요 보안 프로젝트 (인간 필수 + 고평판 요구)
    print("\n[테스트 케이스 3: 중요 프로젝트 (평판 1600 이상, 인간 전문가 필수, 즉시 투입)]")
    constraints_3 = {
        "min_elo": 1600,
        "require_human": True,
        "is_available": True
    }
    scenario_3 = "안전한 Sha3 기반 암호화 프로토콜 적용, Web3 지갑 연동 에스크로 시스템 설계"
    build_team(scenario_3, constraints=constraints_3)
    # -> 박웹쓰리는 평판이 높고 인간이지만 'is_available=False'이므로 제외되고, 대신 가능한 다른 고평판 인간(차병성)이 억지로라도 매칭 후보로 올라가는 모습을 볼 수 있습니다.

    # 시나리오 4: O2O 융합 (최소 평판 조건만 적용)
    print("\n[테스트 케이스 4: 융합 프로젝트 (평판 1500 이상)]")
    constraints_4 = {
        "min_elo": 1500
    }
    scenario_4 = "3D 모델링 기반 플라스틱 부품 출력, 결과물 물리적 배송"
    build_team(scenario_4, constraints=constraints_4)

    print("\n--- [search_db] 테스트 종료 ---")

# ==========================================
# 실행 및 테스트
# ==========================================
if __name__ == "__main__":
    taskrit_test()