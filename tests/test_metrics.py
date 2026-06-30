"""Юнит-тесты pinball loss на детерминированных примерах."""
import pytest

from ml.metrics import pinball_loss, mean_pinball


def test_pinball_overprediction_q90():
    # y_true=10, y_pred=8 → e=2>=0 → q*e = 0.9*2 = 1.8
    assert pinball_loss([10.0], [8.0], 0.9) == pytest.approx(1.8)


def test_pinball_underprediction_penalised_for_high_q():
    # y_true=0, y_pred=4 → e=-4 → (q-1)*e = (0.5-1)*-4 = 2.0
    assert pinball_loss([0.0], [4.0], 0.5) == pytest.approx(2.0)


def test_pinball_perfect_prediction_is_zero():
    assert pinball_loss([5.0, 3.0], [5.0, 3.0], 0.5) == pytest.approx(0.0)


def test_pinball_q50_is_half_mae():
    # для q=0.5 pinball == 0.5 * MAE
    y_true = [1.0, 2.0, 3.0]
    y_pred = [2.0, 2.0, 5.0]  # |ошибки| = 1,0,2 → MAE=1.0
    assert pinball_loss(y_true, y_pred, 0.5) == pytest.approx(0.5)


def test_mean_pinball_keys_and_value():
    y_true = [1.0, 2.0]
    preds = {0.1: [1.0, 2.0], 0.5: [1.0, 2.0], 0.9: [1.0, 2.0]}
    out = mean_pinball(y_true, preds)
    assert set(out) == {"q01", "q05", "q09", "mean"}
    assert out["mean"] == pytest.approx(0.0)


def test_pinball_length_mismatch_raises():
    with pytest.raises(ValueError):
        pinball_loss([1.0, 2.0], [1.0], 0.5)
