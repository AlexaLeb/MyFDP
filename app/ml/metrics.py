"""Метрики качества квантильного прогноза."""
from typing import Dict, Sequence

import numpy as np


def pinball_loss(y_true: Sequence[float], y_pred: Sequence[float], q: float) -> float:
    """Pinball (quantile) loss для уровня q.

    Для q=0.5 эквивалентен 0.5 * MAE. Штрафует занижение и завышение
    асимметрично в зависимости от квантиля.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true и y_pred должны быть одной длины")
    e = y_true - y_pred
    return float(np.mean(np.where(e >= 0, q * e, (q - 1) * e)))


def mean_pinball(y_true: Sequence[float], preds: Dict[float, Sequence[float]]) -> Dict[str, float]:
    """Средний pinball по уровням 0.1/0.5/0.9.

    preds: {0.1: [...], 0.5: [...], 0.9: [...]}.
    Возвращает {q01, q05, q09, mean}.
    """
    losses = {q: pinball_loss(y_true, preds[q], q) for q in (0.1, 0.5, 0.9)}
    return {
        "q01": losses[0.1],
        "q05": losses[0.5],
        "q09": losses[0.9],
        "mean": float(np.mean(list(losses.values()))),
    }
