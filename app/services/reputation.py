"""ELO 평판 엔진."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.task import Task
from app.services import gemini
from app.services import qdrant as qdrantService

# ELO 변동 상수
BASE_ELO = 1000
K_FACTOR = 32  # ELO 변동 계수


async def estimateTaskElo(db: AsyncSession, request: str, requiredDate: int, requiredElo: int, requiredCost: int) -> int:
    """태스크 난이도 ELO 산정.

    기존 유사 태스크의 elo를 기준으로 삼고, 난이도 요소를 가감.
    """
    baseElo = BASE_ELO

    # 유사 태스크 검색 시도
    try:
        vector = await gemini.embedText(request)
        # abilities 컬렉션에서 유사도 검색으로 관련 계정 → 태스크 찾기
        existingTasks = (await db.execute(
            select(Task.elo).where(Task.status.in_(["completed", "matched"])).limit(20)
        )).scalars().all()

        if existingTasks:
            baseElo = int(sum(existingTasks) / len(existingTasks))
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


async def updateEloOnComplete(db: AsyncSession, taskId: str, success: bool):
    """태스크 완료/실패 시 참여 계정의 ELO 변동."""
    task = await db.get(Task, taskId)
    if not task:
        return

    account = await db.get(Account, task.accountId)
    if not account:
        return

    taskElo = task.elo

    # ELO 변동 계산 (간소화된 Elo 레이팅)
    expected = 1 / (1 + 10 ** ((taskElo - account.elo) / 400))
    actual = 1.0 if success else 0.0
    delta = int(K_FACTOR * (actual - expected))

    account.elo = max(0, account.elo + delta)
    task.status = "completed" if success else "failed"

    await db.commit()
