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

def find_best_matches_for_task(task_text, db, top_n=3):
    """특정 단일 Task에 대해 가장 적합한 계정들의 순위를 매깁니다."""
    task_vector = model.encode(task_text).tolist()
    
    results = []
    
    # DB의 모든 계정과 그 계정의 모든 세부 능력치를 순회하며 유사도 평가
    for account in db:
        for ability in account.get("abilities_list", []):
            ability_vector = ability["vector"]
            score = cosine_similarity(task_vector, ability_vector)
            
            results.append({
                "account_name": account["name"],
                "account_type": account["account_type"],
                "matched_ability": ability["description"],
                "score": float(score)
            })
            
    # 유사도(score)가 높은 순으로 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

def build_team(complex_task_text):
    """
    [Step 2 & Step 3] 업무를 쪼개고, 적임자를 찾아 최종 팀을 추천합니다.
    """
    db = load_db()
    if not db:
        return

    print(f"\n[프로젝트 의뢰] {complex_task_text}")
    print("-" * 50)
    
    # 1. 태스크 분할
    # !!! 실제로는 생략된 하위 작업을 ai api로 분석해 더해줘야 함 !!!
    sub_tasks = decompose_task(complex_task_text)
    print(f"✅ [Step 1] 분석된 세부 태스크 ({len(sub_tasks)}개):")
    for i, t in enumerate(sub_tasks, 1):
        print(f"  {i}. {t}")
    print("-" * 50)
    
    final_team = []
    
    # 2. 각 태스크별 후보군 검색 및 출력
    print("✅ [Step 2] 세부 태스크별 적임자 탐색 결과:")
    for task in sub_tasks:
        print(f"\n  🔍 태스크: '{task}'")
        matches = find_best_matches_for_task(task, db, top_n=2)
        
        for rank, match in enumerate(matches, 1):
            print(f"    {rank}위: [{match['account_type']}] {match['account_name']} (적합도: {match['score']:.3f})")
            print(f"        -> 매칭된 스킬: {match['matched_ability']}")
        
        # 3. 최종 팀 구성 (가장 점수가 높은 1위 후보를 팀으로 편입)
        if matches:
            best_match = matches[0]
            final_team.append({
                "task": task,
                "assignee": best_match["account_name"],
                "type": best_match["account_type"],
                "skill": best_match["matched_ability"],
                "score": best_match["score"]
            })

    print("-" * 50)
    
    # 3. 최종 팀 추천 출력
    print("🚀 [Step 3] 최종 추천 HCMR 팀 구성안:")
    assigned_members = set()
    for item in final_team:
        print(f"  - [{item['type']}] {item['assignee']} 님이 '{item['task']}' 업무를 담당합니다. (매칭률: {item['score']*100:.1f}%)")
        assigned_members.add(item['assignee'])
        
    print(f"\n  💡 총 {len(assigned_members)}명의 팀원이 투입되는 하이브리드 팀이 구성되었습니다.")

def taskrit_test():
    """팀 빌딩 검색 파이프라인 테스트 실행"""
    print("\n--- [search_db] Taskrit 팀 매칭 테스트 시작 ---")
    
    # 검색 상황 1: Web3, 보안, 그리고 UI 개발이 혼합된 소프트웨어 프로젝트
    print("\n[테스트 케이스 1: Web3 및 보안 중심 프로젝트]")
    scenario_1 = "Web3 지갑 연동 에스크로 시스템 설계, 안전한 Sha3 기반 암호화 프로토콜 적용 그리고 React 기반 유저 대시보드 화면 만들기"
    build_team(scenario_1)
    
    # 검색 상황 2: 데이터/알고리즘 기획부터 물리적 출력과 배송이 혼합된 융합 프로젝트
    print("\n[테스트 케이스 2: AI 모델링 및 하드웨어 융합 프로젝트]")
    scenario_2 = "추천 알고리즘 설계 및 대용량 데이터 전처리, 3D 모델링 기반 플라스틱 부품 출력 및 결과물 물리적 배송"
    build_team(scenario_2)
    
    print("\n--- [search_db] 테스트 종료 ---")

# ==========================================
# 실행 및 테스트
# ==========================================
if __name__ == "__main__":
    taskrit_test()