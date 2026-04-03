"""Gemini AI 서비스 — 능력치 분해 + 텍스트 임베딩."""

import asyncio
import json
import logging

from fastapi import HTTPException
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.geminiApi)

# 텍스트 생성 모델 폴백 순서: flash-lite → flash → pro → flash-lite → flash → pro
SPLITTING_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]
EMBEDDING_MODEL = "gemini-embedding-2-preview"

DECOMPOSE_SYSTEM = (
    "You are a strict skill decomposition engine. "
    "Given a description of someone's abilities, break it down into a JSON array of distinct, highly cohesive technical skills. "
    "CRITICAL CONSTRAINTS: "
    "1. ONLY extract skills explicitly mentioned in the text. DO NOT infer, assume, or hallucinate unmentioned skills (e.g., if 'Figma' is mentioned, do not assume 'Wireframing' unless stated). "
    "2. Transform each extracted skill into a FULL, DESCRIPTIVE SENTENCE in Korean that explains the capability. "
    "Example format: ['안정적인 대용량 트래픽 처리를 위한 백엔드 API 서버 설계 및 구축 역량'] "
    "Return ONLY the JSON array, no other text."
)
DECOMPOSE_TEMP = 0.2

REQUIREMENT_SYSTEM = (
    "You are a requirement analysis engine. "
    "Given an asset description, determine the single most essential human/agent skill needed. "
    "CRITICAL: Return a JSON array containing EXACTLY ONE full, descriptive sentence in Korean. "
    "This sentence must describe both the required technical skill and the context/purpose of its use. "
    "Example format: ['데이터베이스 성능 최적화 및 관리를 위한 PostgreSQL 튜닝 및 운영 역량'] "
    "Do not return isolated words. Return ONLY the JSON array, no other text."
)
REQUIREMENT_TEMP = 0.3

TASK_DECOMPOSE_SYSTEM = (
    "You are a task analysis engine. "
    "Given a task request, break it down into a JSON array of specific capabilities needed to complete the task. "
    "CRITICAL: Do NOT use isolated keywords. Write each required capability as a FULL, DESCRIPTIVE SENTENCE in Korean "
    "representing what the ideal candidate must be able to do to fulfill this specific task context. "
    "Example format: ['사용자 결제 데이터의 안전한 처리를 위한 블록체인 스마트 컨트랙트 개발 역량', 'Figma를 활용한 직관적인 모바일 앱 화면 기획 및 디자인 역량'] "
    "Return ONLY the JSON array, no other text."
)
TASK_DECOMPOSE_TEMP = 0.5

FALLBACK_DELAY = 3

async def _generateWithFallback(contents: str, systemInstruction: str, temperature: float):
    """모델 폴백을 적용한 텍스트 생성. flash → flash-lite → pro 순서로 시도."""
    loop = asyncio.get_event_loop()
    for i, model in enumerate(SPLITTING_MODELS):
        try:
            response = await loop.run_in_executor(None, lambda m=model: client.models.generate_content(
                model=m,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=systemInstruction,
                    temperature=temperature,
                ),
            ))
            if i > 0:
                logger.info(f"폴백 모델 {model} 사용 성공")
            return response
        except Exception as e:
            if "429" in str(e) and i < len(SPLITTING_MODELS) - 1:
                nextModel = SPLITTING_MODELS[i + 1]
                logger.warning(f"{model} 할당량 초과, {nextModel}로 폴백")
                await asyncio.sleep(FALLBACK_DELAY)
            else:
                logger.error(f"Gemini API 최종 실패 (AI 분석, 모델: {model}): {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Gemini API AI 분석 실패 (모든 모델 소진): {str(e)}"
                )

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]

async def _retryOnQuota(fn, is_embedding=False, text=""):
    """429 할당량 초과 시 비동기 재시도 (임베딩 전용). 최종 실패 시 명시적 오류 반환."""
    loop = asyncio.get_event_loop()
    lastError = None
    for attempt in range(MAX_RETRIES):
        try:
            return await loop.run_in_executor(None, fn)
        except Exception as e:
            lastError = e
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Gemini 할당량 초과, {delay}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                errorType = "임베딩 생성" if is_embedding else "AI 분석"
                logger.error(f"Gemini API 최종 실패 ({errorType}): {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Gemini API {errorType} 실패: {str(e)}"
                )

async def decomposeAbilities(text: str) -> list[str]:
    """능력치 원문 → 단일 능력치 리스트 (정확도 우선, low temperature)."""
    response = await _generateWithFallback(text, DECOMPOSE_SYSTEM, DECOMPOSE_TEMP)
    return _parseJsonArray(response.text)

async def decomposeRequirements(text: str) -> list[str]:
    """에셋 설명 → 요구 능력치 리스트."""
    response = await _generateWithFallback(text, REQUIREMENT_SYSTEM, REQUIREMENT_TEMP)
    return _parseJsonArray(response.text)

async def decomposeTaskRequest(text: str) -> list[str]:
    """태스크 요청 → 필요 능력치 리스트 (다양성 위해 mid temperature)."""
    response = await _generateWithFallback(text, TASK_DECOMPOSE_SYSTEM, TASK_DECOMPOSE_TEMP)
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
    """텍스트 리스트 → 벡터 임베딩 리스트 (순차 처리 및 속도 제한)."""
    results = []
    for i, t in enumerate(texts):
        if i > 0:
            # 다량 처리 시 사용량 초과를 막기 위해 약간의 시차 발생
            await asyncio.sleep(0.3)
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
