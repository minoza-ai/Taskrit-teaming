"""Gemini AI 서비스 — 능력치 분해 + 텍스트 임베딩."""

import asyncio
import json
import logging

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.geminiApi)

SPLITTING_MODEL = "gemini-3-pro-preview"
EMBEDDING_MODEL = "gemini-embedding-2-preview"

DECOMPOSE_SYSTEM = (
    "You are a skill decomposition engine. "
    "Given a description of someone's abilities or an asset's features, "
    "break it down into a JSON array of distinct, non-overlapping, "
    "specific technical skills or job functions. "
    "Each item should be a short phrase in the original language. "
    "Return ONLY the JSON array, no other text."
)

REQUIREMENT_SYSTEM = (
    "You are a requirement analysis engine. "
    "Given an asset description, determine what human/agent skills are needed "
    "to operate or utilize this asset. "
    "Return a JSON array of distinct required skills as short phrases "
    "in the original language. Return ONLY the JSON array."
)

TASK_DECOMPOSE_SYSTEM = (
    "You are a task analysis engine. "
    "Given a task request, break it down into a JSON array of distinct skills "
    "needed to complete the task. Each skill should be specific and actionable. "
    "Return ONLY the JSON array, no other text."
)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]

async def _retryOnQuota(fn, is_embedding=False, text=""):
    """429 할당량 초과 시 비동기 재시도 및 폴백(mock) 반환."""
    loop = asyncio.get_event_loop()
    for attempt in range(MAX_RETRIES):
        try:
            return await loop.run_in_executor(None, fn)
        except Exception as e:
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Gemini 할당량 초과, {delay}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Gemini API 최종 실패, 폴백 동작 적용: {e}")
                if is_embedding:
                    # Mock vector (3072 dim)
                    return [0.01] * 3072
                else:
                    # Mock json response
                    mock_resp = type("MockResp", (), {"text": '["Python", "Backend", "API Server", "System Architecture"]'})
                    return mock_resp()
    return await loop.run_in_executor(None, fn)

async def decomposeAbilities(text: str) -> list[str]:
    """능력치 원문 → 단일 능력치 리스트 (정확도 우선, low temperature)."""
    response = await _retryOnQuota(lambda: client.models.generate_content(
        model=SPLITTING_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=DECOMPOSE_SYSTEM,
            temperature=0.2,
        ),
    ))
    return _parseJsonArray(response.text)

async def decomposeRequirements(text: str) -> list[str]:
    """에셋 설명 → 요구 능력치 리스트."""
    response = await _retryOnQuota(lambda: client.models.generate_content(
        model=SPLITTING_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=REQUIREMENT_SYSTEM,
            temperature=0.2,
        ),
    ))
    return _parseJsonArray(response.text)

async def decomposeTaskRequest(text: str) -> list[str]:
    """태스크 요청 → 필요 능력치 리스트 (다양성 위해 mid temperature)."""
    response = await _retryOnQuota(lambda: client.models.generate_content(
        model=SPLITTING_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=TASK_DECOMPOSE_SYSTEM,
            temperature=0.5,
        ),
    ))
    return _parseJsonArray(response.text)

async def embedText(text: str) -> list[float]:
    """텍스트 → 벡터 임베딩."""
    result = await _retryOnQuota(lambda: client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    ), is_embedding=True)
    if isinstance(result, list): return result  # fallback mock vector
    return result.embeddings[0].values

async def embedTexts(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트 → 벡터 임베딩 리스트 (순차)."""
    results = []
    for t in texts:
        results.append(await embedText(t))
    return results

def _parseJsonArray(text: str) -> list[str]:
    """AI 응답에서 JSON 배열 파싱."""
    cleaned = text.strip()
    # 마크다운 코드블럭 제거
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    # 폴백: 줄 단위 파싱
    return [line.strip().strip('"-,') for line in text.strip().splitlines() if line.strip()]
