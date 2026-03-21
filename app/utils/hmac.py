"""HMAC-SHA256 검증 유틸리티."""

import hashlib
import hmac as _hmac

from fastapi import HTTPException

from app.config import settings


def generateHmac(message: str) -> str:
    """주어진 메시지에 대한 HMAC-SHA256 hex-digest를 생성한다."""
    return _hmac.new(
        settings.hmacKey.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def verifyHmac(message: str, hmacHex: str) -> None:
    """HMAC 검증. 불일치 시 403 HTTPException을 raise한다."""
    expected = generateHmac(message)
    if not _hmac.compare_digest(expected, hmacHex):
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")
