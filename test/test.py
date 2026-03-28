"""
API 테스트 스크립트

테스트 대상 서버 구동법:
1. 가상환경 활성화 (필요시)
2. 환경변수 파일(.env)에 GEMINI_API_KEY가 설정되어 있는지 확인
3. 터미널에서 아래 명령어로 FastAPI 서버를 실행:
   uvicorn app.main:app --reload
4. 새로운 터미널 세션을 열고 이 스크립트를 실행:
   python test.py
"""

import requests
import uuid
import hmac
import hashlib
import json

BASE_URL = "http://localhost:8000"
HMAC_KEY = "00000000000000000000000000000000"

def generate_hmac(message: str) -> str:
    """HMAC-SHA256 hex-digest를 생성한다."""
    return hmac.new(HMAC_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

def print_json(title: str, data: dict | list | None):
    print(f"--- {title} ---")
    if data is None:
        print("None")
    elif isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)
    print("-" * (8 + len(title)))

def run_tests():
    print("=== API 테스트 시작 ===")

    # 1. Root Endpoint Test
    print("\n[1] 루트 엔드포인트 테스트 (/)")
    try:
        res = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 루트 엔드포인트 정상 작동")
    except Exception as e:
        print(f"루트 테스트 실패: {e}")
        return

    # 2. Account 생성 테스트
    print("\n[2] 계정 생성 테스트 (/Account)")
    account_id = f"test_account_{uuid.uuid4().hex[:8]}"
    create_payload = {
        "accountId": account_id,
        "type": "agent",
        "abilityText": "Python FastAPI 전문가. 데이터베이스 설계 및 API 개발 가능.",
        "cost": 100,
        "hmac": generate_hmac(account_id)
    }
    print_json("Request JSON", create_payload)
    try:
        res = requests.post(f"{BASE_URL}/Account", json=create_payload)
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 201
        print("-> 계정 생성 정상 작동")
    except Exception as e:
        print(f"계정 생성 테스트 실패: {e}")

    # 3. Account 조회 테스트
    print("\n[3] 계정 조회 테스트 (/Account/{accountId})")
    try:
        res = requests.get(f"{BASE_URL}/Account/{account_id}")
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 계정 조회 정상 작동")
    except Exception as e:
        print(f"계정 조회 테스트 실패: {e}")

    # 4. Account 수정 테스트
    print("\n[4] 계정 상태 수정 테스트 (/Account/{accountId})")
    update_payload = {
        "abilityText": "Python FastAPI, React 전문가 추가",
        "availability": False,
        "cost": 150,
        "hmac": generate_hmac(account_id)
    }
    print_json("Request JSON", update_payload)
    try:
        res = requests.patch(f"{BASE_URL}/Account/{account_id}", json=update_payload)
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 계정 상태 수정 정상 작동")
    except Exception as e:
        print(f"계정 수정 테스트 실패: {e}")

    # 5. Account Components 조회 테스트
    print("\n[5] 계정 구성요소 조회 테스트 (/Account/{accountId}/Components)")
    ability_id = None
    requirement_id = None
    try:
        res = requests.get(f"{BASE_URL}/Account/{account_id}/Components")
        print(f"Status Code: {res.status_code}")
        try:
            data = res.json()
            print_json("Response JSON", data)
            if data.get("abilityIds"):
                ability_id = data["abilityIds"][0]
            if data.get("requirementIds"):
                requirement_id = data["requirementIds"][0]
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 계정 구성요소 조회 정상 작동")
    except Exception as e:
        print(f"구성요소 조회 테스트 실패: {e}")

    # 6. Ability 단일 조회 테스트
    if ability_id:
        print(f"\n[6] 능력치 단일 조회 테스트 (/Ability/{ability_id})")
        try:
            res = requests.get(f"{BASE_URL}/Ability/{ability_id}")
            print(f"Status Code: {res.status_code}")
            try:
                print_json("Response JSON", res.json())
            except:
                print(f"Response Text: {res.text}")
            assert res.status_code == 200
            print("-> 능력치 단일 조회 정상 작동")
        except Exception as e:
            print(f"능력치 조회 테스트 실패: {e}")
    else:
        print("\n[6] 스킵: 능력치 ID를 추출하지 못함.")

    # 7. Requirement 단일 조회 테스트
    if requirement_id:
        print(f"\n[7] 요구 능력치 단일 조회 테스트 (/Requirement/{requirement_id})")
        try:
            res = requests.get(f"{BASE_URL}/Requirement/{requirement_id}")
            print(f"Status Code: {res.status_code}")
            try:
                print_json("Response JSON", res.json())
            except:
                print(f"Response Text: {res.text}")
            assert res.status_code == 200
            print("-> 요구 능력치 단일 조회 정상 작동")
        except Exception as e:
            print(f"요구 능력치 조회 테스트 실패: {e}")
    else:
        print("\n[7] 스킵: 요구 능력치 ID를 추출하지 못함.")

    # 8. Task 생성 및 매칭 테스트
    print("\n[8] Task 생성 및 매칭 테스트 (/Task)")
    task_id = None
    task_payload = {
        "accountId": account_id,
        "request": "Python FastAPI로 간단한 CRUD 백엔드 시스템을 만들어주세요.",
        "requiredDate": 1735689599,
        "requiredElo": 1000,
        "requiredCost": 200,
        "maxCost": 500,
        "requireHuman": False,
        "hmac": generate_hmac(account_id)
    }
    print_json("Request JSON", task_payload)
    try:
        res = requests.post(f"{BASE_URL}/Task", json=task_payload)
        print(f"Status Code: {res.status_code}")
        try:
            data = res.json()
            print_json("Response JSON", data)
            if isinstance(data, list) and len(data) > 0:
                task_id = data[0].get("taskId")
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code in (200, 201)
        print("-> Task 생성 및 매칭 정상 작동")
    except Exception as e:
        print(f"Task 생성 테스트 실패: {e}")

    # 9. Task 조회 테스트
    if task_id:
        print(f"\n[9] Task 조회 테스트 (/Task/{task_id})")
        try:
            res = requests.get(f"{BASE_URL}/Task/{task_id}")
            print(f"Status Code: {res.status_code}")
            try:
                print_json("Response JSON", res.json())
            except:
                print(f"Response Text: {res.text}")
            assert res.status_code == 200
            print("-> Task 조회 정상 작동")
        except Exception as e:
            print(f"Task 조회 테스트 실패: {e}")

        # 10. Task 상태 업데이트 테스트
        print(f"\n[10] Task 상태 업데이트 테스트 (/Task/{task_id}/Status)")
        status_payload = {"status": "completed", "hmac": generate_hmac(task_id)}
        print_json("Request JSON", status_payload)
        try:
            res = requests.patch(f"{BASE_URL}/Task/{task_id}/Status", json=status_payload)
            print(f"Status Code: {res.status_code}")
            try:
                print_json("Response JSON", res.json())
            except:
                print(f"Response Text: {res.text}")
            assert res.status_code == 200
            print("-> Task 상태 업데이트 정상 작동")
        except Exception as e:
            print(f"Task 상태 업데이트 테스트 실패: {e}")
    else:
        print("\n[9, 10] 스킵: Task ID를 찾지 못함.")

    # 11. 키워드 검색 테스트
    print("\n[11] 키워드 검색 테스트 (POST /Search, mode=keyword)")
    search_keyword_payload = {
        "query": "Python FastAPI",
        "mode": "keyword",
        "limit": 10
    }
    print_json("Request JSON", search_keyword_payload)
    try:
        res = requests.post(f"{BASE_URL}/Search", json=search_keyword_payload)
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 키워드 검색 정상 작동")
    except Exception as e:
        print(f"키워드 검색 테스트 실패: {e}")

    # 12. 벡터 유사도 검색 테스트
    print("\n[12] 벡터 유사도 검색 테스트 (POST /Search, mode=vector)")
    search_vector_payload = {
        "query": "백엔드 API 개발",
        "mode": "vector",
        "limit": 10
    }
    print_json("Request JSON", search_vector_payload)
    try:
        res = requests.post(f"{BASE_URL}/Search", json=search_vector_payload)
        print(f"Status Code: {res.status_code}")
        try:
            print_json("Response JSON", res.json())
        except:
            print(f"Response Text: {res.text}")
        assert res.status_code == 200
        print("-> 벡터 유사도 검색 정상 작동")
    except Exception as e:
        print(f"벡터 유사도 검색 테스트 실패: {e}")

    # 13. Account 삭제 테스트
    print("\n[13] 계정 삭제 테스트 (/Account/{accountId})")
    try:
        res = requests.delete(f"{BASE_URL}/Account/{account_id}", params={"hmac": generate_hmac(account_id)})
        print(f"Status Code: {res.status_code}")
        try:
            if res.text:
                try:
                    print_json("Response JSON", res.json())
                except:
                    print(f"Response Text: {res.text}")
            else:
                print("Response Body is Empty")
        except:
            pass
        assert res.status_code == 204
        print("-> 계정 삭제 정상 작동")
    except Exception as e:
        print(f"계정 삭제 테스트 실패: {e}")

    print("\n=== API 테스트 종료 ===")

if __name__ == "__main__":
    run_tests()
