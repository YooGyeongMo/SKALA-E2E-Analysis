"""Z 단계: 시각화(Seaborn PNG + Plotly HTML).

한글 폰트 규칙(실습4에서 검증한 패턴)
- sns.set_theme()가 rcParams를 초기화하므로 반드시 폰트 지정보다 먼저
- OS별 폰트: macOS=AppleGothic, Windows=Malgun Gothic, 그 외=NanumGothic
- 폰트가 없으면 경고만 남기고 계속 진행(우아한 저하), CI 환경 대비
- axes.unicode_minus=False: 마이너스 기호 깨짐 방지

차트 구성과 각각의 이유
1) 박스플롯: 주 가설(소득 그룹 간 근로시간)의 분포 차이를 그대로
   보여주는 그림. "시각화 > 검정 > 모델" 스토리의 출발점
2) 밀도 히스토그램: 그룹 크기가 76:24로 달라 빈도로 겹치면 왜곡되므로
   밀도(stat=density, common_norm=False)로 정규화해 비교. 주 40시간
   기준선을 함께 그려 "두 그룹 모두 40시간 봉우리"라는 발견을 드러낸다
3) 상관 히트맵: 수치 변수 간 선형 관계 한눈에 보기(요구사항).
   vmin/vmax를 -1~1로 고정해 색이 데이터에 따라 왜곡되지 않게 한다
4) Plotly 교육수준별 고소득 비율(HTML): 범주가 16개라 정적 그림으로는
   좁아서 인터랙티브가 적합. 모델이 학습할 신호(교육수준)의 강도를
   발표에서 마우스오버로 시연할 수 있다
"""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 디스플레이 없는 CI에서도 저장 가능해야 한다

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

# 차트 상수(매직넘버 금지): 크기와 해상도는 여기서만 바꾼다
FIGSIZE = (8, 6)
FIGSIZE_WIDE = (10, 6)
DPI = 150
PALETTE = "Set2"
STANDARD_WORKWEEK = 40  # 주 40시간 표준 근무 기준선


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
    saved: list[str] = [
        _boxplot_hypothesis(config, df, fig_dir),
        _histogram_density(config, df, fig_dir),
        _corr_heatmap(df, fig_dir),
        _plotly_education_rate(config, df, fig_dir),
    ]
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


def _histogram_density(config: AppConfig, df: pd.DataFrame, fig_dir: Path) -> str:
    """그룹별 근로시간 밀도 분포: 40시간 봉우리와 꼬리 차이를 드러낸다."""
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    sns.histplot(
        data=df,
        x=feature,
        hue=target,
        stat="density",  # 그룹 크기가 달라 빈도 대신 밀도로 비교
        common_norm=False,  # 그룹별로 따로 정규화해야 공정한 비교
        element="step",
        bins=40,
        ax=ax,
    )
    ax.axvline(STANDARD_WORKWEEK, color="gray", linestyle="--", linewidth=1)
    ax.text(STANDARD_WORKWEEK + 0.5, ax.get_ylim()[1] * 0.95, "주 40시간 표준", color="gray")
    ax.set_title("소득 그룹별 주당 근로시간 밀도 분포 (그룹별 정규화)")
    ax.set_xlabel("주당 근로시간 (시간)")
    ax.set_ylabel("밀도")
    path = fig_dir / "hist_hours_density.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _corr_heatmap(df: pd.DataFrame, fig_dir: Path) -> str:
    """수치 변수 간 상관계수 히트맵. 색 범위를 -1~1로 고정한다."""
    corr = df.select_dtypes("number").corr()
    fig, ax = plt.subplots(figsize=FIGSIZE)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
    ax.set_title("수치 변수 간 상관계수")
    path = fig_dir / "heatmap_correlation.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _plotly_education_rate(config: AppConfig, df: pd.DataFrame, fig_dir: Path) -> str:
    """교육수준별 고소득 비율 인터랙티브 막대(HTML).

    include_plotlyjs 기본값(내장)을 쓰는 이유: 오프라인에서도 열리는
    자립형 HTML이어야 발표장 네트워크에 의존하지 않는다.
    """
    target = config.analysis.target
    positive = config.analysis.positive_label
    rate = (
        df.groupby("education")[target]
        .apply(lambda s: (s == positive).mean() * 100)
        .sort_values()
        .reset_index(name="rate")
    )
    counts = df["education"].value_counts()
    rate["n"] = rate["education"].map(counts)
    fig = px.bar(
        rate,
        x="rate",
        y="education",
        orientation="h",
        labels={"rate": "고소득(>50K) 비율 (%)", "education": "교육 수준"},
        title="교육수준별 고소득 비율 (마우스오버로 표본수 확인)",
        hover_data={"n": True},
    )
    path = fig_dir / "education_income_rate.html"
    fig.write_html(path)
    return str(path)
