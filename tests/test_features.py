"""Тесты валидации CSV и построения признаков (включая sentinel→0)."""
import numpy as np
import pandas as pd
import pytest

from ml.features import validate_csv, build_feature_row, FEATURES_V3, MIN_HISTORY_DAYS


def _make_df(n_days: int, n_sku: int = 1) -> pd.DataFrame:
    rows = []
    for sku in range(n_sku):
        for d in pd.date_range("2024-01-01", periods=n_days):
            rows.append({"date": d.date().isoformat(), "sku_id": f"S{sku}", "sales": 1})
    return pd.DataFrame(rows)


def test_validate_ok_returns_counts():
    df = _make_df(MIN_HISTORY_DAYS + 5, n_sku=2)
    rows, skus = validate_csv(df)
    assert rows == (MIN_HISTORY_DAYS + 5) * 2
    assert skus == 2


def test_validate_missing_column():
    df = _make_df(MIN_HISTORY_DAYS).drop(columns=["sales"])
    with pytest.raises(ValueError, match="отсутствуют колонки"):
        validate_csv(df)


def test_validate_too_short_history():
    df = _make_df(MIN_HISTORY_DAYS - 1)
    with pytest.raises(ValueError, match="меньше"):
        validate_csv(df)


def test_validate_empty():
    with pytest.raises(ValueError):
        validate_csv(pd.DataFrame(columns=["date", "sku_id", "sales"]))


def test_build_row_has_all_v3_features():
    row = build_feature_row([1.0] * 60, pd.Timestamp("2024-03-01"))
    assert set(row.keys()) >= set(FEATURES_V3)


def test_sentinel_missing_history_is_zero_not_negative():
    # короткая история: lag_56 и roll_*_56 не вычислимы → должны быть 0 (sentinel→0), не -1/NaN
    row = build_feature_row([2.0, 3.0], pd.Timestamp("2024-01-10"))
    assert row["lag_56"] == 0.0
    assert row["roll_mean_56"] >= 0.0
    assert not np.isnan(row["roll_std_56"])
    # ни один признак не равен sentinel -1
    assert all(v != -1.0 for v in row.values())


def test_zero_streak_and_days_since_last_sale():
    row = build_feature_row([5.0, 0.0, 0.0, 0.0], pd.Timestamp("2024-01-05"))
    assert row["zero_streak"] == 3.0
    assert row["days_since_last_sale"] == 3.0


def test_m5_only_features_filled_zero():
    row = build_feature_row([1.0] * 60, pd.Timestamp("2024-03-01"))
    for col in ("sell_price", "snap_CA", "has_event", "is_promo"):
        assert row[col] == 0.0

def test_validate_duplicate_dates_rejected():
    df = _make_df(MIN_HISTORY_DAYS + 5)
    df = pd.concat([df, df.iloc[[10]]], ignore_index=True)  # дубль одной даты
    with pytest.raises(ValueError, match="Дубликат"):
        validate_csv(df)


def test_validate_date_gaps_rejected():
    df = _make_df(MIN_HISTORY_DAYS + 10)
    df = df.drop(index=[30])  # дырка в середине истории
    with pytest.raises(ValueError, match="пропуск"):
        validate_csv(df)
