"""ELO 평판 엔진."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import gemini

# ELO 변동 상수
BASE_ELO = 1000
K_FACTOR = 32  # ELO 변동 계수

async def estimateTaskElo(db: AsyncIOMotorDatabase, request: str, requiredDate: int, requiredElo: int, requiredCost: int) -> int:
    """태스크 난이도 ELO 산정. 기존 유사 태스크의 elo를 기준으로 삼고, 난이도 요소를 가감."""
    baseElo = BASE_ELO

    # 유사 태스크 검색 시도
    try:
        await gemini.embedText(request)
        # 유사 태스크가 아닌 최근 완료/매칭 이력의 Elo 평균을 baseline으로 사용
        existingTasks = await db.tasks.find(
            {"status": {"$in": ["completed", "matched"]}},
            {"_id": 0, "elo": 1},
        ).limit(20).to_list(length=20)

        if existingTasks:
            baseElo = int(sum(t.get("elo", BASE_ELO) for t in existingTasks) / len(existingTasks))
    except Exception:
        pass

    # 난이도 요소 가감
    eloAdjustment = 0

    # 짧은 마감기한 → 난이도 상승
    if requiredDate > 0 and requiredDate <= 3:
        eloAdjustment += 200
    elif requiredDate > 0 and requiredDate <= 7:
        eloAdjustment += 100

    # 높은 ELO 요구 → 난이도 상승
    if requiredElo > 1500:
        eloAdjustment += 150
    elif requiredElo > 1200:
        eloAdjustment += 50

    # 낮은 예산 → 난이도 상승
    if requiredCost > 0 and requiredCost < 100:
        eloAdjustment += 100

    return baseElo + eloAdjustment

async def updateEloOnComplete(db: AsyncIOMotorDatabase, taskId: str, success: bool):
    """태스크 완료/실패 시 참여 계정의 ELO 변동."""
    task = await db.tasks.find_one({"taskId": taskId}, {"_id": 0})
    if not task:
        return

    account = await db.accounts.find_one({"accountId": task.get("accountId")}, {"_id": 0})
    if not account:
        return

    taskElo = task.get("elo", BASE_ELO)
    currentElo = account.get("elo", BASE_ELO)

    # ELO 변동 계산 (간소화된 Elo 레이팅)
    expected = 1 / (1 + 10 ** ((taskElo - currentElo) / 400))
    actual = 1.0 if success else 0.0
    delta = int(K_FACTOR * (actual - expected))

    await db.accounts.update_one(
        {"accountId": account["accountId"]},
        {"$set": {"elo": max(0, currentElo + delta)}},
    )
    await db.tasks.update_one(
        {"taskId": taskId},
        {"$set": {"status": "completed" if success else "failed"}},
    )
