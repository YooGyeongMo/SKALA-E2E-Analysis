"""R 단계: Jinja2로 report.md 자동 생성.

모든 단계의 결과 딕셔너리를 templates/report.md.j2에 주입해 렌더링한다.
보고서를 손으로 쓰지 않는 이유: 파이프라인을 다시 돌리면 보고서도
같은 수치로 다시 만들어진다(자동화의 증명이자 수치 불일치 방지).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
TEMPLATE_NAME = "report.md.j2"


def render_report(config: AppConfig, context: dict[str, Any]) -> Path:
    """결과 딕셔너리를 템플릿에 주입해 output/report.md를 생성한다.

    StrictUndefined: 템플릿이 참조하는 값이 빠져 있으면 조용히 빈칸이
    되는 대신 즉시 오류를 낸다(불완전한 보고서 방지).
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template(TEMPLATE_NAME)
    rendered = template.render(
        project_name=config.project.name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **context,
    )
    report_path = config.output.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(rendered, encoding="utf-8")
    logger.info("[R] 보고서 생성: %s (%s bytes)", report_path, f"{report_path.stat().st_size:,}")
    return report_path
