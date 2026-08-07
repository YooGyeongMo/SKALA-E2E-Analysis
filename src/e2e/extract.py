"""E 단계: 원천 데이터 다운로드와 캐시.

멱등성: data/raw에 파일이 이미 있으면 재다운로드하지 않는다.
원본 파일은 절대 수정하지 않으며(교재 313p 원칙), 이후 단계는
전부 이 사본만 읽는다. 출처 URL은 config.yaml과 README에 기록한다.
"""

import logging
import urllib.request
from pathlib import Path

from e2e.config import AppConfig

logger = logging.getLogger(__name__)


def extract(config: AppConfig) -> Path:
    """원천 CSV를 내려받아 캐시 경로를 반환한다. 캐시가 있으면 그대로 쓴다."""
    raw = config.data.raw_path
    if raw.exists() and raw.stat().st_size > 0:
        logger.info("[E] 캐시 사용: %s (%s bytes)", raw, f"{raw.stat().st_size:,}")
        return raw
    raw.parent.mkdir(parents=True, exist_ok=True)
    logger.info("[E] 다운로드 시작: %s", config.data.url)
    urllib.request.urlretrieve(config.data.url, raw)
    logger.info("[E] 저장 완료: %s (%s bytes)", raw, f"{raw.stat().st_size:,}")
    return raw
