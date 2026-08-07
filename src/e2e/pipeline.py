"""파이프라인 오케스트레이터: run_pipeline(config).

단계를 순서대로 호출하고 각 단계의 결과 딕셔너리를 모아 보고서에
주입한다. 이 함수 자체는 로직을 갖지 않는다(조립만 담당). 로직은
전부 단계 모듈에 있으므로 실패 지점이 곧 책임 모듈이다.

멱등성: 원천은 캐시, output은 덮어쓰기이므로 언제 몇 번을 돌려도
같은 입력이면 같은 결과가 나온다(schedule 자동화의 전제 조건).
"""

import logging
import time
from typing import Any

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.extract import extract
from e2e.model import train_and_save
from e2e.report import render_report
from e2e.stats import analyze
from e2e.visualize import visualize

logger = logging.getLogger(__name__)


def run_pipeline(config: AppConfig) -> dict[str, Any]:
    """E > V > A > M > Z > R 전 단계를 실행하고 결과 요약을 반환한다."""
    started = time.perf_counter()
    logger.info("=== 파이프라인 시작: %s ===", config.project.name)

    extract(config)
    df, clean_meta = load_and_clean(config)
    stats_result = analyze(config, df)
    model_result = train_and_save(config, df)
    figures = visualize(config, df)
    report_path = render_report(
        config,
        {
            "clean": clean_meta,
            "stats": stats_result,
            "model": model_result,
            "figures": figures,
        },
    )

    elapsed = time.perf_counter() - started
    logger.info("=== 파이프라인 완료: %.1f초, 보고서 %s ===", elapsed, report_path)
    return {
        "clean": clean_meta,
        "stats": stats_result,
        "model": model_result,
        "figures": figures,
        "report_path": str(report_path),
        "elapsed_sec": round(elapsed, 1),
    }
