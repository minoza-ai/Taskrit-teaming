"""태스크 생성 / 조회 / 상태 변경 엔드포인트."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import getDb
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, MatchResult
from app.services import gemini
from app.services.matching import matchForTask
from app.services.reputation import estimateTaskElo, updateEloOnComplete

router = APIRouter(tags=["Task"])


@router.post("/Task", response_model=list[MatchResult], status_code=201)
async def createTask(body: TaskCreate, db: AsyncSession = Depends(getDb)):
    """태스크 생성 + 매칭 결과 반환."""
    # 능력치 분해
    skills = await gemini.decomposeTaskRequest(body.request)
    if not skills:
        raise HTTPException(status_code=422, detail="Could not decompose task request")

    # ELO 산정
    taskElo = await estimateTaskElo(db, body.request, body.requiredDate, body.requiredElo, body.requiredCost)

    # 태스크 저장
    taskId = str(uuid.uuid4())
    task = Task(
        taskId=taskId,
        accountId=body.accountId,
        request=body.request,
        requiredAbilities=skills,
        requiredDate=body.requiredDate,
        requiredElo=body.requiredElo,
        requiredCost=body.requiredCost,
        elo=taskElo,
        status="pending",
    )
    db.add(task)
    await db.commit()

    # 매칭
    matchResults = await matchForTask(
        db=db,
        requiredSkills=skills,
        requiredElo=body.requiredElo,
        requiredCost=body.maxCost if body.maxCost > 0 else body.requiredCost,
        requireHuman=body.requireHuman,
    )

    # 매칭 결과가 있으면 상태를 matched로 변경
    hasCandidate = any(r["candidates"] for r in matchResults)
    if hasCandidate:
        task.status = "matched"
        await db.commit()

    return [
        MatchResult(taskId=taskId, requiredAbility=r["requiredAbility"], candidates=r["candidates"])
        for r in matchResults
    ]


@router.get("/Task/{taskId}", response_model=TaskResponse)
async def getTask(taskId: str, db: AsyncSession = Depends(getDb)):
    """태스크 조회."""
    task = await db.get(Task, taskId)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/Task/{taskId}/Status", response_model=TaskResponse)
async def updateTaskStatus(taskId: str, body: TaskStatusUpdate, db: AsyncSession = Depends(getDb)):
    """태스크 상태 변경 + ELO 반영."""
    task = await db.get(Task, taskId)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.status not in ("completed", "failed"):
        raise HTTPException(status_code=422, detail="Status must be 'completed' or 'failed'")

    success = body.status == "completed"
    await updateEloOnComplete(db, taskId, success)

    await db.refresh(task)
    return task
