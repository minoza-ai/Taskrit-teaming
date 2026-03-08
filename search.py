import AIcore as ai
import DBio as db

DB_DATA = None

# 주어진 태스크에 최대한 부합하는 계정 찾기
def findBestMatches(task, constraints=None, top_n=3):
    if constraints is None:
        constraints = {}
    taskVector = ai.SentenceEmbedding(task)
    results = []
    
    for account in DB_DATA:
        # Pre-Filtering
        if constraints.get("IsAvailable") and not account.get("IsAvailable", True):
            continue
        if constraints.get("RequireHuman") and account.get("UserType") != "HUMAN":
            continue
        if "MaxCost" in constraints and account.get("Cost", 10000) > constraints["MaxCost"]:
            continue
        if "MinElo" in constraints and account.get("Elo", 1500) < constraints["MinElo"]:
            continue

        # Search by Ability
        for ability in account.get("Abilities", []):
            score = ai.CosineSimilarity(taskVector, ability["vector"])
            results.append({
                "UserName": account["UserName"],
                "UserType": account["UserType"],
                "Elo": account.get("Elo", 1500),
                "Cost": account.get("Cost", 10000),
                "matchedSkill": ability["description"],
                "score": float(score)
            })

    # sort and return top_n
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

# 태스크를 실행할 팀원 매칭
def MakeTeam(task, constraints=None):
    global DB_DATA
    DB_DATA = db.Load()
    
    sub_tasks = ai.SplitTasks(task)
    final_team = []
    
    for task in sub_tasks:
        matches = findBestMatches(task, constraints, top_n=1)
        if matches:
            best = matches[0]
            final_team.append({
                "task": task,
                "assignee": best["UserName"],
                "matchedSkill": best["matchedSkill"],
                "type": best["UserType"],
                "elo": best["Elo"],
                "cost": best["Cost"],
                "score": best["score"]
            })
        else:
            final_team.append({
                "task": task,
                "assignee": "", # could not find a match
                "matched": None,
                "type": None,
                "elo": None,
                "cost": None,
                "score": None
            })
    return final_team
