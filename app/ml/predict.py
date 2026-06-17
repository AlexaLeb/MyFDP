"""Инференс LightGBM v4: two-stage (классификатор P(sale>0) + квантильные модели).

Прогноз многошаговый рекурсивный: предсказанная медиана (q50) подаётся обратно
в историю как продажи следующего дня для пересчёта лагов.
"""
import os
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd

from ml.features import (
    FEATURES_V3,
    MODEL_DIR,
    build_feature_row,
    validate_csv,
)
from logger.logging import get_logger

logger = get_logger(logger_name=__name__)

QUANTILES = (0.1, 0.5, 0.9)
_MODEL_FILES = {0.1: "lgb_v4_q01.pkl", 0.5: "lgb_v4_q05.pkl", 0.9: "lgb_v4_q09.pkl"}

# Загружаем модели один раз при импорте модуля (в воркере — единожды на старте).
_clf = joblib.load(os.path.join(MODEL_DIR, "clf_sale_prob.pkl"))
_models = {q: joblib.load(os.path.join(MODEL_DIR, fname)) for q, fname in _MODEL_FILES.items()}
logger.info(f"Модели v4 загружены из {MODEL_DIR}")


def _predict_one_day(row: Dict[str, float]) -> Dict[str, float]:
    """row → {q10, q50, q90}. Гарантирует неотрицательность и q10<=q50<=q90."""
    x3 = np.array([[row[f] for f in FEATURES_V3]], dtype=float)
    p_sale = float(_clf.predict_proba(x3)[:, 1][0])
    x4 = np.hstack([x3, np.array([[p_sale]])])

    preds = {q: float(_models[q].predict(x4)[0]) for q in QUANTILES}
    vals = sorted(max(0.0, preds[q]) for q in QUANTILES)  # неотрицательность + монотонность
    return {"q10": vals[0], "q50": vals[1], "q90": vals[2]}


def forecast_sku(sales_history: List[float], last_date: pd.Timestamp, horizon: int) -> List[Dict]:
    """Рекурсивный прогноз на horizon дней вперёд для одного SKU."""
    history = list(map(float, sales_history))
    out: List[Dict] = []
    for step in range(1, horizon + 1):
        target_date = last_date + pd.Timedelta(days=step)
        row = build_feature_row(history, target_date)
        q = _predict_one_day(row)
        q["date"] = target_date.date().isoformat()
        out.append(q)
        history.append(q["q50"])  # медиану — обратно в историю для следующего шага
    return out


def predict_csv(df: pd.DataFrame, horizon: int) -> List[Dict]:
    """Прогноз по всему CSV. Возвращает [{sku_id, date, q10, q50, q90}].

    Предполагается, что df уже прошёл validate_csv.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["sales"] = pd.to_numeric(df["sales"])
    df = df.sort_values(["sku_id", "date"])

    results: List[Dict] = []
    for sku_id, grp in df.groupby("sku_id"):
        sales_history = grp["sales"].tolist()
        last_date = grp["date"].iloc[-1]
        for rec in forecast_sku(sales_history, last_date, horizon):
            results.append({
                "sku_id": str(sku_id),
                "date": rec["date"],
                "q10": rec["q10"],
                "q50": rec["q50"],
                "q90": rec["q90"],
            })
    logger.info(f"Прогноз готов: {df['sku_id'].nunique()} SKU × {horizon} дней = {len(results)} строк")
    return results
