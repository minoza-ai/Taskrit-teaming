import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

# 로컬 DB 파일 경로
DB_FILE = "taskrit_db.json"

print("임베딩 모델을 로드하는 중입니다...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_db():
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def split_abilities(raw_text):
    """
    [1차] 텍스트를 개별 능력치 단위로 쪼갭니다.
    * MVP 단계: 쉼표(,)나 줄바꿈을 기준으로 단순 분리합니다.
    * 고도화 단계: 이 함수 내부에 LLM(프롬프트)을 연결하여 
      "사용자가 입력한 문장을 3개의 핵심 스킬 단위로 분리해줘"와 같이 처리하게 됩니다.
    """
    # 쉼표를 기준으로 분리하고 양쪽 공백 제거, 빈 문자열 제외
    raw_items = raw_text.split(',')
    abilities = [item.strip() for item in raw_items if item.strip()]
    return abilities

def add_account(name, account_type, raw_abilities_text, elo=1500, cost=10000, is_available=True):
    """
    계정 생성 시 능력치 벡터와 함께 평판(elo), 단가(cost), 가용성(is_available)을 함께 저장합니다.
    """
    individual_abilities = split_abilities(raw_abilities_text)
    abilities_data = []
    
    for ability in individual_abilities:
        vector = model.encode(ability).tolist()
        abilities_data.append({
            "description": ability,
            "vector": vector
        })

    account_data = {
        "name": name,
        "account_type": account_type,
        "raw_text": raw_abilities_text,
        "abilities_list": abilities_data,
        "elo": elo,                     # 기본 평판 점수 (기본 1500)
        "cost": cost,                   # 작업 단가
        "is_available": is_available    # 현재 작업 가능 여부 (True/False)
    }

    db = load_db()
    db.append(account_data)
    save_db(db)

def taskrit_test():
    """테스트 환경 구축 및 계정 등록 실행 (제약 조건 테스트용 데이터 다양화)"""
    print("\n--- [ability_db] Taskrit 테스트 환경 구축 시작 ---")
    init_db()
    save_db([]) # 매 실행마다 DB 초기화 (테스트용)
    
    # [인간 그룹: 3명]
    add_account(
        name="차병성", account_type="HUMAN",
        raw_abilities_text="Python 기반 백엔드 아키텍처 설계, Sha3 기반 암호화 및 opsec 보안 프로토콜 구축, 신규 프로젝트 기획 및 팀 빌딩",
        elo=1700, cost=50000, is_available=True  # 고평판, 고비용
    )
    add_account(
        name="김디자인", account_type="HUMAN",
        raw_abilities_text="Figma 기반 모바일 및 웹 UI/UX 디자인, 프론트엔드 퍼블리싱 검수, 사용성 테스트",
        elo=1400, cost=15000, is_available=True  # 저평판, 중간비용
    )
    add_account(
        name="박웹쓰리", account_type="HUMAN",
        raw_abilities_text="Solidity 스마트 컨트랙트 개발, Web3 지갑 연동 및 대금 에스크로 시스템 설계, 토큰 이코노미 기획",
        elo=1600, cost=40000, is_available=False # 현재 다른 프로젝트 진행 중 (작업 불가)
    )
    
    # [AI 에이전트 그룹: 3개]
    add_account(
        name="DevBot-X", account_type="AI",
        raw_abilities_text="React 컴포넌트 자동 생성, Python 스크립트 버그 수정, 다국어 번역 및 문서화",
        elo=1500, cost=1000, is_available=True   # 저비용 AI
    )
    add_account(
        name="DataBrain-99", account_type="AI",
        raw_abilities_text="벡터 DB 임베딩, 추천 알고리즘 설계, 대용량 데이터 전처리 및 자연어 처리",
        elo=1650, cost=5000, is_available=True   # 고평판 AI
    )
    add_account(
        name="SecurAgent", account_type="AI",
        raw_abilities_text="코드 취약점 정적 분석, 침투 테스트(Penetration Testing) 스크립트 작성, 자동화된 보안 리포트 생성",
        elo=1450, cost=2000, is_available=True
    )

    # [로봇/기계 설비 그룹: 2개]
    add_account(
        name="PrintMachine-01", account_type="ROBOT",
        raw_abilities_text="3D 모델링 파일 기반 고정밀 플라스틱 부품 출력, 자동화 조립 라인 배치",
        elo=1500, cost=20000, is_available=True
    )
    add_account(
        name="Drone-Delivery", account_type="ROBOT",
        raw_abilities_text="소형 물류 실내외 자율 주행, 결과물 물리적 배송 및 이동 경로 최적화",
        elo=1550, cost=8000, is_available=True
    )
    
    print("--- [ability_db] 테스트 환경 구축 완료 ---\n")

# ==========================================
# 실행 및 테스트
# ==========================================
if __name__ == "__main__":
    taskrit_test()