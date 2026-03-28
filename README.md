# Taskrit-teaming (Hybrid Matching Engine)

## 📌 서비스 소개
**Taskrit-teaming**은 다양한 유형의 계정(인간, AI 에이전트, 로봇, 에셋(자원))과 사용자(클라이언트)가 요청하는 태스크(Task)를 매칭해주는 **하이브리드 매칭 엔진 API**입니다.
- **Gemini NLP 연동**: 사용자의 자연어 태스크 요청을 분석하여 필요한 능력치(Ability)를 자동 추출하고 적정 ELO 난이도를 산정합니다.
- **Qdrant 벡터 검색**: 추출된 요구 능력치를 기존 계정들이 보유한 능력치와 벡터 유사도(Cosine Similarity)를 기반으로 고속 매칭합니다.
- **하이브리드 리랭킹**: 단순 유사도뿐만 아니라 ELO 평판 점수, 비용(단가) 효율성, 신규 가입 보너스 등을 종합하여 공정하게 정규화된 최적의 후보군을 선별합니다.

---

## ⚙️ 실행 및 세팅 방법

**1. 파이썬 환경 설정**
프로젝트 루트 경로에서 필요한 패키지를 설치합니다.
```bash
pip install -r requirements.txt
```

**2. 환경 변수 설정**
루트 디렉토리에 `.env` 파일을 생성하고 다음 값을 입력합니다.
```ini
GEMINI_API=AAAAAA...
DATABASE_URL=sqlite+aiosqlite:///./taskrit.db
HMAC_KEY=000000...
```
> ※ 로컬 환경의 경우 `taskrit.db` (SQLite) 및 `qdrant_data` (로컬 Qdrant) 폴더가 자동 생성 및 활용됩니다.

**3. 서버 실행**
FastAPI 서버를 실행합니다.
```bash
uvicorn app.main:app --reload
```
서버는 기본적으로 `http://localhost:8000` 에서 구동됩니다.

---

## 🚀 API 명세 (API Specification)

**중요 안내 (HMAC 인증 및 메인 백엔드 통신)**:
본 API는 악의적인 접근을 방지하기 위해 중요 요청에 `hmac` 필드를 필수로 요구합니다. 
> ⚠️ **보안 주의사항**: `HMAC_KEY`는 절대로 클라이언트(프론트엔드 앱, 웹 브라우저)에 노출되어서는 안 되며, **오직 별도의 보안이 유지되는 메인 백엔드 서버에만 존재**해야 합니다. 따라서 중요 요청(계정 생성, 태스크 매칭 등)은 프론트엔드가 엔진 서버를 직접 호출하는 것이 아니라, 클라이언트 ↔ 메인 백엔드 ↔ 매칭 엔진 형태로 경유하여 호출되어야 합니다.

- **HMAC 도출 명세 (Python 구현 예시)**:
사전에 합의된 시크릿 키(`HMAC_KEY`)와 API 요청의 핵심 식별자(`accountId` 또는 `taskId` 등)를 조합하여 **HMAC-SHA256 (hex-digest)** 문자열을 생성해 `hmac` 인자로 전송합니다.

```python
import hmac
import hashlib

# 테스트용 기본 시크릿 키 (실 운영 시 환경 변수로 관리)
HMAC_KEY = "00000000000000000000000000000000"

def generate_hmac(target_id: str) -> str:
    """
    대상 ID(Target ID)를 기반으로 HMAC-SHA256 해시를 생성합니다.
    (예: Account 생성 시 -> generate_hmac(accountId))
    """
    return hmac.new(HMAC_KEY.encode('utf-8'), target_id.encode('utf-8'), hashlib.sha256).hexdigest()
```

---

### 1. 계정 (Account) API

#### 1) 계정 생성
- **Endpoint**: `POST /Account`
- **Description**: 새로운 계정을 생성합니다. 입력된 `abilityText`는 자동으로 임베딩되어 Qdrant에 저장됩니다.
- **Request Body** (JSON):
  ```json
  {
    "accountId": "string (고유 ID)",
    "type": "string (인간: human, 에이전트: agent, 로봇: robot, 자원: asset)",
    "abilityText": "string (보유 능력이나 자기소개 텍스트)",
    "cost": "integer (비용/단가, 예: 100)",
    "hmac": "string (hmac(accountId))"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "accountId": "string",
    "type": "string",
    "elo": 1000,
    "abilityText": "string",
    "availability": true,
    "cost": 100,
    "joinDate": "2024-03-21T10:00:00Z"
  }
  ```

#### 2) 계정 단일 조회
- **Endpoint**: `GET /Account/{accountId}`
- **Description**: 특정 계정의 상세 정보를 조회합니다.
- **Response** (200 OK): 계정 생성과 동일한 JSON 객체.

#### 3) 계정 수정
- **Endpoint**: `PATCH /Account/{accountId}`
- **Description**: 계정의 상태, 텍스트, 단가 등을 수정합니다.
- **Request Body** (JSON - 모든 필드 선택적 적용):
  ```json
  {
    "abilityText": "string (수정할 텍스트)",
    "availability": false,
    "cost": 150,
    "hmac": "string (hmac(accountId))"
  }
  ```

#### 4) 계정 구성요소 배열 조회
- **Endpoint**: `GET /Account/{accountId}/Components`
- **Description**: 해당 계정이 보유한 능력치(Ability) ID들과 에셋으로서 가지는 요구 능력치(Requirement) ID들의 목록을 반환합니다.
- **Response** (200 OK):
  ```json
  {
    "accountId": "string",
    "abilityIds": ["UUID-1", "UUID-2"],
    "requirementIds": []
  }
  ```

#### 5) 계정 삭제
- **Endpoint**: `DELETE /Account/{accountId}?hmac={hmac_string}`
- **Description**: 계정과 연관된 모든 데이터(Qdrant 벡터 포함)를 삭제합니다.
- **Response** (204 No Content)

---

### 2. 계정 권장 검색 API (Account Search API)

#### 1) 계정 검색
- **Endpoint**: `POST /Search`
- **Description**: 팀 매칭을 거치지 않고 직접 계정 풀을 검색합니다. `keyword`와 `vector` 두 가지 모드를 지원합니다.
  - **`keyword` 모드**: 입력된 검색어들이 `abilityText`에 얼마나 포함되어 있는지(단어 일치율)를 기반으로 최대 1,000명의 계정을 검색합니다.
  - **`vector` 모드**: 자연어 검색어를 벡터로 변환하여 Qdrant에 저장된 각 계정의 능력치와 비교합니다. 코사인 유사도가 0.7 이상인 상위 결과 최대 200명을 검색합니다.
- **Request Body** (JSON):
  ```json
  {
    "query": "string (검색어 문장 또는 키워드)",
    "mode": "string ('keyword' 또는 'vector', 기본값: 'keyword')",
    "limit": "integer (반환할 최대 결과 수, 기본값: 20)"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "query": "string (요청한 검색어)",
    "mode": "string (적용된 모드)",
    "results": [
      {
        "accountId": "string",
        "similarity": 0.8521 // (keyword: 단어 일치 비율, vector: 코사인 유사도)
      }
    ]
  }
  ```

---

### 3. 능력치 및 요구 능력치 상세 조회 API

#### 1) 능력치 단일 조회
- **Endpoint**: `GET /Ability/{abilityId}`
- **Response** (200 OK):
  ```json
  {
    "abilityId": "string",
    "accountId": "string",
    "abilityText": "string",
    "createdAt": "datetime string"
  }
  ```

#### 2) 요구 능력치 단일 조회
- **Endpoint**: `GET /Requirement/{requirementId}`
- **Description**: 에셋(Asset) 유형의 계정이 동작하기 위해 필요한 요구 기술 명세 정보.
- **Response** (200 OK):
  ```json
  {
    "requirementId": "string",
    "accountId": "string",
    "abilityText": "string",
    "createdAt": "datetime string"
  }
  ```

---

### 3. 태스크 (Task) 및 매칭 API

#### 1) 태스크 생성 및 자동 매칭 (핵심 API)
- **Endpoint**: `POST /Task`
- **Description**: 클라이언트의 자연어 요청사항을 받아 내부적으로 필요 능력치를 분해하고, 적절한 ELO 요구치를 산정한 뒤 전체 계정 풀에서 분해된 각 능력치별 상위 후보군(최대 10명)을 리랭킹하여 반환합니다.
- **Request Body** (JSON):
  ```json
  {
    "accountId": "string (태스크를 요청하는 계정 ID)",
    "request": "string (요청하고자 하는 작업 내용)",
    "requiredDate": 1735689599, // 완료 요구 기한 (Unix Timestamp)
    "requiredElo": 1000,        // 명시적 요구 ELO (기본 0 = 제한없음)
    "requiredCost": 200,        // 명시적 요구 단가
    "requireHuman": false,      // 인간 작업자 필수 포함 여부
    "maxCost": 500,             // 상한 단가 리밋 (0이면 requiredCost를 상한으로 사용)
    "hmac": "string (hmac(accountId))"
  }
  ```
- **Response** (201 Created):
  *반환값은 각 "분석된 요구 능력치" 단위로 나누어진 배열입니다.*
  ```json
  [
    {
      "taskId": "string (생성된 통합 태스크 ID)",
      "requiredAbility": "string (Gemini가 추출한 세부 요구 스킬 명칭)",
      "candidates": [
        {
          "accountId": "string (매칭 대상 ID)",
          "accountType": "agent",
          "abilityText": "관련 능력치 전문",
          "similarity": 0.8521,     // 벡터 유사도
          "score": 0.9125,          // 최종 리랭킹 하이브리드 스코어
          "linkedAssetId": null     // 본인이 'Asset'일 경우 필요한 오퍼레이터 계정 ID
        }
      ]
    }
  ]
  ```

#### 2) 태스크 정보 단일 조회
- **Endpoint**: `GET /Task/{taskId}`
- **Description**: 생성된 태스크의 상태 정보 및 ELO 산정 결과 등을 확인합니다.
- **Response** (200 OK):
  ```json
  {
    "taskId": "string",
    "accountId": "string",
    "request": "string",
    "requiredAbilities": ["추출된 스킬1", "추출된 스킬2"],
    "requiredDate": 1735689599,
    "requiredElo": 1000,
    "requiredCost": 200,
    "elo": 1250,      // 엔진이 이 작업에 대해 책정한 실제 난이도 ELO
    "status": "matched" // pending, matched, completed, failed
  }
  ```

#### 3) 태스크 결과 플래그 반영 (ELO 평판 시스템 업데이트)
- **Endpoint**: `PATCH /Task/{taskId}/Status`
- **Description**: 프론트엔드에서 태스크의 최종 성공/실패 여부를 알리면, 이를 기반으로 참여했던 계정들의 ELO 평판 점수를 조정합니다.
- **Request Body** (JSON):
  ```json
  {
    "status": "completed", // "completed" 또는 "failed" 만 허용됨
    "hmac": "string (hmac(taskId))"
  }
  ```
- **Response** (200 OK): 태스크 응답과 동일한 JSON 반환 (status 변경됨).
