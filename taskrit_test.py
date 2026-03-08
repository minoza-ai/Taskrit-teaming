import DBio as db
import account
import search
import reputation

def account_test():
    print("\n" + "="*5 + " 계정 등록 테스트 시작 " + "="*5)

    # [HUMAN]
    account.AddAccount("차병성", "HUMAN", "Python 백엔드 아키텍처 설계, Sha3 기반 암호화 시스템", 1700, 50000, True)
    account.AddAccount("박웹쓰리", "HUMAN", "Solidity 스마트 컨트랙트 개발, Web3 지갑 연동", 1600, 40000, False) # 작업 불가 상태
    account.AddAccount("김디자인", "HUMAN", "Figma 기반 모바일 및 웹 UI/UX 디자인, 프론트엔드 퍼블리싱", 1400, 15000, True)

    # [AI]
    account.AddAccount("DevBot-X", "AI", "React 컴포넌트 자동 생성, Python 스크립트 버그 수정", 1500, 1000, True)
    account.AddAccount("DataBrain-99", "AI", "벡터 DB 임베딩, 추천 알고리즘 설계, 대용량 데이터 전처리", 1650, 5000, True)
    account.AddAccount("SecurAgent", "AI", "코드 취약점 정적 분석, 침투 테스트(Penetration Testing)", 1450, 2000, True)

    # [ROBOT]
    account.AddAccount("PrintMachine-01", "ROBOT", "3D 모델링 기반 고정밀 부품 출력", 1500, 20000, True)
    account.AddAccount("Drone-Delivery", "ROBOT", "소형 물류 실내외 자율 주행, 결과물 물리적 배송", 1550, 8000, True)
    account.AddAccount("AutoCam-Bot", "ROBOT", "자동화 드론 촬영, 영상 편집 및 인코딩", 1600, 15000, True)

    # [ASSET]
    account.AddAccount("DevBot-X 로그인 프롬프트", "ASSET", "React 기반 유저 로그인 대시보드 화면 생성", 9999, 500, True)
    account.AddAccount("차병성 암호화 템플릿", "ASSET", "Sha3 기반 암호화 시스템 및 보안 프로토콜 템플릿", 9999, 1000, True)
    account.AddAccount("박웹쓰리 에스크로 컨트랙트", "ASSET", "Web3 지갑 연동 에스크로 스마트 컨트랙트 코드", 9999, 2000, True)

def search_test():
    print("\n" + "="*5 + " 팀원 매칭 테스트 시작 " + "="*5)
    def printMembers(team):
        for member in team:
            print(f"    task: {member['task']}")
            if not member['assignee']:
                print(f"    - 조건에 맞는 적임자를 찾지 못했습니다.")
            else:
                print(f"    - [{member['type']}] {member['assignee']} 님 매칭 (스킬: {member['matchedSkill']}, 단가: {member['cost']}, 평판: {member['elo']})")

    # 시나리오 A: 프론트엔드, AI 추천, 3D 출력 (단어 교체)
    task_A = "사용자가 로그인해서 볼 수 있는 프론트 웹페이지 개발, 고객 맞춤형 상품 제안 AI 모델 기획, 설계 도면을 바탕으로 한 실제 플라스틱 외형 제작"
    print(f"\n  🔍 시나리오 A 의뢰 (제약 조건 없음): '{task_A}'")
    team_A = search.MakeTeam(task_A, constraints=None)
    printMembers(team_A)

    # 시나리오 B: 암호화, 모의 해킹 (단어 교체 + 예산 제한)
    task_B = "해킹 방어를 위한 최고 수준의 데이터 보호 로직 적용, 서비스 오픈 전 취약점 점검 및 모의 해킹 공격"
    constraints_B = {"MaxCost": 3000, "IsAvailable": True}
    print(f"\n  🔍 시나리오 B 의뢰 (단가 3,000 이하, 즉시 투입 가능): '{task_B}'")
    team_B = search.MakeTeam(task_B, constraints=constraints_B)
    printMembers(team_B)

    # 시나리오 C: 블록체인 지갑, UI 기획 (단어 교체 + 인간 한정)
    task_C = "가상화폐 결제를 위한 블록체인 계정 연결, 사용자가 쓰기 편한 스마트폰 앱 화면 기획안 그리기"
    constraints_C = {"RequireHuman": True, "IsAvailable": True}
    print(f"\n  🔍 시나리오 C 의뢰 (인간 필수, 즉시 투입 가능자): '{task_C}'")
    team_C = search.MakeTeam(task_C, constraints=constraints_C)
    printMembers(team_C)

def reputation_test():
    print("\n" + "="*5 + " 평판 변동 테스트 시작 " + "="*5)
    def printChange(username, is_success, difficulty):
        current_db = db.Load()
        old_elo = next(acc["Elo"] for acc in current_db if acc["UserName"] == username)
        
        reputation.UpdateELO(username, isSuccess=is_success, difficultyRating=difficulty)
        
        updated_db = db.Load()
        new_elo = next(acc["Elo"] for acc in updated_db if acc["UserName"] == username)
        status = "성공" if is_success else "실패"
        diff = new_elo - old_elo
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"    - [{username}] 난이도 {difficulty} 업무 {status} -> 기존 {old_elo} => 변경 후 {new_elo} (변동: {diff_str})")

    # 케이스 1: 자신의 ELO보다 높은 어려운 작업을 성공했을 때 (점수 대폭 상승)
    print("\n  [케이스 1: 고난이도 작업 성공]")
    printChange("차병성", is_success=True, difficulty=1900)

    # 케이스 2: 자신의 ELO보다 낮은 쉬운 작업을 성공했을 때 (점수 소폭 상승)
    print("\n  [케이스 2: 저난이도 작업 성공]")
    printChange("DevBot-X", is_success=True, difficulty=1200)

    # 케이스 3: 작업을 실패/검수 반려되었을 때 (점수 하락)
    print("\n  [케이스 3: 일반 작업 실패(반려)]")
    printChange("김디자인", is_success=False, difficulty=1500)

# 종합 테스트
def test():
    print("="*5 + " Taskrit-teaming 통합 테스트 시작 " + "="*5)

    print("\nInitalizing DB...")
    db.Init()
    db.Save([])

    account_test()
    search_test()
    reputation_test()

    print("\n" + "="*5 + " Taskrit-teaming 통합 테스트 완료 " + "="*5)

if __name__ == "__main__":
    test()
