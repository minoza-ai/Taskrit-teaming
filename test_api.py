import json
import time
import requests

BASE = "http://127.0.0.1:8000"
SEP = "=" * 60


def pp(label: str, r):
    """응답 출력."""
    print(f"\n{SEP}")
    print(f"  {label}")
    print(f"  Status: {r.status_code}")
    print(SEP)
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(r.text or "(empty)")
    print()


# ── 1. Health check ──
r = requests.get(f"{BASE}/")
pp("GET / (Health Check)", r)
time.sleep(1)

# ── 2. 계정 생성 (human) ──
human1 = {
    "accountId": "550e8400-e29b-41d4-a716-446655440001",
    "type": "human",
    "abilityText": "Python backend developer. FastAPI, Django, PostgreSQL, Redis experience. Docker and Kubernetes capable. REST API design and microservice architecture.",
    "cost": 500,
}
r = requests.post(f"{BASE}/Account", json=human1)
pp("POST /Account (human1)", r)
time.sleep(5)

# ── 3. 계정 생성 (agent) ──
agent1 = {
    "accountId": "550e8400-e29b-41d4-a716-446655440002",
    "type": "agent",
    "abilityText": "AI code generation agent. Can write Python, JavaScript, TypeScript code. Automated testing and code review capabilities.",
    "cost": 200,
}
r = requests.post(f"{BASE}/Account", json=agent1)
pp("POST /Account (agent1)", r)
time.sleep(5)

# ── 4. 계정 생성 (asset) ──
asset1 = {
    "accountId": "550e8400-e29b-41d4-a716-446655440003",
    "type": "asset",
    "abilityText": "GPU server cluster with NVIDIA A100. Supports large-scale model training and inference. CUDA and TensorRT optimized.",
    "cost": 1000,
}
r = requests.post(f"{BASE}/Account", json=asset1)
pp("POST /Account (asset1)", r)
time.sleep(2)

# ── 5. 계정 조회 ──
r = requests.get(f"{BASE}/Account/{human1['accountId']}")
pp("GET /Account/{{accountId}} (human1)", r)

# ── 6. 계정 구성요소 조회 ──
r = requests.get(f"{BASE}/Account/{human1['accountId']}/Components")
pp("GET /Account/{{accountId}}/Components (human1)", r)

# ── 7. 능력치 UUID로 상세 조회 ──
try:
    components = r.json()
    if components.get("abilityIds"):
        firstAbilityId = components["abilityIds"][0]
        r = requests.get(f"{BASE}/Ability/{firstAbilityId}")
        pp(f"GET /Ability/{{abilityId}}", r)
except Exception:
    print("(능력치 조회 skip)")

# ── 8. 계정 상태 수정 ──
r = requests.patch(f"{BASE}/Account/{human1['accountId']}", json={"cost": 600, "availability": True})
pp("PATCH /Account/{{accountId}} (cost: 500->600)", r)

# ── 9. 태스크 생성 + 매칭 ──
time.sleep(5)
task1 = {
    "accountId": human1["accountId"],
    "request": "Build a REST API backend with user authentication, database integration, and deploy to Kubernetes cluster.",
    "requiredDate": 7,
    "requiredElo": 0,
    "requiredCost": 2000,
    "requireHuman": False,
    "maxCost": 2000,
}
r = requests.post(f"{BASE}/Task", json=task1)
pp("POST /Task (create + match)", r)
time.sleep(2)

# 태스크 ID 추출
try:
    matchResults = r.json()
    taskId = matchResults[0]["taskId"] if matchResults else None
except Exception:
    taskId = None

# ── 10. 태스크 조회 ──
if taskId:
    r = requests.get(f"{BASE}/Task/{taskId}")
    pp("GET /Task/{{taskId}}", r)

    # ── 11. 태스크 상태 변경 (completed) ──
    r = requests.patch(f"{BASE}/Task/{taskId}/Status", json={"status": "completed"})
    pp("PATCH /Task/{{taskId}}/Status (completed)", r)

    # ── 12. ELO 변동 확인 ──
    r = requests.get(f"{BASE}/Account/{human1['accountId']}")
    pp("GET /Account (ELO check after task complete)", r)

# ── 13. 계정 삭제 ──
r = requests.delete(f"{BASE}/Account/{agent1['accountId']}")
pp("DELETE /Account (agent1)", r)

# 삭제 확인
r = requests.get(f"{BASE}/Account/{agent1['accountId']}")
pp("GET /Account (agent1 after delete - expect 404)", r)

print(f"\n{'#' * 60}")
print("  ALL TESTS COMPLETE")
print(f"{'#' * 60}")
