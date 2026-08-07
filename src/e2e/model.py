"""M 단계: sklearn Pipeline 학습, 평가(교차검증, 외부 검증, 해석), joblib 저장.

설계 근거
- 지표는 accuracy + F1: 클래스 비율이 불균형(약 3:1)이라 accuracy만 보면
  전부 다수 클래스로 찍어도 높게 나온다. 소수 클래스 성능을 보는 F1이
  필수. MSE/R2는 회귀 지표라 분류인 이 문제에 부적합
- 전처리를 Pipeline 안에 넣는 이유: fit이 train에서만 일어나므로
  test 통계가 전처리에 새어 들어가는 데이터 누수를 구조적으로 차단
- stratify=y: 분할 후에도 두 세트의 클래스 비율을 동일하게 유지
- joblib 저장 후 즉시 재로딩해 예측 일치를 검증

평가 3층 구조와 각각의 역할
- 단일 분할(8:2): 기본 평가와 classification_report
- 교차검증(Stratified 5-fold): 단일 분할은 분할 운에 따라 성능이 달라질
  수 있다. 5개 분할의 평균과 표준편차로 성능의 안정성까지 보고한다
- 외부 검증(adult.test): 같은 파일을 쪼갠 평가는 낙관 편향 위험이 있다.
  학습에 한 번도 쓰지 않은 별도 홀드아웃으로 일반화 성능을 최종 확인한다.
  이 파일은 첫 줄이 주석행이고 라벨 끝에 마침표가 붙어 있어(">50K.")
  전처리하지 않으면 정확도가 0으로 무너진다

오즈비: 계수를 exp()로 변환하면 "이 피처가 1 늘 때 고소득 오즈가 몇 배"로
읽힌다. 상관 히트맵에서 세운 가설(신호는 범주 변수에 있다)을 모델이
실제로 배운 내용으로 확인하는 해석 단계다.

구체적인 실측 수치는 자동 생성 보고서(output/report.md)가 담당한다.
"""

import logging
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    make_scorer,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

RF_ESTIMATORS = 100  # RandomForest 트리 수: sklearn 기본값, 비교 실험용
CV_FOLDS = 5  # 교차검증 분할 수: 관례적 표준(편향과 분산의 균형)
TOP_ODDS = 5  # 오즈비 상위/하위 표시 개수


def _build_pipeline(config: AppConfig, classifier: Any) -> Pipeline:
    """전처리(ColumnTransformer) + 분류기를 하나의 Pipeline으로 조립한다."""
    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), config.model.numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), config.model.categorical_features),
        ]
    )
    return Pipeline([("prep", preprocessor), ("clf", classifier)])


def _cross_validate(
    config: AppConfig, x: pd.DataFrame, y: pd.Series, positive: str
) -> dict[str, Any]:
    """Stratified 5-fold 교차검증: 분할 운을 제거하고 성능의 분산까지 잰다.

    클래스가 불균형이므로 각 fold의 클래스 비율을 유지하는 Stratified가
    필수 조건이다(일반 KFold는 fold별 비율이 흔들린다).
    """
    pipeline = _build_pipeline(
        config, LogisticRegression(max_iter=1000, random_state=config.project.seed)
    )
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=config.project.seed)
    scores = cross_validate(
        pipeline,
        x,
        y,
        cv=cv,
        scoring={
            "accuracy": make_scorer(accuracy_score),
            "f1": make_scorer(f1_score, pos_label=positive),
        },
    )
    return {
        "folds": CV_FOLDS,
        "accuracy_mean": round(float(scores["test_accuracy"].mean()), 4),
        "accuracy_std": round(float(scores["test_accuracy"].std()), 4),
        "f1_mean": round(float(scores["test_f1"].mean()), 4),
        "f1_std": round(float(scores["test_f1"].std()), 4),
    }


def _evaluate_external(config: AppConfig, pipeline: Pipeline) -> dict[str, Any] | None:
    """UCI adult.test로 외부 검증한다. 파일이 없으면 생략(None)."""
    path = config.data.test_raw_path
    if path is None or not path.exists():
        return None
    target = config.analysis.target
    df = pd.read_csv(
        path,
        header=None,
        names=config.data.columns,
        na_values=config.data.na_token,
        skipinitialspace=True,
        skiprows=1,  # 첫 줄이 주석행("|1x3 Cross validator")
    )
    # 라벨 끝 마침표 제거: 그대로 두면 학습 라벨(">50K")과 매칭되지 않아
    # 모든 예측이 오답 처리된다
    df[target] = df[target].str.rstrip(".")
    df = df.drop_duplicates().dropna().reset_index(drop=True)

    x = df[config.model.numeric_features + config.model.categorical_features]
    pred = pipeline.predict(x)
    return {
        "rows": len(df),
        "accuracy": round(float(accuracy_score(df[target], pred)), 4),
        "f1": round(float(f1_score(df[target], pred, pos_label=config.analysis.positive_label)), 4),
    }


def _odds_ratios(pipeline: Pipeline) -> dict[str, list[dict[str, Any]]]:
    """기준선 계수를 오즈비로 변환해 상위/하위 피처를 뽑는다.

    표준화된 수치 피처는 "1 표준편차 증가당", 원핫 범주 피처는
    "해당 범주일 때"의 고소득 오즈 배수로 읽는다.
    """
    names = pipeline.named_steps["prep"].get_feature_names_out()
    odds = np.exp(pipeline.named_steps["clf"].coef_[0])
    order = np.argsort(odds)
    fmt = [{"feature": str(names[i]), "odds": round(float(odds[i]), 2)} for i in order]
    return {"top": list(reversed(fmt[-TOP_ODDS:])), "bottom": fmt[:TOP_ODDS]}


def train_and_save(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """모델 비교, 교차검증, 외부 검증, 해석까지 수행하고 기준선을 저장한다."""
    target = config.analysis.target
    positive = config.analysis.positive_label
    x = df[config.model.numeric_features + config.model.categorical_features]
    y = df[target]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=config.model.test_size,
        stratify=y,
        random_state=config.project.seed,
    )

    # class_weight="balanced" 실험: 현재 병목은 소수 클래스 recall이다.
    # 소수 클래스의 오류에 더 큰 가중치를 주면 recall이 오르는 대신
    # precision이 내려간다. 성능 개선이 아니라 "어느 방향으로 틀릴지"를
    # 선택하는 실험이므로 recall 열을 함께 보고해 트레이드오프를 드러낸다
    candidates: list[tuple[str, Any]] = [
        ("LogisticRegression", LogisticRegression(max_iter=1000, random_state=config.project.seed)),
        (
            "LogReg(balanced)",
            LogisticRegression(
                max_iter=1000, random_state=config.project.seed, class_weight="balanced"
            ),
        ),
        (
            "RandomForest",
            RandomForestClassifier(
                n_estimators=RF_ESTIMATORS, random_state=config.project.seed, n_jobs=-1
            ),
        ),
    ]
    comparison: list[dict[str, Any]] = []
    baseline_pipeline: Pipeline | None = None
    baseline_pred: np.ndarray | None = None
    for name, clf in candidates:
        pipeline = _build_pipeline(config, clf)
        pipeline.fit(x_train, y_train)
        pred = pipeline.predict(x_test)
        comparison.append(
            {
                "name": name,
                "accuracy": round(float(accuracy_score(y_test, pred)), 4),
                "f1": round(float(f1_score(y_test, pred, pos_label=positive)), 4),
                "recall": round(float(recall_score(y_test, pred, pos_label=positive)), 4),
            }
        )
        if name == "LogisticRegression":
            baseline_pipeline = pipeline
            baseline_pred = pred

    assert baseline_pipeline is not None and baseline_pred is not None
    report_text = classification_report(y_test, baseline_pred)

    cv = _cross_validate(config, x, y, positive)
    external = _evaluate_external(config, baseline_pipeline)
    odds = _odds_ratios(baseline_pipeline)

    config.output.model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(baseline_pipeline, config.output.model_path)
    reloaded = joblib.load(config.output.model_path)
    reload_ok = bool(np.array_equal(reloaded.predict(x_test), baseline_pred))

    baseline = comparison[0]
    result = {
        "model_name": baseline["name"],
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "accuracy": baseline["accuracy"],
        "f1": baseline["f1"],
        "positive_label": positive,
        "model_path": str(config.output.model_path),
        "reload_ok": reload_ok,
        "comparison": comparison,
        "classification_report": report_text,
        "cv": cv,
        "external": external,
        "odds": odds,
    }
    for row in comparison:
        logger.info(
            "[M] %s: accuracy=%.4f, F1=%.4f, recall=%.4f",
            row["name"],
            row["accuracy"],
            row["f1"],
            row["recall"],
        )
    logger.info(
        "[M] 교차검증 %d-fold: accuracy %.4f(±%.4f), F1 %.4f(±%.4f)",
        cv["folds"],
        cv["accuracy_mean"],
        cv["accuracy_std"],
        cv["f1_mean"],
        cv["f1_std"],
    )
    if external:
        logger.info(
            "[M] 외부 검증(adult.test %s행): accuracy=%.4f, F1=%.4f",
            f"{external['rows']:,}",
            external["accuracy"],
            external["f1"],
        )
    logger.info(
        "[M] 저장 모델=%s (train %s / test %s), 재로딩 일치=%s",
        baseline["name"],
        f"{len(x_train):,}",
        f"{len(x_test):,}",
        reload_ok,
    )
    return result
