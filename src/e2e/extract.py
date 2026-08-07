"""E 단계: 원천 데이터 다운로드와 캐시.

멱등성: data/raw에 파일이 이미 있으면 재다운로드하지 않는다.
원본 파일은 절대 수정하지 않으며(교재 313p 원칙), 이후 단계는
전부 이 사본만 읽는다. 출처 URL은 config.yaml과 README에 기록한다.

외부 검증용 홀드아웃(adult.test)도 같은 규칙으로 내려받는다.
config에 test_url이 없으면 조용히 생략한다(외부 평가는 선택 사항).
"""

import logging
import urllib.request
from pathlib import Path

from e2e.config import AppConfig

logger = logging.getLogger(__name__)


def _download_if_missing(url: str, path: Path, label: str) -> Path:
    """캐시가 있으면 그대로 쓰고, 없으면 내려받는다."""
    if path.exists() and path.stat().st_size > 0:
        logger.info("[E] 캐시 사용(%s): %s (%s bytes)", label, path, f"{path.stat().st_size:,}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("[E] 다운로드 시작(%s): %s", label, url)
    urllib.request.urlretrieve(url, path)
    logger.info("[E] 저장 완료(%s): %s (%s bytes)", label, path, f"{path.stat().st_size:,}")
    return path


def extract(config: AppConfig) -> Path:
    """학습 원천(필수)과 외부 홀드아웃(선택)을 내려받아 학습 경로를 반환한다."""
    raw = _download_if_missing(config.data.url, config.data.raw_path, "학습")
    if config.data.test_url and config.data.test_raw_path:
        _download_if_missing(config.data.test_url, config.data.test_raw_path, "외부검증")
    return raw
