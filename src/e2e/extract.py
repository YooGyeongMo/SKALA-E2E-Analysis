"""E 단계: 원천 데이터 다운로드와 캐시.

멱등성: data/raw에 파일이 이미 있으면 재다운로드하지 않는다.
원본 파일은 절대 수정하지 않으며(교재 313p 원칙), 이후 단계는
전부 이 사본만 읽는다. 출처 URL은 config.yaml과 README에 기록한다.

폴백 설계: 네트워크는 일시 장애가 흔하므로 다운로드를 재시도하고,
실패한 시도의 불완전 파일은 즉시 삭제한다(다음 실행이 깨진 캐시를
정상 캐시로 오인하는 사고 방지). 최종 실패는 원인 URL을 담은
명확한 예외로 올린다.

외부 검증용 홀드아웃(adult.test)도 같은 규칙으로 내려받는다.
config에 test_url이 없으면 조용히 생략한다(외부 평가는 선택 사항).
"""

import logging
import time
import urllib.request
from pathlib import Path

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

DOWNLOAD_RETRIES = 3  # 일시적 네트워크 장애 대비 재시도 횟수
RETRY_WAIT_SEC = 2  # 재시도 간 대기(순간 장애가 지나갈 시간)


def _download_if_missing(url: str, path: Path, label: str) -> Path:
    """캐시가 있으면 그대로 쓰고, 없으면 재시도를 포함해 내려받는다."""
    if path.exists() and path.stat().st_size > 0:
        logger.info("[E] 캐시 사용(%s): %s (%s bytes)", label, path, f"{path.stat().st_size:,}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            logger.info("[E] 다운로드 시작(%s, %d/%d): %s", label, attempt, DOWNLOAD_RETRIES, url)
            urllib.request.urlretrieve(url, path)
            logger.info("[E] 저장 완료(%s): %s (%s bytes)", label, path, f"{path.stat().st_size:,}")
            return path
        except OSError as error:
            # 실패한 시도의 불완전 파일은 즉시 제거: 깨진 캐시 방지
            path.unlink(missing_ok=True)
            logger.warning(
                "[E] 다운로드 실패(%s, %d/%d): %s", label, attempt, DOWNLOAD_RETRIES, error
            )
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(RETRY_WAIT_SEC)
    raise RuntimeError(
        f"{label} 데이터 다운로드가 {DOWNLOAD_RETRIES}회 모두 실패했다: {url} "
        "(네트워크 상태를 확인하거나 잠시 후 다시 실행)"
    )


def extract(config: AppConfig) -> Path:
    """학습 원천(필수)과 외부 홀드아웃(선택)을 내려받아 학습 경로를 반환한다."""
    raw = _download_if_missing(config.data.url, config.data.raw_path, "학습")
    if config.data.test_url and config.data.test_raw_path:
        _download_if_missing(config.data.test_url, config.data.test_raw_path, "외부검증")
    return raw
