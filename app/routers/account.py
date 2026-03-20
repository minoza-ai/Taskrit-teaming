"""계정 CRUD 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import getDb
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse, AccountComponents
from app.services import account as accountService

router = APIRouter(tags=["Account"])


@router.post("/Account", response_model=AccountResponse, status_code=201)
async def createAccount(body: AccountCreate, db: AsyncSession = Depends(getDb)):
    """계정 생성 (능력치 분해 + 임베딩 포함)."""
    existing = await accountService.getAccount(db, body.accountId)
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists")

    account = await accountService.createAccount(db, body.accountId, body.type, body.abilityText, body.cost)
    return account


@router.get("/Account/{accountId}", response_model=AccountResponse)
async def getAccount(accountId: str, db: AsyncSession = Depends(getDb)):
    """계정 조회."""
    account = await accountService.getAccount(db, accountId)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/Account/{accountId}", response_model=AccountResponse)
async def updateAccount(accountId: str, body: AccountUpdate, db: AsyncSession = Depends(getDb)):
    """계정 상태 수정."""
    account = await accountService.updateAccount(db, accountId, body.abilityText, body.availability, body.cost)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.delete("/Account/{accountId}", status_code=204)
async def deleteAccount(accountId: str, db: AsyncSession = Depends(getDb)):
    """계정 삭제."""
    success = await accountService.deleteAccount(db, accountId)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")


@router.get("/Account/{accountId}/Components", response_model=AccountComponents)
async def getAccountComponents(accountId: str, db: AsyncSession = Depends(getDb)):
    """계정 구성요소 조회 (능력치/요구 능력치 ID 목록)."""
    components = await accountService.getComponents(db, accountId)
    if not components:
        raise HTTPException(status_code=404, detail="Account not found")
    return components
