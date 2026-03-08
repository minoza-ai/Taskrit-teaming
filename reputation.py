import DBio as db

DB_DATA = None
K_FACTOR = 32 # ELO 점수 변동 폭을 결정하는 상수

def UpdateELO(username, isSuccess, difficultyRating=1500):
    global DB_DATA
    DB_DATA = db.Load()
    
    updated = False
    for account in DB_DATA:
        if account["UserName"] == username:
            current_elo = account.get("Elo", 1500)
            
            # ELO 승률 기대치 계산
            expected_score = 1 / (1 + 10 ** ((difficultyRating - current_elo) / 400))
            actual_score = 1 if isSuccess else 0
            
            # 새로운 평판 점수 산출
            new_elo = current_elo + K_FACTOR * (actual_score - expected_score)
            account["Elo"] = round(new_elo)

            updated = True
            break
            
    if updated:
        db.Save(DB_DATA)
    else:
        raise ValueError(f"Account '{username}' not found in the database.")
