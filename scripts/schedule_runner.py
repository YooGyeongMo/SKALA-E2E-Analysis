"""schedule 기반 자동 실행기.

- 기본 모드: 매일 08:00에 파이프라인 실행을 등록하고 대기 루프를 돈다
- --once: 즉시 1회 실행(발표 시연용: 한 방에 report.md가 재생성된다)

파이프라인이 멱등(캐시+덮어쓰기)이므로 스케줄 반복 실행이 안전하다.
실행: python scripts/schedule_runner.py --once
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import schedule  # noqa: E402

from e2e.config import load_config  # noqa: E402
from e2e.pipeline import run_pipeline  # noqa: E402

DAILY_AT = "08:00"
POLL_SEC = 60


def job(config_path: str) -> None:
    config = load_config(config_path)
    run_pipeline(config)


def main() -> int:
    parser = argparse.ArgumentParser(description="파이프라인 스케줄 실행기")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--once", action="store_true", help="즉시 1회 실행 후 종료")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.once:
        job(args.config)
        return 0

    schedule.every().day.at(DAILY_AT).do(job, config_path=args.config)
    logging.info("스케줄 등록 완료: 매일 %s 실행 (Ctrl+C로 종료)", DAILY_AT)
    while True:
        schedule.run_pending()
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    sys.exit(main())
