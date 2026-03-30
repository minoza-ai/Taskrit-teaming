"""태스크 생성 / 조회 / 상태 변경 엔드포인트."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import getDb
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, MatchResult
from app.services import gemini
from app.services.matching import matchForTask
from app.services.reputation import estimateTaskElo, updateEloOnComplete
from app.utils.hmac import verifyHmac

router = APIRouter(tags=["Task"])

@router.post("/Task", response_model=list[MatchResult], status_code=201)
async def createTask(body: TaskCreate, db: AsyncIOMotorDatabase = Depends(getDb)):
    """태스크 생성 + 매칭 결과 반환."""
    verifyHmac(body.accountId, body.hmac)

    try:
        # 능력치 분해
        skills = await gemini.decomposeTaskRequest(body.request)
        if not skills:
            raise HTTPException(status_code=422, detail="Could not decompose task request")

        # ELO 산정
        taskElo = await estimateTaskElo(db, body.request, body.requiredDate, body.requiredElo, body.requiredCost)

        # 태스크 저장
        taskId = str(uuid.uuid4())
        task = {
            "taskId": taskId,
            "accountId": body.accountId,
            "request": body.request,
            "requiredAbilities": skills,
            "requiredDate": body.requiredDate,
            "requiredElo": body.requiredElo,
            "requiredCost": body.requiredCost,
            "elo": taskElo,
            "status": "pending",
        }
        await db.tasks.insert_one(task)

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
            await db.tasks.update_one({"taskId": taskId}, {"$set": {"status": "matched"}})

        return [
            MatchResult(taskId=taskId, requiredAbility=r["requiredAbility"], candidates=r["candidates"])
            for r in matchResults
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")

@router.get("/Task/{taskId}", response_model=TaskResponse)
async def getTask(taskId: str, db: AsyncIOMotorDatabase = Depends(getDb)):
    """태스크 조회."""
    task = await db.tasks.find_one({"taskId": taskId}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/Task/{taskId}/Status", response_model=TaskResponse)
async def updateTaskStatus(taskId: str, body: TaskStatusUpdate, db: AsyncIOMotorDatabase = Depends(getDb)):
    """태스크 상태 변경 + ELO 반영."""
    verifyHmac(taskId, body.hmac)

    task = await db.tasks.find_one({"taskId": taskId}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.status not in ("completed", "failed"):
        raise HTTPException(status_code=422, detail="Status must be 'completed' or 'failed'")

    try:
        success = body.status == "completed"
        await updateEloOnComplete(db, taskId, success)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task status update failed: {str(e)}")

    updatedTask = await db.tasks.find_one({"taskId": taskId}, {"_id": 0})
    if not updatedTask:
        raise HTTPException(status_code=404, detail="Task not found")
    return updatedTask
