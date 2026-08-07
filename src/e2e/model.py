"""M 단계: sklearn Pipeline 학습, 평가(모델 비교 포함), joblib 저장.

설계 근거
- 지표는 accuracy + F1: 클래스 비율이 약 76:24로 불균형이라 accuracy만
  보면 전부 다수 클래스로 찍어도 76%가 나온다. 소수 클래스(>50K)
  성능을 보는 F1이 필수. MSE/R2는 회귀 지표라 분류인 이 문제에 부적합
- 전처리를 Pipeline 안에 넣는 이유: fit이 train에서만 일어나므로
  test 통계가 전처리에 새어 들어가는 데이터 누수를 구조적으로 차단
- stratify=y: 분할 후에도 두 세트의 클래스 비율을 동일하게 유지
- OneHotEncoder(handle_unknown="ignore"): 운영 중 처음 보는 범주가
  와도 크래시 대신 0 벡터로 처리
- joblib 저장 후 즉시 재로딩해 예측 일치를 검증: "저장이 됐다"가 아니라
  "저장된 것이 동작한다"까지 확인

모델 비교 설계
- LogisticRegression(기준선) vs RandomForest(비선형): 동일한 분할과
  동일한 전처리로 비교해야 차이가 순수하게 모델에서 온다
- 저장(배포) 모델은 LogisticRegression으로 유지: 계수로 해석 가능하고
  빠르며, 이 과제의 목적은 Pipeline 구성 검증이지 성능 경쟁이 아니다.
  RandomForest가 이기더라도 그 차이가 해석 가능성을 포기할 만큼 큰지
  비교표로 판단 근거를 남긴다
"""

import logging
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

RF_ESTIMATORS = 100  # RandomForest 트리 수: sklearn 기본값, 비교 실험용


def _build_pipeline(config: AppConfig, classifier: Any) -> Pipeline:
    """전처리(ColumnTransformer) + 분류기를 하나의 Pipeline으로 조립한다."""
    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), config.model.numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), config.model.categorical_features),
        ]
    )
    return Pipeline([("prep", preprocessor), ("clf", classifier)])


def train_and_save(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """두 모델을 동일 조건에서 비교하고, 기준선 Pipeline을 joblib으로 저장한다."""
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

    candidates: list[tuple[str, Any]] = [
        ("LogisticRegression", LogisticRegression(max_iter=1000, random_state=config.project.seed)),
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
            }
        )
        if name == "LogisticRegression":
            baseline_pipeline = pipeline
            baseline_pred = pred

    assert baseline_pipeline is not None and baseline_pred is not None
    report_text = classification_report(y_test, baseline_pred)

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
    }
    for row in comparison:
        logger.info("[M] %s: accuracy=%.4f, F1=%.4f", row["name"], row["accuracy"], row["f1"])
    logger.info(
        "[M] 저장 모델=%s (train %s / test %s), 재로딩 일치=%s",
        baseline["name"],
        f"{len(x_train):,}",
        f"{len(x_test):,}",
        reload_ok,
    )
    return result
