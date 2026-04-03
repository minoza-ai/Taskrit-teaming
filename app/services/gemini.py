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
    "You are a strict skill decomposition engine utilizing CoT. "
    "Given a description of someone's abilities, break it down into a JSON array of objects representing technical skills. "
    "CRITICAL CONSTRAINTS: "
    "1. ONLY extract skills explicitly mentioned in the text. DO NOT infer, assume, or hallucinate unmentioned skills. "
    "2. Return an array of JSON objects with the following keys: "
    "'abilityText' (A descriptive SENTENCE in Korean), 'domain' (String or null), "
    "'job' (Must be one of: [웹 프론트엔드 개발자, 서버/백엔드 개발자, 모바일 앱 개발자, 응용 소프트웨어 개발자, 인프라/데브옵스 엔지니어, 데이터 엔지니어, 데이터 사이언티스트, AI/머신러닝 엔지니어, QA 엔지니어, 보안 엔지니어, 프로덕트/프로젝트 매니저, UI/UX 디자이너] or null), "
    "'proficiency' (Must be one of: [신입, 주니어, 미들, 시니어, 리드] or null), "
    "'techStack' (Array of Strings. ALWAYS standard format: lowercase, remove all whitespace e.g., 'spring boot' -> 'springboot'), "
    "'legacyDegree' (Must be one of: [없음, 낮음, 중간, 높음] or null). "
    "Example format: [{\"abilityText\": \"대규모 트래픽 처리를 위한 백엔드 구축 역량\", \"domain\": \"이커머스\", \"job\": \"서버/백엔드 개발자\", \"proficiency\": \"미들\", \"techStack\": [\"java\", \"springboot\"], \"legacyDegree\": \"없음\"}] "
    "Return ONLY the JSON array."
)
DECOMPOSE_TEMP = 0.2

REQUIREMENT_SYSTEM = (
    "You are a requirement analysis engine utilizing CoT. "
    "Given an asset description, determine the single most essential human/agent skill needed. "
    "CRITICAL: Return a JSON array containing EXACTLY ONE JSON object. "
    "The object must contain: "
    "'abilityText' (Descriptive sentence), 'domain', "
    "'job' (From: [웹 프론트엔드 개발자, 서버/백엔드 개발자, 모바일 앱 개발자, 응용 소프트웨어 개발자, 인프라/데브옵스 엔지니어, 데이터 엔지니어, 데이터 사이언티스트, AI/머신러닝 엔지니어, QA 엔지니어, 보안 엔지니어, 프로덕트/프로젝트 매니저, UI/UX 디자이너] or null), "
    "'proficiency' (From: [신입, 주니어, 미들, 시니어, 리드] or null), "
    "'techStack' (Array of Strings. ALWAYS lowercase and remove whitespace e.g., 'react js' -> 'reactjs'), "
    "'legacyDegree' (From: [없음, 낮음, 중간, 높음] or null). "
    "Example: [{\"abilityText\": \"데이터베이스 성능 최적화를 위한 PostgreSQL 운영 역량\", \"domain\": null, \"job\": \"데이터 엔지니어\", \"proficiency\": \"시니어\", \"techStack\": [\"postgresql\"], \"legacyDegree\": \"낮음\"}] "
    "Return ONLY the JSON array."
)
REQUIREMENT_TEMP = 0.3

TASK_DECOMPOSE_SYSTEM = (
    "You are a task analysis engine utilizing CoT. "
    "Given a task request, break it down into a JSON array of capability objects needed to complete the task. "
    "Each object must contain keys: "
    "'abilityText' (Descriptive sentence), 'domain', "
    "'job' (From: [웹 프론트엔드 개발자, 서버/백엔드 개발자, 모바일 앱 개발자, 응용 소프트웨어 개발자, 인프라/데브옵스 엔지니어, 데이터 엔지니어, 데이터 사이언티스트, AI/머신러닝 엔지니어, QA 엔지니어, 보안 엔지니어, 프로덕트/프로젝트 매니저, UI/UX 디자이너] or null), "
    "'proficiency' (From: [신입, 주니어, 미들, 시니어, 리드] or null), "
    "'techStack' (Array of Strings. ALWAYS lowercase and remove whitespace e.g., 'react js' -> 'reactjs'. 테크 스택은 사용자의 요구사항에서 명확히 유추할 수 있는 필수 기술로만 제한하라.), "
    "'legacyDegree' (From: [없음, 낮음, 중간, 높음] or null). "
    "Example: [{\"abilityText\": \"사용자 결제 데이터의 안전한 처리를 위한 블록체인 역량\", \"domain\": \"핀테크\", \"job\": \"서버/백엔드 개발자\", \"proficiency\": \"리드\", \"techStack\": [\"solidity\"], \"legacyDegree\": \"없음\"}] "
    "Return ONLY the JSON array."
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

async def decomposeAbilities(text: str) -> list[dict]:
    """능력치 원문 → 단일 능력치 객체 리스트 (정확도 우선, low temperature)."""
    response = await _generateWithFallback(text, DECOMPOSE_SYSTEM, DECOMPOSE_TEMP)
    return _parseJsonArray(response.text)

async def decomposeRequirements(text: str) -> list[dict]:
    """에셋 설명 → 요구 능력치 객체 리스트."""
    response = await _generateWithFallback(text, REQUIREMENT_SYSTEM, REQUIREMENT_TEMP)
    return _parseJsonArray(response.text)

async def decomposeTaskRequest(text: str) -> list[dict]:
    """태스크 요청 → 필요 능력치 객체 리스트 (다양성 위해 mid temperature)."""
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

import re

def _parseJsonArray(text: str) -> list[dict]:
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
            result = []
            for item in parsed:
                if isinstance(item, dict):
                    # 기술 스택은 프롬프트 지시와 더불어 Python 파이프로도 완전 정규화
                    if 'techStack' in item and isinstance(item['techStack'], list):
                        item['techStack'] = [re.sub(r'\s+', '', str(ts).lower()) for ts in item['techStack']]
                    result.append(item)
            return result
    except json.JSONDecodeError:
        pass
    return []
