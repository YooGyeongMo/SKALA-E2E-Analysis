"""Z 단계: 시각화(Seaborn PNG).

한글 폰트 규칙(실습4에서 검증한 패턴)
- sns.set_theme()가 rcParams를 초기화하므로 반드시 폰트 지정보다 먼저
- OS별 폰트: macOS=AppleGothic, Windows=Malgun Gothic, 그 외=NanumGothic
- 폰트가 없으면 경고만 남기고 계속 진행(우아한 저하), CI 환경 대비
- axes.unicode_minus=False: 마이너스 기호 깨짐 방지

박스플롯을 첫 차트로 두는 이유: 주 가설(소득 그룹 간 근로시간)의
분포 차이를 그대로 보여주는 그림이라 "시각화 > 검정 > 모델"이
하나의 스토리로 이어진다.

TODO(시각화 담당): 상관 히트맵, 그룹 막대 차트, Plotly 인터랙티브 HTML
"""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 디스플레이 없는 CI에서도 저장 가능해야 한다

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

# 차트 상수(매직넘버 금지): 크기와 해상도는 여기서만 바꾼다
FIGSIZE = (8, 6)
DPI = 150
PALETTE = "Set2"


def set_korean_font() -> None:
    """OS별 한글 폰트를 지정한다. set_theme가 rcParams를 덮으므로 먼저 호출."""
    sns.set_theme(style="whitegrid", palette=PALETTE)
    installed = {f.name for f in fm.fontManager.ttflist}
    for candidate in ("AppleGothic", "Malgun Gothic", "NanumGothic"):
        if candidate in installed:
            plt.rcParams["font.family"] = candidate
            break
    else:
        logger.warning("[Z] 한글 폰트 미탐지: 한글 레이블이 깨질 수 있음(진행은 계속)")
    plt.rcParams["axes.unicode_minus"] = False


def visualize(config: AppConfig, df: pd.DataFrame) -> list[str]:
    """차트를 생성해 figures 디렉터리에 저장하고 경로 목록을 반환한다."""
    set_korean_font()
    fig_dir = config.output.figures_dir
    fig_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    saved.append(_boxplot_hypothesis(config, df, fig_dir))

    logger.info("[Z] 차트 %d개 저장: %s", len(saved), ", ".join(saved))
    return saved


def _boxplot_hypothesis(config: AppConfig, df: pd.DataFrame, fig_dir: Path) -> str:
    """주 가설의 그림: 소득 그룹별 주당 근로시간 박스플롯."""
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    fig, ax = plt.subplots(figsize=FIGSIZE)
    sns.boxplot(data=df, x=target, y=feature, hue=target, legend=False, ax=ax)
    ax.set_title("소득 그룹별 주당 근로시간 분포")
    ax.set_xlabel("소득 그룹")
    ax.set_ylabel("주당 근로시간 (시간)")
    path = fig_dir / "boxplot_hours_by_income.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return str(path)
