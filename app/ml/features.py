"""Построение признаков для инференса v4 из пользовательского CSV.

Пользователь присылает только (date, sku_id, sales). Модель v4 обучена на
M5-признаках, часть которых недоступна (цены, SNAP, события календаря США) —
они заполняются нулями. Это осознанное ограничение MVP: пайплайн end-to-end
работает, точность на чужом домене ниже, чем на M5.
"""
import json
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(__file__)
MODEL_DIR = os.environ.get(
    "MODEL_DIR",
    os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "ml_models")),
)

with open(os.path.join(MODEL_DIR, "features_v4.json"), encoding="utf-8") as f:
    _CONTRACT = json.load(f)

FEATURES_V3: List[str] = _CONTRACT["features_v3"]   # 38 признаков (вход классификатора)
FEATURES_V4: List[str] = _CONTRACT["features_v4"]   # 39 = FEATURES_V3 + p_sale
SENTINEL_COLS: List[str] = _CONTRACT["sentinel_cols"]
MIN_HISTORY_DAYS: int = _CONTRACT.get("min_history_days", 60)

REQUIRED_COLUMNS = ("date", "sku_id", "sales")

# Признаки M5, которых нет в пользовательском CSV — заполняем нулями.
M5_ONLY = {
    "sell_price", "price_rel", "is_promo", "price_change",
    "snap_CA", "snap_TX", "snap_WI",
    "has_event", "is_top_event", "is_outlier_day",
}


def validate_csv(df: pd.DataFrame) -> Tuple[int, int]:
    """Проверяет CSV. Возвращает (row_count, sku_count) или бросает ValueError."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"В CSV отсутствуют колонки: {', '.join(missing)}")
    if df.empty:
        raise ValueError("CSV пустой")

    try:
        dates = pd.to_datetime(df["date"], errors="raise")
    except Exception:
        raise ValueError("Колонка 'date' содержит некорректные даты")
    if dates.isna().any():
        raise ValueError("Колонка 'date' содержит пустые/некорректные даты")

    try:
        pd.to_numeric(df["sales"], errors="raise")
    except Exception:
        raise ValueError("Колонка 'sales' должна быть числовой")

    # Непрерывность истории: лаги считаются позиционно (h[-7] = «7 записей назад»),
    # поэтому дубликаты дат и пропуски дней дают тихо неверный прогноз — отклоняем сразу.
    days = pd.DataFrame({"sku_id": df["sku_id"].values, "date": dates.dt.normalize().values})
    dup = days[days.duplicated()]
    if len(dup) > 0:
        examples = ", ".join(
            f"{r.sku_id}: {pd.Timestamp(r.date).date()}" for r in dup.head(5).itertuples()
        )
        raise ValueError(f"Дубликаты дат внутри SKU: {examples}")

    agg = days.groupby("sku_id")["date"].agg(["min", "max", "count"])
    span_days = (agg["max"] - agg["min"]).dt.days + 1
    gapped = agg[span_days != agg["count"]]
    if len(gapped) > 0:
        examples = ", ".join(str(s) for s in gapped.index[:5])
        raise ValueError(
            f"{len(gapped)} SKU имеют пропуски дат — история должна быть непрерывной "
            f"по дням. Примеры: {examples}"
        )

    counts = agg["count"]
    short = counts[counts < MIN_HISTORY_DAYS]
    if len(short) > 0:
        examples = ", ".join(str(s) for s in short.index[:5])
        raise ValueError(
            f"{len(short)} SKU имеют меньше {MIN_HISTORY_DAYS} дней истории "
            f"(нужно для lag_56). Примеры: {examples}"
        )

    return int(len(df)), int(df["sku_id"].nunique())


def _safe_std(values: np.ndarray) -> float:
    return float(np.std(values, ddof=1)) if len(values) >= 2 else 0.0


def build_feature_row(sales_history: List[float], target_date: pd.Timestamp) -> Dict[str, float]:
    """Считает 38 признаков (порядок FEATURES_V3) для прогноза на target_date.

    sales_history — хронологический список продаж по дни ДО target_date.
    Недостающая история (sentinel) кодируется нулём.
    """
    h = np.asarray(sales_history, dtype=float)
    n = len(h)
    row: Dict[str, float] = {}

    def lag(k: int) -> float:
        return float(h[-k]) if n >= k else 0.0

    def roll_mean(w: int) -> float:
        return float(np.mean(h[-w:])) if n >= 1 else 0.0

    def roll_std(w: int) -> float:
        return _safe_std(h[-w:]) if n >= 1 else 0.0

    for k in (1, 2, 3, 4, 7, 14, 28, 56):
        row[f"lag_{k}"] = lag(k)
    for w in (7, 14, 28, 56):
        row[f"roll_mean_{w}"] = roll_mean(w)
        row[f"roll_std_{w}"] = roll_std(w)

    # Календарные признаки
    row["wday"] = float(target_date.dayofweek + 1)  # 1..7
    row["month"] = float(target_date.month)
    row["week_of_year"] = float(target_date.isocalendar()[1])
    row["is_weekend"] = float(1 if target_date.dayofweek >= 5 else 0)
    row["is_month_start"] = float(1 if target_date.day == 1 else 0)
    row["is_month_end"] = float(1 if target_date.is_month_end else 0)

    # Признаки разреженности / активности
    trailing_zeros = 0
    for v in reversed(h):
        if v == 0:
            trailing_zeros += 1
        else:
            break
    row["zero_streak"] = float(trailing_zeros)
    row["days_since_last_sale"] = float(trailing_zeros)  # дней с последней продажи
    last56 = h[-56:]
    nz = last56[last56 > 0]
    row["sale_frequency_56"] = float(len(nz) / len(last56)) if len(last56) else 0.0
    row["avg_sales_nonzero_56"] = float(np.mean(nz)) if len(nz) else 0.0
    row["age_of_series"] = float(n)
    row["is_new_sku"] = float(1 if n < 28 else 0)

    # M5-only — недоступно в user-CSV
    for col in M5_ONLY:
        row[col] = 0.0

    # Защитная замена sentinel -1 → 0 (мы и так не генерируем -1)
    for col in SENTINEL_COLS:
        if row.get(col, 0.0) == -1.0:
            row[col] = 0.0

    return row
