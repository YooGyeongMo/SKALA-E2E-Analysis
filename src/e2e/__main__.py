"""실행 진입점: python -m e2e [--config config.yaml]"""

import argparse
import logging
import sys

from e2e.config import load_config
from e2e.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Adult Census End2End 분석 파이프라인")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        config = load_config(args.config)
        run_pipeline(config)
    except Exception:
        logging.exception("파이프라인 실패")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
