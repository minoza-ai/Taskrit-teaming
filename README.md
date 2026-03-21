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
루트 디렉토리에 `.env` 파일을 생성하고 다음 값을 입력합니다. (Gemini API 키 필수)
```ini
GEMINI_API_KEY=your_gemini_api_key_here
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

**중요 안내 (HMAC 인증)**:
본 API는 보안을 위해 `hmac` 필드를 필수로 요구합니다. 프론트엔드에서는 사전에 합의된 시크릿 키(`HMAC_KEY`)와 대상 ID(`accountId` 또는 `taskId` 등)를 조합하여 **HMAC-SHA256 (hex-digest)** 값을 생성해 페이로드에 포함시켜야 합니다.
*(테스트 환경 기본 시크릿 키: `00000000000000000000000000000000`)*

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

### 2. 능력치 및 요구 능력치 상세 조회 API

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
