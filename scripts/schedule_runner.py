"""schedule 기반 자동 실행기.

- 기본 모드: 매일 08:00에 파이프라인 실행을 등록하고 대기 루프를 돈다
- --once: 즉시 1회 실행(발표 시연용: 한 방에 report.md가 재생성된다)

오류 격리 설계: 스케줄 잡은 예외를 잡아 로깅만 하고 루프를 살린다.
하루 한 번의 실패(일시적 네트워크 등)가 자동화 전체를 죽이면 안 되고,
멱등한 파이프라인이므로 다음 주기의 재시도가 안전하기 때문이다.
단, --once(수동 1회 실행)는 실패를 종료 코드 1로 정직하게 알린다.
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


def job(config_path: str) -> bool:
    """파이프라인 1회 실행. 실패해도 예외를 밖으로 던지지 않는다.

    스케줄 루프에서 잡이 예외를 던지면 루프 전체가 죽는다. 실패는
    logging.exception으로 원인 전체를 기록하고 False만 반환해,
    루프는 살리되 실패 사실은 로그에 남긴다.
    """
    try:
        config = load_config(config_path)
        run_pipeline(config)
        logging.info("리포트 생성 완료")
        return True
    except Exception:
        logging.exception("리포트 생성 실패: 다음 주기에 재시도한다")
        return False


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
        # 수동 1회 실행은 성공 여부를 종료 코드로 정직하게 보고한다
        return 0 if job(args.config) else 1

    schedule.every().day.at(DAILY_AT).do(job, config_path=args.config)
    logging.info("스케줄 등록 완료: 매일 %s 실행 (Ctrl+C로 종료)", DAILY_AT)
    while True:
        schedule.run_pending()
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    sys.exit(main())
