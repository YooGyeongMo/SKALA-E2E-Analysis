"""M 단계: sklearn Pipeline 학습, 평가, joblib 저장.

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

TODO(ML 담당): classification_report 출력, RandomForest 비교 실험
"""

import logging
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from e2e.config import AppConfig

logger = logging.getLogger(__name__)


def train_and_save(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """전처리+모델 Pipeline을 학습하고 평가한 뒤 joblib으로 저장한다."""
    target = config.analysis.target
    x = df[config.model.numeric_features + config.model.categorical_features]
    y = df[target]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=config.model.test_size,
        stratify=y,
        random_state=config.project.seed,
    )

    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), config.model.numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), config.model.categorical_features),
        ]
    )
    pipeline = Pipeline(
        [
            ("prep", preprocessor),
            ("clf", LogisticRegression(max_iter=1000, random_state=config.project.seed)),
        ]
    )
    pipeline.fit(x_train, y_train)
    pred = pipeline.predict(x_test)

    accuracy = float(accuracy_score(y_test, pred))
    f1 = float(f1_score(y_test, pred, pos_label=config.analysis.positive_label))

    config.output.model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, config.output.model_path)
    reloaded = joblib.load(config.output.model_path)
    reload_ok = bool(np.array_equal(reloaded.predict(x_test), pred))

    result = {
        "model_name": "LogisticRegression",
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
        "positive_label": config.analysis.positive_label,
        "model_path": str(config.output.model_path),
        "reload_ok": reload_ok,
    }
    logger.info(
        "[M] accuracy=%.4f, F1=%.4f (train %s / test %s), 재로딩 일치=%s",
        accuracy,
        f1,
        f"{len(x_train):,}",
        f"{len(x_test):,}",
        reload_ok,
    )
    return result
